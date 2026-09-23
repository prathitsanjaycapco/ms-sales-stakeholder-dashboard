import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from app.executive_store import ExecutiveAnalyticsStore, engagement_assignments
from app.persistence import PersistentStakeholderRepository
from app.repository import ConflictError
from app.resourcing_store import (
    ResourcingStore, business_today, candidate_stage_history, candidates, onboarding_records,
    onboarding_steps, resource_requirements, resourcing_events,
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
        self.assertEqual(sum(row["stage"] in {"RESUME_REVIEW", "CAPCO_INTERVIEW", "MS_INTERVIEW", "OFFER"} for row in candidate_rows), overview["metrics"]["candidates"])
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
        self.assertGreater(analytics["MS Interview"]["average_days"], 0)
        board = next(row for row in self.store.list_onboarding() if row["blocked_steps"])
        self.assertEqual("START_AT_RISK", board["risk"])
        self.assertGreater(board["risk_explanation"]["historical_average_remaining_days"], 0)

    def test_selected_candidate_reuses_identity_and_creates_onboarding(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "RESUME_REVIEW")
        before = len(self.store.list_onboarding())
        selected = self.store.update_candidate(candidate["id"], {"stage": "ONBOARDING", "expected_start_date": date.today()})
        self.assertEqual(before + 1, len(self.store.list_onboarding()))
        self.assertEqual(candidate["capco_employee_id"], selected["capco_employee_id"])
        self.assertIsNotNone(selected["onboarding"])
        with self.engine.connect() as connection:
            history = list(connection.execute(select(candidate_stage_history).where(candidate_stage_history.c.candidate_id == candidate["id"])).mappings())
        self.assertEqual("ONBOARDING", history[-1]["stage"])

    def test_offer_acceptance_handoff_is_idempotent(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "OFFER")
        offer = self.store.get_offer(candidate["id"])
        before = len(self.store.list_onboarding())
        accepted = self.store.upsert_offer(candidate["id"], {
            "offer_status": "OFFER_ACCEPTED",
            "expected_updated_at": offer["updated_at"],
        })
        self.assertEqual(before + 1, len(self.store.list_onboarding()))
        self.assertEqual("ONBOARDING", self.store.get_candidate(candidate["id"])["stage"])
        self.store.upsert_offer(candidate["id"], {
            "offer_status": "OFFER_ACCEPTED",
            "expected_updated_at": accepted["updated_at"],
        })
        self.assertEqual(before + 1, len(self.store.list_onboarding()))
        with self.engine.connect() as connection:
            handoffs = list(connection.execute(select(candidate_stage_history).where(
                (candidate_stage_history.c.candidate_id == candidate["id"]) &
                (candidate_stage_history.c.stage == "ONBOARDING")
            )).mappings())
        self.assertEqual(1, len(handoffs))

    def test_offer_acceptance_rejects_a_role_without_remaining_headcount(self):
        offer_candidate = next(row for row in self.store.list_candidates() if row["stage"] == "OFFER")
        other_candidate = next(row for row in self.store.list_candidates(requirement_id=offer_candidate["resource_requirement_id"]) if row["id"] != offer_candidate["id"])
        self.store.update_candidate(other_candidate["id"], {"stage": "ONBOARDING"})
        role = self.store.get_requirement(offer_candidate["resource_requirement_id"])
        self.store.update_requirement(role["id"], {"requested_headcount": 1})
        offer = self.store.get_offer(offer_candidate["id"])
        with self.assertRaises(ConflictError):
            self.store.upsert_offer(offer_candidate["id"], {"offer_status": "OFFER_ACCEPTED", "expected_updated_at": offer["updated_at"]})

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
        self.assertIn({"id": "US", "label": "United States", "offices": ["New York", "Charlotte"]}, options["office_directory"])

    def test_interview_save_keeps_candidate_in_the_same_stage(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "MS_INTERVIEW")
        saved = self.store.add_interview(candidate["id"], {
            "interview_round": 2, "scheduled_at": datetime.now(timezone.utc),
            "interview_type": "Video", "status": "SCHEDULED", "feedback": "Panel booked", "recommendation": "PROCEED",
            "ms_interviewer_stakeholder_ids": [], "capco_attendee_ids": [],
        })
        self.assertEqual("MS_INTERVIEW", self.store.get_candidate(candidate["id"])["stage"])
        self.assertEqual("COMPLETED", self.store.update_interview(saved["id"], {"status": "COMPLETED", "expected_updated_at": saved["updated_at"]})["status"])

    def test_stale_candidate_write_is_rejected(self):
        candidate = self.store.list_candidates()[0]
        self.store.update_candidate(candidate["id"], {"expected_updated_at": candidate["updated_at"], "expected_start_date": date.today()})
        with self.assertRaises(ConflictError):
            self.store.update_candidate(candidate["id"], {"expected_updated_at": candidate["updated_at"], "stage": "CAPCO_INTERVIEW"})

    def test_candidate_profile_fields_are_editable_and_start_date_stays_in_sync(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "RESUME_REVIEW")
        updated = self.store.update_candidate(candidate["id"], {
            "expected_updated_at": candidate["updated_at"], "match_score": 87,
            "skills": ["Python", "AWS"], "expected_start_date": date(2099, 10, 1),
            "first_name": "Priya", "last_name": "Shah", "note": "Candidate profile edited.",
        })
        self.assertEqual(87, updated["match_score"])
        self.assertEqual(["Python", "AWS"], updated["skills"])
        self.assertEqual("Priya Shah", updated["name"])
        self.assertEqual(date(2099, 10, 1), updated["expected_start_date"])

        board = self.store.list_onboarding()[0]
        onboarded = self.store.get_candidate(board["candidate_id"])
        self.store.update_candidate(onboarded["id"], {"expected_updated_at": onboarded["updated_at"], "expected_start_date": date(2099, 11, 1)})
        self.assertEqual(date(2099, 11, 1), self.store.get_onboarding(board["id"])["expected_start_date"])

    def test_role_sourcing_state_and_candidate_transition_are_audited(self):
        role = next(row for row in self.store.list_requirements() if not row["candidate_count"])
        self.assertEqual("NEEDS_BENCH_CHECK", role["sourcing_state"])
        with self.assertRaises(ConflictError):
            self.store.update_requirement(role["id"], {"bench_outcome": "NO_CANDIDATE"})
        updated = self.store.update_requirement(role["id"], {"bench_checked": True, "bench_outcome": "NO_CANDIDATE", "resourcing_request_submitted": True})
        self.assertTrue(updated["sourcing_ready"])
        self.assertEqual("SOURCING_IN_PROGRESS", updated["sourcing_state"])
        candidate = next(row for row in self.store.list_candidates() if row["stage"] == "RESUME_REVIEW")
        with self.assertRaises(ConflictError):
            self.store.transition_candidate(candidate["id"], {"action": "ADVANCE", "target_stage": "OFFER", "expected_updated_at": candidate["updated_at"]})
        advanced = self.store.transition_candidate(candidate["id"], {"action": "ADVANCE", "expected_updated_at": candidate["updated_at"]})
        self.assertEqual("CAPCO_INTERVIEW", advanced["stage"])
        corrected = self.store.transition_candidate(advanced["id"], {"action": "CORRECT", "target_stage": "RESUME_REVIEW", "reason": "Duplicate stage update", "expected_updated_at": advanced["updated_at"]})
        self.assertEqual("RESUME_REVIEW", corrected["stage"])
        with self.engine.connect() as connection:
            audit = connection.execute(select(candidate_stage_history).where(candidate_stage_history.c.candidate_id == candidate["id"]).order_by(candidate_stage_history.c.entered_at.desc())).mappings().first()
            checklist_events = list(connection.execute(select(resourcing_events).where(resourcing_events.c.requirement_id == role["id"])).mappings())
        self.assertEqual("Duplicate stage update", audit["note"])
        self.assertTrue(any(event["event_type"] == "SOURCING_CHECKLIST_UPDATED" for event in checklist_events))

    def test_blocker_events_are_retained_after_resolution(self):
        board = next(row for row in self.store.list_onboarding() if not row["actual_start_date"])
        step = next(row for row in board["steps"] if row["status"] != "COMPLETE")
        blocked = self.store.update_step(board["id"], step["id"], {"status": "BLOCKED", "blocker_reason": "Client access approval pending"})
        self.assertTrue(blocked["blocker_history"])
        current = next(row for row in blocked["steps"] if row["id"] == step["id"])
        resolved = self.store.update_step(board["id"], step["id"], {"status": "IN_PROGRESS", "expected_updated_at": current["updated_at"]})
        self.assertEqual(["BLOCKER_RESOLVED", "BLOCKER_CREATED"], [row["event_type"] for row in resolved["blocker_history"][:2]])

    def test_role_trash_cascades_and_restores_as_one_group(self):
        role = next(row for row in self.store.list_requirements() if row["candidate_count"])
        candidate_ids = {row["id"] for row in self.store.list_candidates(requirement_id=role["id"])}
        board_ids = {row["id"] for row in self.store.list_onboarding() if row["candidate_id"] in candidate_ids}
        self.store.archive_requirement(role["id"], "Duplicate role", "employee-001")
        self.assertFalse(any(row["id"] == role["id"] for row in self.store.list_requirements()))
        self.assertFalse(candidate_ids.intersection(row["id"] for row in self.store.list_candidates()))
        self.assertFalse(board_ids.intersection(row["id"] for row in self.store.list_onboarding()))
        trash = next(row for row in self.store.list_trash() if row["id"] == role["id"])
        self.assertEqual("ROLE", trash["type"])
        self.assertEqual(1 + len(candidate_ids) + len(board_ids), trash["affected_count"])
        self.store.restore_trash_item("ROLE", role["id"])
        self.assertIsNotNone(self.store.get_requirement(role["id"]))
        self.assertEqual(candidate_ids, {row["id"] for row in self.store.list_candidates(requirement_id=role["id"])})

    def test_candidate_and_onboarding_trash_are_recoverable(self):
        candidate = next(row for row in self.store.list_candidates() if row["stage"] in {"RESUME_REVIEW", "CAPCO_INTERVIEW"})
        self.store.archive_candidate(candidate["id"], "Entered twice", "employee-001")
        self.assertFalse(any(row["id"] == candidate["id"] for row in self.store.list_candidates()))
        self.assertTrue(any(row["id"] == candidate["id"] and row["type"] == "CANDIDATE" for row in self.store.list_trash()))
        self.store.restore_trash_item("CANDIDATE", candidate["id"])
        self.assertEqual(candidate["id"], self.store.get_candidate(candidate["id"])["id"])

        board = self.store.list_onboarding()[0]
        self.store.archive_onboarding(board["id"], "Restarting onboarding", "employee-001")
        self.assertFalse(any(row["id"] == board["id"] for row in self.store.list_onboarding()))
        self.assertFalse(any(row["id"] == board["candidate_id"] for row in self.store.list_candidates()))
        self.store.restore_trash_item("ONBOARDING", board["id"])
        self.assertEqual(board["id"], self.store.get_onboarding(board["id"])["id"])


if __name__ == "__main__":
    unittest.main()
