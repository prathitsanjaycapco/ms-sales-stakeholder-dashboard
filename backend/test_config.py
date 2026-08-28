import unittest
from unittest.mock import patch

from backend.config import Settings


class ProductionConfigurationTests(unittest.TestCase):
    def test_production_requires_database_url(self):
        with patch.dict("os.environ", {"APP_ENV": "production", "API_CORS_ORIGINS": "https://account.example.com"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                Settings.from_environment()

    def test_production_rejects_localhost_cors(self):
        environment = {
            "APP_ENV": "production", "DATABASE_URL": "postgresql+psycopg://service@db/account",
            "API_CORS_ORIGINS": "http://localhost:5173",
        }
        with patch.dict("os.environ", environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "localhost"):
                Settings.from_environment()

    def test_production_requires_trusted_identity_gateway(self):
        environment = {
            "APP_ENV": "production", "DATABASE_URL": "postgresql+psycopg://service@db/account",
            "API_CORS_ORIGINS": "https://account.example.com",
        }
        with patch.dict("os.environ", environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TRUSTED_PROXY_SECRET"):
                Settings.from_environment()

    def test_production_requires_explicitly_durable_upload_storage(self):
        environment = {
            "APP_ENV": "production", "DATABASE_URL": "postgresql+psycopg://service@db/account",
            "API_CORS_ORIGINS": "https://account.example.com", "AUTH_MODE": "trusted_proxy",
            "TRUSTED_PROXY_SECRET": "test-secret",
        }
        with patch.dict("os.environ", environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DOCUMENT_STORAGE_DURABLE"):
                Settings.from_environment()

    def test_external_ai_requires_key_model_and_explicit_data_approval(self):
        environment = {"APP_ENV": "development", "AI_PROVIDER": "openai", "OPENAI_API_KEY": "test-key", "AI_MODEL": "approved-model"}
        with patch.dict("os.environ", environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "AI_EXTERNAL_DATA_APPROVED"):
                Settings.from_environment()


if __name__ == "__main__":
    unittest.main()
