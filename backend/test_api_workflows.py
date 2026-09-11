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

    def test_stakeholder_map_and_filters_support_a_scope_less_pod_head(self):
        pod_map = self.client.get("/api/pods/ISG/map")
        filters = self.client.get("/api/pods/ISG/filters")

        self.assertEqual(200, pod_map.status_code, pod_map.text)
        self.assertEqual(200, filters.status_code, filters.text)
        self.assertIsNotNone(pod_map.json()["pod_head_stakeholder_id"])
        self.assertNotIn(None, filters.json()["business_units"])

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

    def test_resourcing_metrics_reconcile_across_executive_pod_and_project_views(self):
        resourcing = self.client.get("/api/resourcing/overview?pod=ISG").json()
        executive = self.client.get("/api/executive/weekly?pod=ISG").json()
        pod = self.client.get("/api/pods/ISG/dashboard").json()["view_model"]
        self.assertEqual(resourcing["metrics"], executive["resourcing"])
        self.assertEqual(resourcing["metrics"], pod["resourcing"])
        self.assertEqual(resourcing["critical_items"], pod["resourcingSummary"]["criticalItems"])
        self.assertTrue(any(item["type"].startswith("STAFFING_") for item in pod["criticalItems"]))
        role = self.client.get("/api/resource-requirements?pod=ISG").json()[0]
        project = self.client.get(f"/api/engagements/{role['engagement_id']}").json()
        self.assertIn(role["id"], {item["id"] for item in project["resourcing"]["requirements"]})

    def test_engagement_detail_reconciles_delivery_commercial_and_people_records(self):
        executive = self.client.get("/api/executive/overview").json()
        summary = next(item for item in executive["projectPortfolio"] if item["opportunityId"])
        detail = self.client.get(f"/api/engagements/{summary['id']}")
        self.assertEqual(200, detail.status_code)
        project = detail.json()
        self.assertEqual(summary["id"], project["engagement"]["id"])
        self.assertEqual(summary["opportunityId"], project["opportunity"]["id"])
        self.assertEqual(summary["teamSize"], len(project["team"]))
        self.assertIn("milestones", project)
        self.assertIn("revenue", project)
        self.assertIn("risks", project)
        self.assertTrue(all(item["engagement_id"] == summary["id"] for item in project["milestones"]))
        self.assertTrue(all(item["engagement_id"] == summary["id"] for item in project["revenue"]))
        self.assertTrue(all(item["engagement_id"] == summary["id"] for item in project["risks"]))


if __name__ == "__main__":
    unittest.main()
