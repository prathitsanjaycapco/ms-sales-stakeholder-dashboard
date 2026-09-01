import unittest
from decimal import Decimal

from sqlalchemy import select

from backend.executive_import import ExecutiveImportBatch, EngagementRow, RevenueRow, import_executive_batch
from backend.executive_store import ExecutiveAnalyticsStore, engagements, revenue_records
from backend.persistence import PersistentStakeholderRepository


class ExecutiveImportTests(unittest.TestCase):
    def setUp(self):
        self.repository = PersistentStakeholderRepository("sqlite+pysqlite:///:memory:", seed_demo_data=True, auto_create_schema=True)
        self.store = ExecutiveAnalyticsStore(self.repository.engine, self.repository, None, seed_demo_data=True, auto_create_schema=True)

    def tearDown(self):
        self.repository.engine.dispose()

    def batch(self):
        with self.repository.engine.connect() as connection:
            current = dict(connection.execute(select(engagements).where(engagements.c.id == "eng-isg-equities")).mappings().one())
        engagement = EngagementRow.model_validate({
            **{key: current[key] for key in EngagementRow.model_fields if key not in {"source_system", "source_record_id"}},
            "health": "AMBER", "source_system": "test-psa", "source_record_id": "project-1001",
        })
        revenue = RevenueRow(id="imported-revenue-1001", engagement_id=engagement.id, recognized_on="2026-08-31", amount=Decimal("1234.56"))
        return ExecutiveImportBatch(engagements=[engagement], revenue_records=[revenue])

    def test_dry_run_validates_without_writing(self):
        counts = import_executive_batch(self.repository.engine, self.batch(), dry_run=True)
        self.assertEqual(1, counts["engagements"])
        with self.repository.engine.connect() as connection:
            self.assertIsNone(connection.execute(select(revenue_records.c.id).where(revenue_records.c.id == "imported-revenue-1001")).scalar_one_or_none())

    def test_import_upserts_and_records_provenance(self):
        import_executive_batch(self.repository.engine, self.batch())
        with self.repository.engine.connect() as connection:
            row = connection.execute(select(engagements).where(engagements.c.id == "eng-isg-equities")).mappings().one()
            revenue = connection.execute(select(revenue_records).where(revenue_records.c.id == "imported-revenue-1001")).mappings().one()
        self.assertEqual("AMBER", row["health"])
        self.assertEqual("test-psa", row["source_system"])
        self.assertIsNotNone(row["last_synced_at"])
        self.assertEqual(Decimal("1234.56"), revenue["amount"])

    def test_unknown_canonical_reference_rejects_the_whole_batch(self):
        batch = self.batch()
        batch.engagements[0].business_unit_id = "missing-unit"
        with self.assertRaisesRegex(ValueError, "unknown business unit"):
            import_executive_batch(self.repository.engine, batch)


if __name__ == "__main__":
    unittest.main()
