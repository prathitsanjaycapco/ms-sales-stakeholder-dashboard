import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect, select, text

from backend.canonical_schema import stakeholder_assignments
from backend.executive_store import ExecutiveAnalyticsStore
from backend.models import DocumentLinkCreate, MeetingCreate, NoteCreate, StakeholderCreate, StakeholderUpdate
from backend.persistence import PersistentStakeholderRepository
from backend.pod_store import PodOperatingStore
from backend.resourcing_store import ResourcingStore


class PersistentStakeholderRepositoryTests(unittest.TestCase):
    @staticmethod
    def _business_fingerprint(engine):
        table_names = sorted(name for name in inspect(engine).get_table_names() if name not in {"alembic_version", "idempotency_records", "audit_events"})
        with engine.connect() as connection:
            return {
                name: [tuple(row) for row in connection.execute(text(f'SELECT * FROM "{name}"')).all()]
                for name in table_names
            }

    def test_store_construction_is_read_only_after_explicit_seed(self):
        engine_url = "sqlite+pysqlite:///:memory:"
        repository = PersistentStakeholderRepository(engine_url, seed_demo_data=True, auto_create_schema=True)
        executive = ExecutiveAnalyticsStore(repository.engine, repository, None, seed_demo_data=True, auto_create_schema=True)
        pod = PodOperatingStore(repository.engine, repository, seed_demo_data=True, auto_create_schema=True)
        executive.pod_store = pod
        ResourcingStore(repository.engine, repository, seed_demo_data=True, auto_create_schema=True)
        before = self._business_fingerprint(repository.engine)

        restarted = PersistentStakeholderRepository(engine_url, engine=repository.engine, seed_demo_data=False, auto_create_schema=True)
        restarted_executive = ExecutiveAnalyticsStore(repository.engine, restarted, None, seed_demo_data=False, auto_create_schema=True)
        restarted_pod = PodOperatingStore(repository.engine, restarted, seed_demo_data=False, auto_create_schema=True)
        restarted_executive.pod_store = restarted_pod
        ResourcingStore(repository.engine, restarted, seed_demo_data=False, auto_create_schema=True)

        self.assertEqual(before, self._business_fingerprint(repository.engine))
        repository.engine.dispose()

    def test_reporting_change_closes_previous_assignment_version(self):
        repository = PersistentStakeholderRepository("sqlite+pysqlite:///:memory:", seed_demo_data=True, auto_create_schema=True)
        person = next(item for item in repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Stakeholder")
        replacement_manager = next(
            item for item in repository.list_stakeholders(pod="ISG")
            if item.id != person.id and item.organizational_role == "Business Stakeholder"
        )
        previous_assignment_id = person.assignment_id
        repository.update_reporting_line(person.id, replacement_manager.id, "History verification")
        with repository.engine.connect() as connection:
            rows = connection.execute(
                select(stakeholder_assignments).where(stakeholder_assignments.c.stakeholder_id == person.id)
            ).mappings().all()
        self.assertEqual(2, len(rows))
        prior = next(row for row in rows if row["id"] == previous_assignment_id)
        current = next(row for row in rows if row["is_current"])
        self.assertFalse(prior["is_current"])
        self.assertIsNotNone(prior["effective_to"])
        self.assertTrue(current["id"].startswith("assignment-version-"))
        repository.engine.dispose()

    def test_cross_unit_reporting_change_is_durable(self):
        repository = PersistentStakeholderRepository("sqlite+pysqlite:///:memory:", seed_demo_data=True, auto_create_schema=True)
        division_head = next(item for item in repository.list_stakeholders(pod="ISG") if item.organizational_role == "Division Head")
        report = next(item for item in repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Unit Head" and item.business_unit != division_head.business_unit)
        repository.update_reporting_line(report.id, division_head.id, "Canonical division structure")
        self.assertEqual(division_head.id, repository.get_stakeholder(report.id).manager_id)
        with repository.engine.connect() as connection:
            current = connection.execute(
                select(stakeholder_assignments.c.manager_stakeholder_id).where(
                    stakeholder_assignments.c.stakeholder_id == report.id,
                    stakeholder_assignments.c.is_current,
                )
            ).scalar_one()
        self.assertEqual(division_head.id, current)
        repository.engine.dispose()

    def test_meeting_projection_failure_rolls_back_canonical_record(self):
        repository = PersistentStakeholderRepository("sqlite+pysqlite:///:memory:", seed_demo_data=True, auto_create_schema=True)
        stakeholder = repository.list_stakeholders(pod="ISG")[0]
        before = set(repository.meetings)
        payload = MeetingCreate(
            subject="Atomic meeting", meeting_date=datetime.now(timezone.utc),
            stakeholder_ids=[stakeholder.id], summary="", organizer="Test",
            outcome="Follow-up required",
        )

        def fail_projection(_connection, _meeting):
            raise RuntimeError("calendar write failed")

        with self.assertRaisesRegex(RuntimeError, "calendar write failed"):
            repository.create_meeting_transactional(payload, fail_projection)
        self.assertEqual(before, set(repository.meetings))
        repository.engine.dispose()

    def test_mutations_survive_repository_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "stakeholders.db"
            database_url = f"sqlite:///{database_path.as_posix()}"
            first = PersistentStakeholderRepository(database_url, seed_demo_data=True, auto_create_schema=True)
            stakeholder = first.list_stakeholders(pod="ISG", search="Daniel Kim")[0]
            first.update_stakeholder(stakeholder.id, StakeholderUpdate(location="Chicago, USA"))
            note = first.create_note(
                stakeholder.id,
                NoteCreate(body="Persistence verification", category="General", author="Test Suite"),
            )
            document = first.create_document(stakeholder.id, DocumentLinkCreate(
                title="Persistent account plan", url="https://example.com/account-plan", document_type="Account Plan",
            ))
            meeting = first.list_meetings(stakeholder.id)[0]
            meeting_document = first.create_meeting_document(meeting.id, DocumentLinkCreate(
                title="Persistent meeting brief", stored_name="persistent-brief.pdf", file_name="brief.pdf",
                file_size=1024, content_type="application/pdf", document_type="Meeting Brief",
            ))
            replacement = first.create_stakeholder(StakeholderCreate(
                name="Taylor Persistence",
                title="VP, Equities Technology",
                pod="ISG",
                division="Front Office",
                business_unit="Equities",
                team_type="Technology",
                is_primary_technology=True,
            ))
            first.save_dashboard_task("ISG", {"id": "custom-1", "title": "Validate cockpit", "status": "Open", "due": "2026-08-28"})
            first.save_dashboard_focus("ISG", ["Protect delivery", "Advance pipeline"])
            first.update_dashboard_critical_status("ISG", "c1", "Resolved")
            first.update_dashboard_task_status("ISG", "t1", "Done")
            first.engine.dispose()

            second = PersistentStakeholderRepository(database_url, seed_demo_data=False, auto_create_schema=False)
            restored = second.get_stakeholder(stakeholder.id)
            restored_notes = second.list_notes(stakeholder.id)
            self.assertEqual(restored.location, "Chicago, USA")
            self.assertTrue(any(item.id == note.id and item.body == "Persistence verification" for item in restored_notes))
            self.assertTrue(any(item.id == document.id for item in second.list_documents(stakeholder.id)))
            self.assertTrue(any(item.id == meeting_document.id for item in second.list_meeting_documents(meeting.id)))
            self.assertTrue(second.get_stakeholder(replacement.id).is_primary_technology)
            self.assertFalse(second.get_stakeholder(stakeholder.id).is_primary_technology)
            self.assertGreater(len(second.list_stakeholders(pod="ISG")), 100)
            self.assertEqual("Validate cockpit", second.dashboard_task_records["ISG:custom-1"]["title"])
            self.assertEqual(["Protect delivery", "Advance pipeline"], second.dashboard_focus["ISG"])
            self.assertEqual("Resolved", second.dashboard_critical_statuses["ISG:c1"])
            self.assertEqual("Done", second.dashboard_task_statuses["ISG:t1"])
            second.engine.dispose()

    def test_two_repository_instances_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "concurrent.db"
            database_url = f"sqlite:///{database_path.as_posix()}"
            first = PersistentStakeholderRepository(database_url, seed_demo_data=True, auto_create_schema=True)
            second = PersistentStakeholderRepository(database_url, seed_demo_data=False, auto_create_schema=False)
            first_person, second_person = first.list_stakeholders(pod="ISG")[:2]

            first.update_stakeholder(first_person.id, StakeholderUpdate(location="Chicago, USA"))
            second.update_stakeholder(second_person.id, StakeholderUpdate(location="Boston, USA"))
            first.refresh_if_stale()

            self.assertEqual("Chicago, USA", first.get_stakeholder(first_person.id).location)
            self.assertEqual("Boston, USA", first.get_stakeholder(second_person.id).location)

            second.update_stakeholder(first_person.id, StakeholderUpdate(title="Concurrent title update"))
            first.refresh_if_stale()
            self.assertEqual("Chicago, USA", first.get_stakeholder(first_person.id).location)
            self.assertEqual("Concurrent title update", first.get_stakeholder(first_person.id).title)
            first.engine.dispose()
            second.engine.dispose()


if __name__ == "__main__":
    unittest.main()
