import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.executive_store import ExecutiveAnalyticsStore
from backend.integrity import reconcile_account
from backend.pod_store import PodOperatingStore
from backend.persistence import PersistentStakeholderRepository


class AccountIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repository = PersistentStakeholderRepository(
            "sqlite+pysqlite:///:memory:", engine=self.engine, seed_demo_data=True, auto_create_schema=True,
        )
        self.pod_store = PodOperatingStore(self.engine, self.repository)
        self.executive_store = ExecutiveAnalyticsStore(self.engine, self.repository, self.pod_store)

    def tearDown(self):
        self.engine.dispose()

    def test_cross_screen_pipeline_meetings_and_workforce_reconcile(self):
        result = reconcile_account(self.repository, self.pod_store, self.executive_store, date.today())
        failures = [item for item in result["checks"] if not item["passed"]]
        self.assertEqual([], failures, failures)
        self.assertEqual("passed", result["status"])


if __name__ == "__main__":
    unittest.main()
