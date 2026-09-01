import unittest
from datetime import date, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.executive_store import ExecutiveAnalyticsStore, engagement_assignments
from backend.persistence import PersistentStakeholderRepository
from backend.repository import ConflictError
from backend.resourcing_store import (
    ResourcingStore, business_today, candidate_stage_history, candidates, onboarding_records,
    onboarding_steps, resource_requirements,
)


class ResourcingStoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repository = PersistentStakeholderRepository(
            "sqlite+pysqlite:///:memory:", engine=self.engine, seed_demo_data=True, auto_create_schema=True,
        )
        self.executive = ExecutiveAnalyticsStore(self.engine, self.repository, None, seed_demo_data=True, auto_create_schema=True)
        self.store = ResourcingStore(self.engine, self.repository, seed_demo_data=True, auto_create_schema=True)

    def tearDown(self):
        self.engine.dispose()

    def test_overview_metrics_reconcile_to_canonical_rows(self):
        overview = self.store.overview()
        roles = self.store.list_requirements()
        candidate_rows = self.store.list_candidates()
        boards = self.store.list_onboarding()
        active_roles = [row for row in roles if row["status"] in {"OPEN", "SOURCING", "PARTIALLY_FILLED"}]
        self.assertEqual(sum(row["remaining_headcount"] for row in active_roles), overview["metrics"]["open_demand"])
        self.assertEqual(sum(row["stage"] not in {"REJECTED", "WITHDRAWN"} for row in candidate_rows), overview["metrics"]["candidates"])
        active_boards = [row for row in boards if row["overall_status"] != "COMPLETE" and not row["actual_start_date"]]
        self.assertEqual(len(active_boards), overview["metrics"]["onboarding"])
        self.assertEqual(sum(row["blocked_steps"] > 0 for row in active_boards), overview["metrics"]["blocked"])
        self.assertEqual(sum(row["responsible_party"] == "MORGAN_STANLEY" for row in active_boards), overview["metrics"]["waiting_on_ms"])
        self.assertEqual(sum(row["responsible_party"] == "CAPCO" for row in active_boards), overview["metrics"]["waiting_on_capco"])

    def test_aging_durations_and_risk_are_calculated_from_dates(self):
        role = max(self.store.list_requirements(), key=lambda row: row["age_days"])
        created_at = role["created_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_date = created_at.astimezone(ZoneInfo("America/New_York")).date()
        self.assertEqual((business_today() - created_date).days, role["age_days"])
        analytics = {row["stage"]: row for row in self.store.analytics()}
        self.assertGreater(analytics["MS Review"]["average_days"], 0)
        board = next(row for row in self.store.list_onboarding() if row["blocked_steps"])
        self.assertEqual("START_AT_RISK", board["risk"])
        self.assertGreater(board["risk_explanation"]["historical_average_remaining_days"], 0)

    def test_selected_candidate_reuses_identity_and_creates_onboarding(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "CAPCO_REVIEW")
        before = len(self.store.list_onboarding())
        selected = self.store.update_candidate(candidate["id"], {"stage": "SELECTED", "expected_start_date": date.today()})
        self.assertEqual(before + 1, len(self.store.list_onboarding()))
        self.assertEqual(candidate["capco_employee_id"], selected["capco_employee_id"])
        self.assertIsNotNone(selected["onboarding"])
        with self.engine.connect() as connection:
            history = list(connection.execute(select(candidate_stage_history).where(candidate_stage_history.c.candidate_id == candidate["id"])).mappings())
        self.assertEqual("SELECTED", history[-1]["stage"])

    def test_started_candidate_creates_employee_assignment_to_same_project(self):
        candidate_by_id = {row["id"]: row for row in self.store.list_candidates()}
        board = next(row for row in self.store.list_onboarding() if not row["actual_start_date"] and not candidate_by_id[row["candidate_id"]]["capco_employee_id"])
        with self.engine.begin() as connection:
            connection.execute(onboarding_steps.update().where(onboarding_steps.c.onboarding_record_id == board["id"]).values(status="COMPLETE"))
        result = self.store.start_candidate(board["id"])
        candidate = self.store.get_candidate(board["candidate_id"])
        requirement = self.store.get_requirement(candidate["resource_requirement_id"])
        with self.engine.connect() as connection:
            assignment = connection.execute(select(engagement_assignments).where(engagement_assignments.c.id == result["assignment_id"])).mappings().one()
        self.assertEqual(requirement["engagement_id"], assignment["engagement_id"])
        self.assertEqual(result["employee_id"], assignment["employee_id"])

    def test_no_orphan_candidate_or_onboarding_rows(self):
        with self.engine.connect() as connection:
            requirement_ids = set(connection.execute(select(resource_requirements.c.id)).scalars())
            candidate_rows = list(connection.execute(select(candidates)).mappings())
            candidate_ids = {row["id"] for row in candidate_rows}
            boards = list(connection.execute(select(onboarding_records)).mappings())
        self.assertTrue(all(row["resource_requirement_id"] in requirement_ids for row in candidate_rows))
        self.assertTrue(all(row["candidate_id"] in candidate_ids for row in boards))

    def test_options_use_canonical_projects_people_and_stakeholders(self):
        options = self.store.options("ISG")
        self.assertTrue(options["engagements"])
        self.assertTrue(options["employees"])
        self.assertTrue(options["stakeholders"])
        self.assertTrue(all(row["pod_id"] == "ISG" for row in options["engagements"]))

    def test_stale_candidate_write_is_rejected(self):
        candidate = self.store.list_candidates()[0]
        self.store.update_candidate(candidate["id"], {"expected_updated_at": candidate["updated_at"], "expected_start_date": date.today()})
        with self.assertRaises(ConflictError):
            self.store.update_candidate(candidate["id"], {"expected_updated_at": candidate["updated_at"], "stage": "CAPCO_REVIEW"})

    def test_blocker_events_are_retained_after_resolution(self):
        board = next(row for row in self.store.list_onboarding() if not row["actual_start_date"])
        step = next(row for row in board["steps"] if row["status"] != "COMPLETE")
        blocked = self.store.update_step(board["id"], step["id"], {"status": "BLOCKED", "blocker_reason": "Client access approval pending"})
        self.assertTrue(blocked["blocker_history"])
        current = next(row for row in blocked["steps"] if row["id"] == step["id"])
        resolved = self.store.update_step(board["id"], step["id"], {"status": "IN_PROGRESS", "expected_updated_at": current["updated_at"]})
        self.assertEqual(["BLOCKER_RESOLVED", "BLOCKER_CREATED"], [row["event_type"] for row in resolved["blocker_history"][:2]])


if __name__ == "__main__":
    unittest.main()
