import unittest

from backend.models import DocumentLinkCreate, DocumentLinkUpdate, NoteCreate, OpportunityCreate, StakeholderCreate, StakeholderUpdate
from backend.repository import ConflictError, StakeholderRepository


class StakeholderRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = StakeholderRepository()

    def test_seed_has_varied_enterprise_data(self):
        records = self.repository.list_stakeholders(pod="ISG")
        self.assertGreater(len(records), 100)
        self.assertGreater(len({record.location for record in records}), 5)
        self.assertEqual({record.relationship_strength for record in records}, {"Strong", "Medium", "Developing", "Unknown"})
        self.assertTrue(any(record.manager_id is None and record.organizational_role == "Business Stakeholder" for record in records))
        self.assertTrue(any(record.is_primary_technology for record in records))

    def test_map_uses_independent_business_units_and_filters(self):
        map_data = self.repository.build_map("ISG")
        self.assertEqual([len(division["units"]) for division in map_data.divisions], [4, 4, 3])
        buyer_map = self.repository.build_map("ISG", division="Front Office", role="Buyer")
        self.assertTrue(buyer_map.stakeholders)
        self.assertTrue(all(item.division == "Front Office" and item.is_buyer for item in buyer_map.stakeholders))

    def test_seeded_and_created_stakeholders_are_editable(self):
        unit = next(iter(self.repository.units.values()))
        manager = self.repository.get_stakeholder(unit["business_stakeholder_ids"][0])
        created = self.repository.create_stakeholder(StakeholderCreate(
            name="Morgan Test", title="Director, Strategy", pod=manager.pod, division=manager.division,
            business_unit=manager.business_unit, manager_id=manager.id, tags=["Strategy"],
        ))
        updated = self.repository.update_stakeholder(created.id, StakeholderUpdate(is_buyer=True, budget_amount=1_500_000))
        self.assertTrue(updated.is_buyer)
        self.assertEqual(updated.budget_amount, 1_500_000)

    def test_reporting_lines_reject_cycles(self):
        unit = next(iter(self.repository.units.values()))
        lead = self.repository.get_stakeholder(unit["business_stakeholder_ids"][0])
        branch = next(item for item in self.repository.stakeholders.values() if item.manager_id == lead.id)
        with self.assertRaises(ConflictError):
            self.repository.update_reporting_line(lead.id, branch.id, "Invalid cycle")

    def test_notes_opportunities_and_primary_technology_history(self):
        unit = next(iter(self.repository.units.values()))
        stakeholder_id = unit["business_stakeholder_ids"][0]
        note = self.repository.create_note(stakeholder_id, NoteCreate(body="Useful account intelligence."))
        self.assertEqual(self.repository.list_notes(stakeholder_id)[0].id, note.id)
        opportunity = self.repository.create_opportunity(OpportunityCreate(
            name="Workflow modernization", stakeholder_ids=[stakeholder_id], estimated_value=900_000,
        ))
        self.assertIn(opportunity.id, self.repository.opportunities)
        replacement_id = unit["technology_stakeholder_ids"][1]
        result = self.repository.set_primary_technology(unit["id"], replacement_id, "Succession planning")
        self.assertEqual(result["status"], "saved")
        self.assertTrue(self.repository.list_history(replacement_id))

    def test_document_links_are_editable_and_canonical(self):
        stakeholder = self.repository.list_stakeholders(pod="ISG")[0]
        document = self.repository.create_document(stakeholder.id, DocumentLinkCreate(
            title="Decision brief", url="https://example.com/decision-brief", document_type="Meeting Brief",
            description="Pre-read for the next decision meeting", owner="Priya Shah",
        ))
        self.assertEqual(stakeholder.id, document.stakeholder_id)
        updated = self.repository.update_document(document.id, DocumentLinkUpdate(title="Updated decision brief"))
        self.assertEqual("Updated decision brief", updated.title)
        self.assertIn(document.id, {item.id for item in self.repository.list_documents(stakeholder.id)})
        self.repository.delete_document(document.id)
        self.assertNotIn(document.id, self.repository.documents)

    def test_uploaded_documents_can_target_meetings(self):
        meeting = self.repository.list_meetings()[0]
        document = self.repository.create_meeting_document(meeting.id, DocumentLinkCreate(
            title="Meeting evidence pack",
            stored_name="safe-test-file.pdf",
            file_name="evidence-pack.pdf",
            content_type="application/pdf",
            file_size=2048,
            sharepoint_url="https://example.sharepoint.com/evidence-pack",
            document_type="Meeting Brief",
        ))
        self.assertEqual(meeting.id, document.meeting_id)
        self.assertIsNone(document.stakeholder_id)
        self.assertEqual(f"/api/documents/{document.id}/download", document.download_url)
        self.assertIn(document.id, {item.id for item in self.repository.list_meeting_documents(meeting.id)})


if __name__ == "__main__":
    unittest.main()
