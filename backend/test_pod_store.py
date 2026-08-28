import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.pod_store import PodOperatingStore
from backend.models import MeetingCreate
from backend.repository import StakeholderRepository


class PodOperatingStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = StakeholderRepository()
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.store = PodOperatingStore(cls.engine, cls.repository)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_seed_is_substantial_and_idempotent(self):
        counts = self.store.counts()
        self.assertGreaterEqual(counts["pod_events"], 300)
        self.assertGreaterEqual(counts["pod_event_attendees"], 500)
        self.assertEqual(72, counts["pod_tasks"])
        self.assertEqual(24, counts["pod_critical_items"])
        self.assertEqual(36, counts["pod_milestones"])

        PodOperatingStore(self.engine, self.repository)
        self.assertEqual(counts, self.store.counts())

    def test_dashboard_is_fully_linked_to_canonical_records(self):
        view = self.store.dashboard("ISG", "week", date(2026, 8, 24))
        for section in (
            "people", "meetings", "opportunities", "criticalItems", "tasks",
            "relationships", "milestones", "focus", "health",
        ):
            self.assertTrue(view[section], section)

        people = {item["id"] for item in view["people"]}
        self.assertTrue(all(event["stakeholderId"] in people for event in view["meetings"]))
        self.assertTrue(all(event["capcoAttendees"] for event in view["meetings"]))
        self.assertTrue(all(" " in name for event in view["meetings"] for name in event["capcoAttendees"]))
        self.assertTrue(all(event["openActions"] and event["discussionTopics"] for event in view["meetings"]))
        self.assertTrue(all(item["stakeholderId"] in self.repository.stakeholders for item in view["criticalItems"]))
        self.assertTrue(all(item["capcoOwner"] and item["msOwner"] for item in view["criticalItems"]))

    def test_all_pods_and_tag_filter_use_one_linked_portfolio(self):
        start = date(2026, 8, 24)
        individual = [self.store.dashboard(pod, "week", start) for pod in ("ISG", "Wealth Management", "MSIM")]
        combined = self.store.dashboard("All", "week", start)
        self.assertEqual(sum(len(view["meetings"]) for view in individual), len(combined["meetings"]))
        self.assertEqual({"ISG", "Wealth Management", "MSIM"}, {item["pod"] for item in combined["meetings"]})

        ai = self.store.dashboard("All", "week", start, "AI")
        for section in ("people", "meetings", "upcomingPrep", "opportunities", "criticalItems", "tasks", "relationships", "milestones"):
            self.assertTrue(all("AI" in item["tags"] for item in ai[section]), section)
        self.assertTrue(ai["people"])
        self.assertTrue(ai["opportunities"])

    def test_relationship_priority_commitments_and_health_are_computed(self):
        view = self.store.dashboard("All", "week", date(2026, 8, 24))
        risk_scores = [item["riskScore"] for item in view["relationships"]]
        self.assertEqual(sorted(risk_scores, reverse=True), risk_scores)
        self.assertEqual(len(view["criticalItems"]) + len(view["milestones"]), len(view["commitments"]))
        deadline_fields = {
            "id", "pod", "deadline", "title", "category", "priority", "owner",
            "stakeholder", "stakeholderId", "opportunityId", "status", "sourceType", "tags",
        }
        self.assertTrue(all(set(item) == deadline_fields for item in view["commitments"]))
        self.assertEqual(
            sorted(item["deadline"] for item in view["commitments"]),
            [item["deadline"] for item in view["commitments"]],
        )
        self.assertTrue(all(
            item["days"] is None or item["days"] == max(0, (date.today() - date.fromisoformat(item["lastMeeting"])).days)
            for item in view["relationships"]
        ))
        self.assertEqual(
            len(view["relationshipAttention"]), view["summary"]["relationshipAttentionCount"]
        )
        self.assertEqual(len(view["meetings"]), view["summary"]["meetingCount"])
        self.assertEqual(len(view["commitments"]), view["summary"]["deadlineCount"])
        self.assertTrue(all(item["formula"] and item["dataSource"] == "Live SQL operating records" for item in view["health"]))
        self.assertTrue(all(0 <= item["value"] <= 100 for item in view["health"]))

    def test_relationship_recency_updates_from_a_new_linked_meeting(self):
        repository = StakeholderRepository()
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        store = PodOperatingStore(engine, repository)
        stakeholder = repository.list_stakeholders(pod="ISG")[0]
        meeting = repository.create_meeting(MeetingCreate(
            subject="Newest persisted relationship meeting",
            meeting_date=datetime.now(timezone.utc) - timedelta(hours=1),
            summary="Latest relationship checkpoint.",
            stakeholder_ids=[stakeholder.id],
            organizer="Priya Shah",
            outcome="Next step agreed",
            next_steps=["Confirm deadline"],
            tags=["Relationship"],
        ))
        store.create_meeting_event("ISG", meeting, {
            "duration_minutes": 45,
            "event_type": "client",
            "capco_attendees": ["Priya Shah"],
            "prep_required": False,
        })
        view = store.dashboard("ISG", "week", date.today() - timedelta(days=date.today().weekday()))
        relationship = next(item for item in view["relationships"] if item["stakeholderId"] == stakeholder.id)
        person = next(item for item in view["people"] if item["id"] == stakeholder.id)
        self.assertEqual(meeting.meeting_date.date().isoformat(), relationship["lastMeeting"])
        self.assertEqual(relationship["lastMeeting"], person["lastMeeting"])
        self.assertEqual(meeting.id, relationship["latestMeetingId"])
        self.assertEqual(0, relationship["days"])
        self.assertFalse(relationship["needsAttention"])
        engine.dispose()

    def test_meeting_brief_is_grounded_in_linked_account_records(self):
        view = self.store.dashboard("ISG", "week", date(2026, 8, 24))
        meeting = view["meetings"][0]
        brief = self.store.generate_meeting_brief(meeting["meetingId"])
        self.assertEqual("Ready", brief["status"])
        self.assertEqual(meeting["stakeholderId"], brief["meeting"]["stakeholderId"])
        self.assertTrue(brief["executiveSummary"])
        self.assertTrue(brief["recommendedQuestions"])
        self.assertGreaterEqual(brief["sourceSummary"]["stakeholderNotes"], 1)
        self.assertGreaterEqual(brief["sourceSummary"]["priorMeetings"], 1)

    def test_every_pod_view_profile_target_resolves_to_the_same_canonical_pool(self):
        for pod in ("ISG", "Wealth Management", "MSIM"):
            view = self.store.dashboard(pod, "week", date(2026, 8, 24))
            linked_ids = {
                item["stakeholderId"]
                for section in ("meetings", "criticalItems", "relationships", "opportunities")
                for item in view[section]
                if item.get("stakeholderId")
            }
            self.assertTrue(linked_ids, pod)
            for stakeholder_id in linked_ids:
                record = self.repository.get_stakeholder(stakeholder_id)
                self.assertEqual(stakeholder_id, record.id)
                self.assertEqual(pod, record.pod)

    def test_task_focus_and_critical_mutations_are_durable(self):
        task = self.store.list_tasks("ISG")[0]
        updated = self.store.update_task("ISG", task["id"], {"status": "Done"})
        self.assertEqual("Done", updated["status"])
        self.assertIsNotNone(updated["completed_at"])
        self.assertEqual("Done", next(item for item in self.store.list_tasks("ISG") if item["id"] == task["id"])["status"])

        priorities = ["Win the decision", "Protect delivery", "Expand coverage"]
        self.store.update_focus("ISG", priorities)
        month = self.store.dashboard("ISG", "month", date(2026, 8, 1))
        self.assertEqual(priorities, month["focus"])

        critical_id = month["criticalItems"][0]["id"]
        self.store.update_critical_status("ISG", critical_id, "Resolved")
        refreshed = self.store.dashboard("ISG", "month", date(2026, 8, 1))
        self.assertNotIn(critical_id, {item["id"] for item in refreshed["criticalItems"]})

    def test_created_meetings_and_critical_items_feed_dashboard(self):
        repository = StakeholderRepository()
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        store = PodOperatingStore(engine, repository)
        stakeholder = repository.list_stakeholders(pod="ISG")[0]
        meeting = repository.create_meeting(MeetingCreate(
            subject="User-created decision meeting",
            meeting_date=datetime(2026, 8, 28, 10, tzinfo=timezone.utc),
            summary="Validate the decision path.",
            stakeholder_ids=[stakeholder.id],
            organizer="Priya Shah",
            outcome="Decision required",
            next_steps=["Send the evidence pack"],
            tags=["AI", "Decision"],
        ))
        event = store.create_meeting_event("ISG", meeting, {
            "duration_minutes": 45,
            "event_type": "client",
            "capco_attendees": ["Priya Shah", "Rachel Chen"],
            "prep_required": True,
        })
        critical = store.create_critical_item("ISG", {
            "title": "Decision dependency",
            "description": "Client decision is required before mobilization.",
            "item_type": "DECISION",
            "severity": "RED",
            "capco_owner": "Priya Shah",
            "due_date": date(2026, 8, 29),
            "stakeholder_id": stakeholder.id,
            "opportunity_id": None,
            "tags": ["AI", "Delivery"],
        }, "critical-test-created")
        updated_event = store.update_meeting_event("ISG", meeting.id, {
            "subject": "Updated decision meeting",
            "duration_minutes": 75,
            "capco_attendees": ["Rachel Chen", "Priya Shah"],
            "outcome": "Decision confirmed",
            "tags": ["AI", "Executive"],
        })
        store.update_critical_item("ISG", critical["id"], {
            "title": "Updated decision dependency",
            "severity": "AMBER",
            "capco_owner": "Rachel Chen",
            "tags": ["AI", "Risk"],
        })
        dashboard = store.dashboard("ISG", "week", date(2026, 8, 24))
        created_event = next(item for item in dashboard["meetings"] if item["id"] == event["id"])
        self.assertEqual(meeting.id, created_event["meetingId"])
        self.assertEqual("Updated decision meeting", updated_event["title"])
        self.assertEqual("Updated decision meeting", repository.meetings[meeting.id].subject)
        self.assertEqual(["Rachel Chen", "Priya Shah"], created_event["capcoAttendees"])
        self.assertIn("Executive", created_event["tags"])
        self.assertIn(critical["id"], {item["id"] for item in dashboard["criticalItems"]})
        updated_critical = next(item for item in dashboard["criticalItems"] if item["id"] == critical["id"])
        self.assertEqual("Updated decision dependency", updated_critical["title"])
        self.assertEqual("Rachel Chen", updated_critical["capcoOwner"])
        self.assertIn("Risk", updated_critical["tags"])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
