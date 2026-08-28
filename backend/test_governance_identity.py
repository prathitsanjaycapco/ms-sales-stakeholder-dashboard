import unittest

from fastapi.testclient import TestClient

from backend.main import app


class GovernanceAndIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_employee_and_engagement_profiles_are_joined(self):
        employees = self.client.get("/api/employees")
        self.assertEqual(200, employees.status_code)
        self.assertGreaterEqual(len(employees.json()), 8)
        employee_id = employees.json()[0]["id"]
        profile = self.client.get(f"/api/employees/{employee_id}/profile")
        self.assertEqual(200, profile.status_code)
        self.assertIn("assignments", profile.json())
        self.assertIn("stakeholder_relationships", profile.json())

        engagement = self.client.get("/api/engagements/eng-isg-equities")
        self.assertEqual(200, engagement.status_code)
        self.assertEqual("eng-isg-equities", engagement.json()["engagement"]["id"])
        self.assertTrue(engagement.json()["team"])
        self.assertTrue(engagement.json()["stakeholders"])

    def test_reader_is_read_only_and_successful_mutation_is_audited(self):
        reader_headers = {"X-Development-Subject": "read-test", "X-Development-Roles": "Reader"}
        session = self.client.get("/api/session", headers=reader_headers)
        self.assertEqual({"read": True, "write": False, "admin": False}, session.json()["permissions"])

        tasks = self.client.get("/api/pods/ISG/tasks", headers=reader_headers).json()
        original_status = tasks[0]["status"]
        changed_status = "Open" if original_status == "In Progress" else "In Progress"
        denied = self.client.patch(
            f"/api/pods/ISG/tasks/{tasks[0]['id']}",
            headers=reader_headers,
            json={"status": changed_status},
        )
        self.assertEqual(403, denied.status_code)

        written = self.client.patch(
            f"/api/pods/ISG/tasks/{tasks[0]['id']}",
            headers={"X-Development-Subject": "audit-test", "X-Development-Roles": "Account Admin"},
            json={"status": changed_status},
        )
        self.assertEqual(200, written.status_code)
        audit_id = written.headers.get("X-Audit-Event-ID")
        self.assertTrue(audit_id)
        history = self.client.get(
            "/api/audit-events?limit=10",
            headers={"X-Development-Roles": "Account Admin"},
        )
        self.assertEqual(200, history.status_code)
        self.assertIn(audit_id, {item["id"] for item in history.json()})
        event = next(item for item in history.json() if item["id"] == audit_id)
        self.assertEqual("task", event["entity_type"])
        self.assertEqual(tasks[0]["id"], event["entity_id"])
        restored = self.client.patch(
            f"/api/pods/ISG/tasks/{tasks[0]['id']}",
            headers={"X-Development-Subject": "audit-test", "X-Development-Roles": "Account Admin"},
            json={"status": original_status},
        )
        self.assertEqual(200, restored.status_code)


if __name__ == "__main__":
    unittest.main()
