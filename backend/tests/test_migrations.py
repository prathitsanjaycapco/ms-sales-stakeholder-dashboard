import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


ALEMBIC_CONFIG = Path(__file__).resolve().parents[1] / "alembic.ini"


class MigrationTests(unittest.TestCase):
    def test_revision_identifiers_fit_alembic_version_column(self):
        scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_CONFIG)))
        for revision in scripts.walk_revisions():
            self.assertLessEqual(len(revision.revision), 32, revision.revision)

    def test_fresh_schema_reaches_head_without_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "migration.db"
            config = Config(str(ALEMBIC_CONFIG))
            config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
            command.upgrade(config, "head")
            with closing(sqlite3.connect(database)) as connection:
                revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            self.assertEqual("0018_remove_account_assistant", revision)
            command.check(config)
            self.assertTrue({
                "accounts", "stakeholders", "opportunities", "pod_events", "executive_engagements",
                "resource_requirements", "resourcing_candidates", "candidate_interviews",
                "candidate_offers", "onboarding_records", "onboarding_steps",
                "idempotency_records",
            }.issubset(tables))
            self.assertEqual([], foreign_key_errors)

    def test_pod_head_migration_repairs_existing_reporting_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy-stakeholders.db"
            config = Config(str(ALEMBIC_CONFIG))
            config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
            command.upgrade(config, "0016_bench_outcome_check")
            with closing(sqlite3.connect(database)) as connection:
                # Revision 0001 historically reflects the imported metadata in
                # this project, so temporarily bypass present-day checks to
                # model rows written by the pre-0017 application.
                connection.execute("PRAGMA ignore_check_constraints = ON")
                connection.execute("INSERT INTO accounts (id, name) VALUES ('a1', 'Morgan Stanley')")
                connection.execute("INSERT INTO pods (id, account_id, name) VALUES ('ISG', 'a1', 'ISG')")
                for person_id, name in (("division-head", "Division Head"), ("unit-head", "Unit Head"), ("primary-tech", "Technology Manager"), ("business", "Business Person")):
                    connection.execute("""INSERT INTO stakeholders
                        (id, name, title, level, location, country_code, biography, source_system)
                        VALUES (?, ?, 'Leader', 'Managing Director', 'New York', 'US', '', 'legacy')""", (person_id, name))
                connection.execute("""INSERT INTO divisions
                    (id, pod_id, name, color, head_stakeholder_id)
                    VALUES ('front-office', 'ISG', 'Front Office', '#1675d1', 'division-head')""")
                connection.execute("""INSERT INTO business_units
                    (id, division_id, name, sort_order) VALUES ('equities', 'front-office', 'Equities', 0)""")
                assignment_sql = """INSERT INTO stakeholder_assignments
                    (id, stakeholder_id, pod_id, division_id, business_unit_id, team_type,
                     organizational_role, manager_stakeholder_id, is_primary_technology,
                     is_buyer, is_influencer, is_budget_holder, relationship_strength,
                     capco_contingents, tags, effective_from, is_current)
                    VALUES (?, ?, 'ISG', 'front-office', ?, ?, ?, NULL, ?, 0, 1, 0, 'Developing', 0, '[]', '2026-01-01', 1)"""
                connection.execute(assignment_sql, ("a-division", "division-head", None, "Business", "Division Head", 0))
                connection.execute(assignment_sql, ("a-unit", "unit-head", "equities", "Business", "Business Unit Head", 0))
                connection.execute(assignment_sql, ("a-tech", "primary-tech", "equities", "Technology", "Technology Stakeholder", 1))
                connection.execute(assignment_sql, ("a-business", "business", "equities", "Business", "Business Stakeholder", 0))
                connection.commit()
                connection.execute("PRAGMA ignore_check_constraints = OFF")

            command.upgrade(config, "head")
            with closing(sqlite3.connect(database)) as connection:
                pod_head = connection.execute("SELECT head_stakeholder_id FROM pods WHERE id = 'ISG'").fetchone()[0]
                managers = dict(connection.execute("""SELECT stakeholder_id, manager_stakeholder_id
                    FROM stakeholder_assignments WHERE is_current = 1"""))
                head_scope = connection.execute("""SELECT division_id, business_unit_id, manager_stakeholder_id
                    FROM stakeholder_assignments WHERE stakeholder_id = ? AND is_current = 1""", (pod_head,)).fetchone()
            self.assertEqual("isg-pod-head", pod_head)
            self.assertEqual((None, None, None), head_scope)
            self.assertEqual(pod_head, managers["division-head"])
            self.assertEqual("division-head", managers["unit-head"])
            self.assertEqual("unit-head", managers["primary-tech"])
            self.assertEqual("unit-head", managers["business"])

    def test_resourcing_workflow_maps_legacy_stages_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy-resourcing.db"
            config = Config(str(ALEMBIC_CONFIG))
            config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
            command.upgrade(config, "0012_executive_provenance")
            timestamp = "2026-08-01 12:00:00"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("""INSERT INTO resource_requirements
                    (id, pod_id, division_id, business_unit_id, engagement_id, title, role, description,
                     requested_headcount, level, location, required_skills, preferred_skills, target_start_date,
                     priority, status, request_owner_capco_employee_id, client_stakeholder_id,
                     resourcing_app_created, bench_checked, bench_outcome, resourcing_request_submitted,
                     created_at, updated_at)
                    VALUES ('role-legacy', 'ISG', 'division-1', 'unit-1', 'engagement-1', 'Legacy role',
                            'Engineer', '', 4, 'Consultant', 'New York', '[]', '[]', '2026-10-01',
                            'HIGH', 'SOURCING', 'employee-1', 'stakeholder-1', 1, 0, NULL, 0, ?, ?)""", (timestamp, timestamp))
                legacy = {
                    "resume": "IDENTIFIED",
                    "capco": "SUBMITTED_TO_MS",
                    "ms": "INTERVIEWING",
                    "selected-board": "SELECTED",
                    "selected-no-board": "SELECTED",
                }
                for candidate_id, stage in legacy.items():
                    connection.execute("""INSERT INTO resourcing_candidates
                        (id, resource_requirement_id, candidate_type, first_name, last_name, level, location,
                         skills, stage, capco_reviewer_id, date_identified, match_score, created_at, updated_at)
                        VALUES (?, 'role-legacy', 'EXTERNAL', ?, 'Candidate', 'Consultant', 'New York', '[]',
                                ?, 'employee-1', '2026-08-01', 80, ?, ?)""", (candidate_id, candidate_id, stage, timestamp, timestamp))
                    connection.execute("""INSERT INTO candidate_stage_history
                        (id, candidate_id, stage, entered_at, note) VALUES (?, ?, ?, ?, '')""",
                        (f"history-{candidate_id}", candidate_id, stage, timestamp))
                connection.execute("""INSERT INTO onboarding_records
                    (id, candidate_id, overall_status, created_at, updated_at)
                    VALUES ('board-legacy', 'selected-board', 'IN_PROGRESS', ?, ?)""", (timestamp, timestamp))
                connection.commit()

            command.upgrade(config, "head")
            with closing(sqlite3.connect(database)) as connection:
                stages = dict(connection.execute("SELECT id, stage FROM resourcing_candidates"))
                old_open_rows = connection.execute("""SELECT COUNT(*) FROM candidate_stage_history
                    WHERE id LIKE 'history-%' AND exited_at IS NULL""").fetchone()[0]
                migration_notes = dict(connection.execute("""SELECT candidate_id, note FROM candidate_stage_history
                    WHERE id LIKE 'migration-0013-%'"""))
                checklist = connection.execute("""SELECT resourcing_app_created, bench_checked, bench_outcome, country_code
                    FROM resource_requirements WHERE id = 'role-legacy'""").fetchone()
            self.assertEqual({
                "resume": "RESUME_REVIEW",
                "capco": "CAPCO_INTERVIEW",
                "ms": "MS_INTERVIEW",
                "selected-board": "ONBOARDING",
                "selected-no-board": "OFFER",
            }, stages)
            self.assertEqual(0, old_open_rows)
            self.assertTrue(all("Migrated from legacy stage" in note for note in migration_notes.values()))
            self.assertEqual((1, 1, "EXISTING_PIPELINE", "US"), checklist)


if __name__ == "__main__":
    unittest.main()
