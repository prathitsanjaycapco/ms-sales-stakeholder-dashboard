import unittest
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend.schema_integrity import POSTGRESQL_FOREIGN_KEYS, POSTGRESQL_INDEXES
from backend.config import settings


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

            self.assertEqual("0008_account_assistant", revision)
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


if __name__ == "__main__":
    unittest.main()
