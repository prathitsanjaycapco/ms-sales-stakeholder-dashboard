import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend.schema_integrity import POSTGRESQL_FOREIGN_KEYS, POSTGRESQL_INDEXES
from backend.config import settings
from backend.models import StakeholderUpdate
from backend.persistence import PersistentStakeholderRepository


DATABASE_URL = settings.database_url


@unittest.skipUnless(DATABASE_URL.startswith("postgresql"), "PostgreSQL integration URL is not configured")
class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_database_is_at_head_with_all_cross_domain_integrity_objects(self):
        with self.engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            constraints = set(connection.execute(text(
                "SELECT conname FROM pg_constraint WHERE contype = 'f'"
            )).scalars())
            indexes = set(connection.execute(text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
            )).scalars())

            self.assertEqual("0012_executive_provenance", revision)
        self.assertTrue({item[0] for item in POSTGRESQL_FOREIGN_KEYS}.issubset(constraints))
        self.assertTrue({item[0] for item in POSTGRESQL_INDEXES}.issubset(indexes))

    def test_cross_domain_foreign_key_rejects_an_orphan_without_leaving_data(self):
        invalid_id = f"validation-orphan-{uuid4().hex}"
        with self.engine.connect() as connection:
            transaction = connection.begin()
            division_id = connection.execute(text("SELECT id FROM divisions LIMIT 1")).scalar_one()
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text("UPDATE divisions SET head_stakeholder_id = :invalid WHERE id = :division"),
                    {"invalid": invalid_id, "division": division_id},
                )
            transaction.rollback()

    def test_resourcing_requirement_rejects_an_orphan_project(self):
        with self.engine.connect() as connection:
            transaction = connection.begin()
            requirement_id = connection.execute(text("SELECT id FROM resource_requirements LIMIT 1")).scalar_one()
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text("UPDATE resource_requirements SET engagement_id = :invalid WHERE id = :requirement"),
                    {"invalid": f"missing-engagement-{uuid4().hex}", "requirement": requirement_id},
                )
            transaction.rollback()

    def test_two_repository_workers_preserve_overlapping_updates(self):
        first = PersistentStakeholderRepository(DATABASE_URL, seed_demo_data=False, auto_create_schema=False)
        second = PersistentStakeholderRepository(DATABASE_URL, seed_demo_data=False, auto_create_schema=False)
        verifier = PersistentStakeholderRepository(DATABASE_URL, seed_demo_data=False, auto_create_schema=False)
        person = first.list_stakeholders(pod="ISG")[0]
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                updates = [
                    pool.submit(first.update_stakeholder, person.id, StakeholderUpdate(location="Concurrency Test Location")),
                    pool.submit(second.update_stakeholder, person.id, StakeholderUpdate(title="Concurrency Test Title")),
                ]
                for update in updates:
                    update.result(timeout=15)
            verifier.refresh_if_stale()
            current = verifier.get_stakeholder(person.id)
            self.assertEqual("Concurrency Test Location", current.location)
            self.assertEqual("Concurrency Test Title", current.title)
        finally:
            verifier.update_stakeholder(person.id, StakeholderUpdate(location=person.location, title=person.title))
            first.engine.dispose()
            second.engine.dispose()
            verifier.engine.dispose()


if __name__ == "__main__":
    unittest.main()
