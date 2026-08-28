import unittest

from fastapi.testclient import TestClient

from backend.main import app


class CriticalWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_partner_project_drills_to_same_pod_stakeholder_and_opportunity(self):
        executive = self.client.get("/api/executive/overview").json()
        project = next(item for item in executive["projectPortfolio"] if item["stakeholderId"] and item["opportunityId"])
        stakeholder = self.client.get(f"/api/stakeholders/{project['stakeholderId']}")
        opportunity = self.client.get(f"/api/opportunities/{project['opportunityId']}")
        pod_map = self.client.get(f"/api/pods/{project['pod']}/map").json()
        pod_dashboard = self.client.get(f"/api/pods/{project['pod']}/dashboard").json()["view_model"]
        self.assertEqual(200, stakeholder.status_code)
        self.assertEqual(project["stakeholderId"], stakeholder.json()["id"])
        self.assertEqual(project["opportunityId"], opportunity.json()["id"])
        self.assertIn(project["stakeholderId"], {item["id"] for item in pod_map["stakeholders"]})
        self.assertIn(project["opportunityId"], {item["id"] for item in pod_dashboard["opportunities"]})

    def test_meeting_profile_chain_and_deployment_evidence(self):
        meetings = self.client.get("/api/meetings?pod=ISG").json()
        meeting = meetings[0]
        detail = self.client.get(f"/api/meetings/{meeting['id']}").json()
        stakeholder_id = detail["stakeholder_ids"][0]
        profile_meetings = self.client.get(f"/api/stakeholders/{stakeholder_id}/meetings").json()
        self.assertIn(meeting["id"], {item["id"] for item in profile_meetings})
        reconciliation = self.client.get("/api/integrity/reconciliation").json()
        self.assertEqual("passed", reconciliation["status"], reconciliation["checks"])
        health = self.client.get("/api/health").json()
        self.assertTrue(health["persistent"])
        self.assertEqual("normalized-sql", health["repository"])


if __name__ == "__main__":
    unittest.main()
