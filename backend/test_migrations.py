import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


class MigrationTests(unittest.TestCase):
    def test_revision_identifiers_fit_alembic_version_column(self):
        scripts = ScriptDirectory.from_config(Config("alembic.ini"))
        for revision in scripts.walk_revisions():
            self.assertLessEqual(len(revision.revision), 32, revision.revision)

    def test_fresh_schema_reaches_head_without_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "migration.db"
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
            command.upgrade(config, "head")
            with closing(sqlite3.connect(database)) as connection:
                revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            self.assertEqual("0012_executive_provenance", revision)
            command.check(config)
            self.assertTrue({
                "accounts", "stakeholders", "opportunities", "pod_events", "executive_engagements",
                "assistant_document_chunks", "assistant_conversations", "assistant_messages",
                "resource_requirements", "resourcing_candidates", "candidate_interviews",
                "candidate_offers", "onboarding_records", "onboarding_steps",
                "idempotency_records",
            }.issubset(tables))
            self.assertEqual([], foreign_key_errors)


if __name__ == "__main__":
    unittest.main()
