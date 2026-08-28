import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from backend.canonical_schema import (
    assistant_conversations,
    assistant_document_chunks,
    assistant_document_indexes,
    assistant_messages,
)
from backend.main import app, pod_engine


class AccountAssistantWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.conversation_ids = []

    @classmethod
    def tearDownClass(cls):
        if not cls.conversation_ids:
            return
        with pod_engine.begin() as connection:
            connection.execute(delete(assistant_messages).where(
                assistant_messages.c.conversation_id.in_(cls.conversation_ids)
            ))
            connection.execute(delete(assistant_conversations).where(
                assistant_conversations.c.id.in_(cls.conversation_ids)
            ))

    def test_reader_can_ask_grounded_question_and_open_private_history(self):
        headers = {"x-development-subject": "assistant-test-user", "x-development-roles": "Reader"}
        response = self.client.post("/api/assistant/chat", headers=headers, json={
            "message": "What is the current pipeline for the Morgan Stanley account?",
            "context": {"pod": "All", "section": "Executive View"},
        })
        self.assertEqual(200, response.status_code, response.text)
        payload = response.json()
        self.conversation_ids.append(payload["conversation_id"])
        self.assertTrue(payload["grounded"])
        self.assertGreater(payload["retrieval_count"], 0)
        self.assertTrue(payload["message"]["citations"])
        self.assertIn(payload["message"]["provider"], {"local-grounded", "local-fallback"})

        detail = self.client.get(
            f"/api/assistant/conversations/{payload['conversation_id']}", headers=headers,
        )
        self.assertEqual(200, detail.status_code)
        self.assertEqual(["user", "assistant"], [item["role"] for item in detail.json()["messages"]])

        denied = self.client.get(
            f"/api/assistant/conversations/{payload['conversation_id']}",
            headers={"x-development-subject": "different-user", "x-development-roles": "Reader"},
        )
        self.assertEqual(404, denied.status_code)
        denied_delete = self.client.delete(
            f"/api/assistant/conversations/{payload['conversation_id']}",
            headers={"x-development-subject": "different-user", "x-development-roles": "Reader"},
        )
        self.assertEqual(404, denied_delete.status_code)
        self.assertEqual(204, self.client.delete(
            f"/api/assistant/conversations/{payload['conversation_id']}", headers=headers,
        ).status_code)

    def test_off_topic_question_is_refused_without_sources(self):
        response = self.client.post("/api/assistant/chat", headers={
            "x-development-subject": "assistant-test-user", "x-development-roles": "Reader",
        }, json={"message": "What is the weather tomorrow?", "context": {"pod": "ISG"}})
        self.assertEqual(200, response.status_code, response.text)
        payload = response.json()
        self.conversation_ids.append(payload["conversation_id"])
        self.assertEqual(0, payload["retrieval_count"])
        self.assertEqual([], payload["message"]["citations"])
        self.assertIn("only answer questions grounded", payload["message"]["content"])

    def test_uploaded_text_is_indexed_retrieved_and_cascade_deleted(self):
        headers = {"x-development-subject": "assistant-document-test", "x-development-roles": "Account Admin"}
        stakeholder_id = self.client.get("/api/stakeholders?pod=ISG", headers=headers).json()[0]["id"]
        response = self.client.post(
            f"/api/stakeholders/{stakeholder_id}/documents/upload",
            headers={**headers, "content-type": "text/plain"},
            params={
                "file_name": "helios-brief.txt", "title": "Project Helios account brief",
                "document_type": "Research", "owner": "Capco Account Team",
            },
            content=b"Project Helios requires a regulatory architecture workshop before the October steering committee.",
        )
        self.assertEqual(201, response.status_code, response.text)
        document_id = response.json()["id"]
        try:
            question = self.client.post("/api/assistant/chat", headers=headers, json={
                "message": "What does Project Helios require before the October steering committee?",
                "context": {"pod": "ISG", "section": "Stakeholder Map", "entity_type": "stakeholder", "entity_id": stakeholder_id},
            })
            self.assertEqual(200, question.status_code, question.text)
            payload = question.json()
            self.conversation_ids.append(payload["conversation_id"])
            citations = payload["message"]["citations"]
            self.assertTrue(any(item["source_type"] == "document" and item["source_id"] == document_id for item in citations))
            with pod_engine.connect() as connection:
                self.assertGreater(connection.execute(select(func.count()).select_from(assistant_document_chunks).where(
                    assistant_document_chunks.c.document_id == document_id
                )).scalar_one(), 0)
        finally:
            deleted = self.client.delete(f"/api/documents/{document_id}", headers=headers)
            self.assertEqual(204, deleted.status_code, deleted.text)
        with pod_engine.connect() as connection:
            self.assertEqual(0, connection.execute(select(func.count()).select_from(assistant_document_indexes).where(
                assistant_document_indexes.c.document_id == document_id
            )).scalar_one())


if __name__ == "__main__":
    unittest.main()
