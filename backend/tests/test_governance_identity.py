import unittest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.canonical_schema import idempotency_records
from app.governance import Principal, execute_idempotent


class GovernanceAndIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

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

    def test_offer_rates_require_commercial_role(self):
        denied = self.client.get(
            "/api/candidates/candidate-021/offer",
            headers={"X-Development-Roles": "Editor"},
        )
        self.assertEqual(403, denied.status_code)
        allowed = self.client.get(
            "/api/candidates/candidate-021/offer",
            headers={"X-Development-Roles": "Account Manager"},
        )
        self.assertEqual(200, allowed.status_code)
        self.assertIn("proposed_rate", allowed.json())

    def test_reader_aliases_to_viewer_and_unknown_roles_are_rejected(self):
        reader = self.client.get("/api/session", headers={"X-Development-Roles": "Reader"})
        self.assertEqual(200, reader.status_code)
        self.assertEqual(["Viewer"], reader.json()["roles"])

        unknown = self.client.get("/api/session", headers={"X-Development-Roles": "Made Up Role"})
        self.assertEqual(403, unknown.status_code)
        self.assertEqual("UNKNOWN_ROLE", unknown.json()["code"])

    def test_pod_scope_is_enforced(self):
        headers = {"X-Development-Roles": "Viewer", "X-Development-Pods": "ISG"}
        self.assertEqual(200, self.client.get("/api/pods/ISG/dashboard", headers=headers).status_code)
        denied = self.client.get("/api/pods/MSIM/dashboard", headers=headers)
        self.assertEqual(403, denied.status_code)
        self.assertEqual("POD_SCOPE_REQUIRED", denied.json()["code"])

    def test_liveness_and_readiness_do_not_require_identity(self):
        self.assertEqual(200, self.client.get("/api/health/live").status_code)
        readiness = self.client.get("/api/health/ready")
        self.assertEqual(200, readiness.status_code)
        self.assertTrue(readiness.json()["checks"]["database"])

    def test_trust_and_notification_feeds_expose_evidence_without_admin_data(self):
        viewer = {"X-Development-Roles": "Reader"}
        trust = self.client.get("/api/data-trust", headers=viewer)
        self.assertEqual(200, trust.status_code, trust.text)
        self.assertIn("delivery", {item["key"] for item in trust.json()["sources"]})
        digest = self.client.get("/api/notifications/digest?pod=ISG", headers=viewer)
        self.assertEqual(200, digest.status_code, digest.text)
        self.assertEqual("ISG", digest.json()["scope"])
        self.assertEqual(digest.json()["summary"]["total"], len(digest.json()["items"]))
        denied_audit = self.client.get("/api/audit-events", headers=viewer)
        self.assertEqual(403, denied_audit.status_code)

    def test_idempotency_key_replays_once_and_rejects_payload_reuse(self):
        engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
        idempotency_records.create(engine)
        scope = {
            "type": "http", "method": "POST", "path": "/api/example", "query_string": b"",
            "headers": [(b"idempotency-key", b"stable-key")], "scheme": "http",
            "server": ("testserver", 80), "client": ("testclient", 1),
        }
        request = Request(scope)
        principal = Principal("idempotency-test", frozenset({"Account Admin"}))
        calls = []
        first, replayed = execute_idempotent(engine, principal, request, {"value": 1}, lambda: calls.append(1) or {"id": "created"})
        second, replayed_second = execute_idempotent(engine, principal, request, {"value": 1}, lambda: calls.append(2) or {"id": "duplicate"})
        self.assertEqual({"id": "created"}, first)
        self.assertEqual(first, second)
        self.assertFalse(replayed)
        self.assertTrue(replayed_second)
        self.assertEqual([1], calls)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
