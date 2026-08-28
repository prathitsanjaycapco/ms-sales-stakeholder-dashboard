import unittest
from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.executive_store import (
    ExecutiveAnalyticsStore, employee_capacity, engagement_assignments,
    employees, engagements, revenue_records,
)
from backend.pod_store import PodOperatingStore
from backend.repository import StakeholderRepository


class ExecutiveAnalyticsStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = StakeholderRepository()
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.pod_store = PodOperatingStore(cls.engine, cls.repository)
        cls.store = ExecutiveAnalyticsStore(cls.engine, cls.repository, cls.pod_store)
        cls.anchor = date(2026, 8, 28)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_seed_is_normalized_substantial_and_idempotent(self):
        counts = self.store.counts()
        self.assertEqual(11, counts["executive_engagements"])
        self.assertEqual(84, counts["capco_employees"])
        self.assertEqual(84, counts["engagement_assignments"])
        self.assertEqual(168, counts["employee_capacity"])
        self.assertGreaterEqual(counts["employee_skills"], 100)
        self.assertEqual(44, counts["engagement_milestones"])
        ExecutiveAnalyticsStore(self.engine, self.repository, self.pod_store)
        self.assertEqual(counts, self.store.counts())

    def test_account_revenue_matches_dated_source_records(self):
        overview = self.store.overview("quarter", self.anchor)
        with self.engine.connect() as connection:
            source_total = connection.execute(select(func.sum(revenue_records.c.amount)).where(
                revenue_records.c.recognized_on.between(date(2026, 7, 1), date(2026, 9, 30))
            )).scalar_one()
        self.assertAlmostEqual(source_total, overview["accountPulse"]["revenue"])
        self.assertAlmostEqual(
            overview["accountPulse"]["revenue"],
            sum(row["revenue"] for row in overview["podPerformance"]),
        )
        self.assertAlmostEqual(
            overview["accountPulse"]["revenue"],
            sum(row["revenue"] for row in overview["segmentPerformance"]),
        )

    def test_utilization_matches_capacity_and_billable_allocation(self):
        overview = self.store.overview("quarter", self.anchor)
        with self.engine.connect() as connection:
            capacities = dict(connection.execute(select(
                employee_capacity.c.employee_id, employee_capacity.c.available_hours
            ).where(employee_capacity.c.period_start == date(2026, 7, 1))).all())
            assignments = connection.execute(select(engagement_assignments).where(
                engagement_assignments.c.start_date <= date(2026, 9, 30),
                engagement_assignments.c.end_date >= date(2026, 7, 1),
            )).mappings().all()
        denominator = sum(capacities[row["employee_id"]] for row in assignments)
        numerator = sum(
            capacities[row["employee_id"]] * row["allocation_percent"] / 100
            for row in assignments if row["billable"]
        )
        self.assertAlmostEqual(numerator / denominator, overview["accountPulse"]["utilization"])
        self.assertEqual(len({row["employee_id"] for row in assignments}), overview["accountPulse"]["headcount"])

    def test_pipeline_weighting_uses_canonical_opportunity_records(self):
        overview = self.store.overview("quarter", self.anchor)
        opportunities = overview["commercial"]["opportunities"]
        self.assertAlmostEqual(
            sum(row["value"] * row["probability"] / 100 for row in opportunities),
            overview["commercial"]["weightedPipeline"],
        )
        self.assertTrue(all(row["stakeholderId"] in self.repository.stakeholders for row in opportunities))

    def test_project_pod_and_segment_rollups_reconcile(self):
        overview = self.store.overview("quarter", self.anchor)
        self.assertEqual(
            overview["accountPulse"]["activeProjects"],
            sum(row["activeProjects"] for row in overview["podPerformance"]),
        )
        self.assertEqual(
            overview["accountPulse"]["projectsAtRisk"],
            sum(row["projectsAtRisk"] for row in overview["podPerformance"]),
        )
        self.assertEqual(
            {"ISG", "Wealth Management", "MSIM"},
            {row["pod"] for row in overview["podPerformance"]},
        )

    def test_capacity_gap_and_recommendations_are_traceable(self):
        overview = self.store.overview("quarter", self.anchor)
        for row in overview["capacityDemand"]:
            self.assertAlmostEqual(row["availableCapacity"] - row["demand"], row["gap"], places=1)
        self.assertTrue(overview["recommendations"])
        for recommendation in overview["recommendations"]:
            self.assertTrue(recommendation["supportingMetrics"])
            self.assertTrue(recommendation["relatedEntities"])
            self.assertTrue(recommendation["confidence"])
            self.assertEqual("2026-07-01", recommendation["sourcePeriod"]["start"])

    def test_project_sponsors_and_opportunities_resolve_to_canonical_entities(self):
        overview = self.store.overview("quarter", self.anchor)
        canonical_opportunities = {row.id for row in self.repository.list_opportunities()}
        for project in overview["projectPortfolio"]:
            self.assertIn(project["stakeholderId"], self.repository.stakeholders)
            if project["opportunityId"]:
                self.assertIn(project["opportunityId"], canonical_opportunities)

    def test_pod_filter_and_period_selection(self):
        account = self.store.overview("quarter", self.anchor)
        isg = self.store.overview("quarter", self.anchor, pod="ISG")
        self.assertEqual({"ISG"}, {row["pod"] for row in isg["projectPortfolio"]})
        self.assertLess(isg["accountPulse"]["revenue"], account["accountPulse"]["revenue"])
        custom = self.store.overview("custom", start_date=date(2026, 8, 1), end_date=date(2026, 8, 31))
        self.assertEqual("2026-08-01", custom["meta"]["startDate"])
        self.assertLess(custom["accountPulse"]["revenue"], account["accountPulse"]["revenue"])

    def test_metric_definitions_and_heatmap_thresholds_are_exposed(self):
        overview = self.store.overview("quarter", self.anchor)
        definitions = overview["meta"]["definitions"]
        for key in ("utilization", "weightedPipeline", "deliveryOnTime", "capacityGap", "heatmap"):
            self.assertTrue(definitions[key])
        valid = {"Strong", "Watch", "Action"}
        self.assertTrue(all(set(row["heatmap"].values()) <= valid for row in overview["segmentPerformance"]))

    def test_weekly_view_defaults_to_monday_and_includes_all_pods(self):
        weekly = self.store.weekly(date(2026, 8, 28))
        self.assertEqual("2026-08-24", weekly["meta"]["weekStart"])
        self.assertEqual("2026-08-30", weekly["meta"]["weekEnd"])
        self.assertEqual({"ISG", "Wealth Management", "MSIM"}, {row["pod"] for row in weekly["podSummaries"]})
        self.assertTrue(weekly["weeklyCalendar"])
        self.assertTrue(weekly["attentionItems"])

    def test_weekly_employee_count_and_project_teams_reconcile_to_assignments(self):
        weekly = self.store.weekly(date(2026, 8, 24))
        with self.engine.connect() as connection:
            source_ids = set(connection.execute(select(engagement_assignments.c.employee_id).where(
                engagement_assignments.c.start_date <= date(2026, 8, 30),
                engagement_assignments.c.end_date >= date(2026, 8, 24),
                engagement_assignments.c.status == "Active",
            )).scalars())
        self.assertEqual(source_ids, {row["id"] for row in weekly["teamActivity"]})
        self.assertEqual(len(source_ids), weekly["pulse"]["activeEmployees"])
        for project in weekly["projects"]:
            self.assertEqual(project["teamSize"], len(project["team"]))
            self.assertTrue(all(member["id"] in source_ids for member in project["team"]))

    def test_weekly_team_activity_is_linked_not_free_text(self):
        weekly = self.store.weekly(date(2026, 8, 24))
        canonical_people = {row["id"] for row in weekly["teamActivity"]}
        self.assertTrue(all(row["assignments"] for row in weekly["teamActivity"]))
        self.assertTrue(all(row["activities"] for row in weekly["teamActivity"]))
        for employee in weekly["teamActivity"]:
            for activity in employee["activities"]:
                self.assertIn(activity["sourceType"], {"meeting", "event", "task", "milestone", "engagement_milestone", "assignment"})
                self.assertTrue(activity["sourceId"])
        self.assertTrue(all(set(item["employeeIds"]) <= canonical_people for item in weekly["weeklyCalendar"]))

    def test_next_four_weeks_and_simple_sales_are_derived(self):
        weekly = self.store.weekly(date(2026, 8, 24), outlook_weeks=4)
        self.assertEqual(4, len(weekly["upcomingWeeks"]))
        self.assertEqual("2026-08-31", weekly["upcomingWeeks"][0]["weekStart"])
        self.assertEqual("2026-09-27", weekly["upcomingWeeks"][-1]["weekEnd"])
        opportunities = self.store._opportunities(None)
        active = [row for row in opportunities if row["stage"] not in {"Won", "Lost"}]
        self.assertAlmostEqual(sum(row["value"] for row in active), weekly["salesSummary"]["pipeline"])
        self.assertAlmostEqual(sum(row["weightedValue"] for row in active), weekly["salesSummary"]["weightedPipeline"])
        self.assertLessEqual(len(weekly["recommendations"]), 3)

    def test_weekly_pod_filter_preserves_canonical_employee_ids(self):
        weekly = self.store.weekly(date(2026, 8, 24), pod="MSIM")
        self.assertEqual({"MSIM"}, {row["pod"] for row in weekly["podSummaries"]})
        self.assertTrue(all(set(row["pods"]) == {"MSIM"} for row in weekly["teamActivity"]))
        with self.engine.connect() as connection:
            persisted = {row[0] for row in connection.execute(select(employees.c.id))}
        self.assertTrue({row["id"] for row in weekly["teamActivity"]} <= persisted)


if __name__ == "__main__":
    unittest.main()
