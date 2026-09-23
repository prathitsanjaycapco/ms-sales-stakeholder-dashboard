import unittest

from app.models import DocumentLinkCreate, DocumentLinkUpdate, NoteCreate, OpportunityCreate, StakeholderCreate, StakeholderUpdate
from app.repository import ConflictError, StakeholderRepository


class StakeholderRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = StakeholderRepository()

    def test_seed_has_varied_enterprise_data(self):
        records = self.repository.list_stakeholders(pod="ISG")
        self.assertGreater(len(records), 100)
        self.assertGreater(len({record.location for record in records}), 5)
        self.assertEqual({record.relationship_strength for record in records}, {"Strong", "Medium", "Developing", "Unknown"})
        managerless = [record for record in records if record.manager_id is None]
        self.assertEqual(1, len(managerless))
        self.assertEqual("Pod Head", managerless[0].organizational_role)
        self.assertEqual(self.repository.pod_heads["ISG"], managerless[0].id)
        self.assertTrue(any(record.is_primary_technology for record in records))

    def test_seeded_hierarchy_uses_canonical_heads(self):
        for pod, expected_name in {
            "ISG": "Dan Simkowitz",
            "Wealth Management": "Jed Finn",
            "MSIM": "Ben Huneke",
        }.items():
            people = self.repository.list_stakeholders(pod=pod)
            pod_head = self.repository.get_stakeholder(self.repository.pod_heads[pod])
            self.assertEqual(expected_name, pod_head.name)
            self.assertIsNone(pod_head.manager_id)
            self.assertTrue(all(
                item.manager_id == pod_head.id
                for item in people
                if item.organizational_role == "Division Head"
            ))
            self.assertTrue(all(
                item.manager_id is not None
                for item in people
                if item.organizational_role != "Pod Head"
            ))

    def test_pod_head_change_reparents_division_heads(self):
        current = self.repository.get_stakeholder(self.repository.pod_heads["ISG"])
        replacement = next(
            item for item in self.repository.list_stakeholders(pod="ISG")
            if item.organizational_role == "Business Stakeholder"
            and not any(report.manager_id == item.id for report in self.repository.stakeholders.values())
        )
        result = self.repository.set_pod_head("ISG", replacement.id, "Leadership transition")
        self.assertEqual(replacement.id, result["head_stakeholder_id"])
        self.assertTrue(all(
            item.manager_id == replacement.id
            for item in self.repository.list_stakeholders(pod="ISG")
            if item.organizational_role == "Division Head"
        ))
        self.assertIsNotNone(current.manager_id)
        self.assertEqual(
            [replacement.id],
            [item.id for item in self.repository.list_stakeholders(pod="ISG") if item.manager_id is None],
        )

    def test_map_uses_independent_business_units_and_filters(self):
        map_data = self.repository.build_map("ISG")
        self.assertEqual([len(division["units"]) for division in map_data.divisions], [4, 4, 3])
        buyer_map = self.repository.build_map("ISG", division="Front Office", role="Buyer")
        self.assertTrue(buyer_map.stakeholders)
        self.assertTrue(all(item.division == "Front Office" and item.is_buyer for item in buyer_map.stakeholders))

        filter_options = self.repository.filter_options("ISG")
        self.assertNotIn(None, filter_options["business_units"])
        self.assertNotIn("Division Leadership", filter_options["business_units"])
        self.assertTrue(filter_options["business_units"])

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

    def test_reporting_lines_allow_cross_unit_managers_within_a_pod(self):
        division_head = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Division Head")
        report = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Unit Head" and item.business_unit != division_head.business_unit)
        result = self.repository.update_reporting_line(report.id, division_head.id, "Align unit reporting to division head")
        self.assertEqual(division_head.id, result["manager_id"])
        self.assertEqual(division_head.id, self.repository.get_stakeholder(report.id).manager_id)

    def test_stakeholder_creation_allows_a_same_pod_cross_unit_manager(self):
        manager = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Division Head")
        created = self.repository.create_stakeholder(StakeholderCreate(
            name="Cross Unit Report", title="Director, Strategy", pod="ISG", division="Front Office",
            business_unit="Equities", manager_id=manager.id,
        ))
        self.assertEqual(manager.id, created.manager_id)

    def test_reporting_lines_reject_cross_pod_managers(self):
        report = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Unit Head")
        manager = next(item for item in self.repository.list_stakeholders(pod="MSIM") if item.organizational_role == "Division Head")
        with self.assertRaises(ConflictError):
            self.repository.update_reporting_line(report.id, manager.id, "Invalid cross-pod reporting")

    def test_reporting_lines_reject_missing_managers_and_invalid_head_links(self):
        business = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Stakeholder")
        division_head = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Division Head")
        wrong_manager = next(item for item in self.repository.list_stakeholders(pod="ISG") if item.organizational_role == "Business Stakeholder")
        with self.assertRaises(ConflictError):
            self.repository.update_reporting_line(business.id, None, "Invalid orphan")
        with self.assertRaises(ConflictError):
            self.repository.update_reporting_line(division_head.id, wrong_manager.id, "Invalid division head")

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
