from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


TRUE_VALUES = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in TRUE_VALUES


def _database_url(environment: str) -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    if environment == "production":
        raise RuntimeError("DATABASE_URL is required in production")
    path = Path(__file__).resolve().with_name("stakeholder-dev.db")
    return f"sqlite:///{path.as_posix()}"


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    repository_backend: str
    require_database: bool
    seed_demo_data: bool
    auto_create_schema: bool
    cors_origins: tuple[str, ...]
    upload_root: Path
    auth_mode: str
    trusted_proxy_secret: str | None
    development_actor: str
    development_roles: tuple[str, ...]
    document_storage_backend: str
    document_storage_durable: bool
    ai_provider: str
    ai_model: str | None
    ai_api_key: str | None
    ai_external_data_approved: bool
    ai_max_sources: int

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.getenv("APP_ENV", "development").strip().lower()
        if environment not in {"development", "test", "production"}:
            raise RuntimeError("APP_ENV must be development, test, or production")
        database_url = _database_url(environment)
        default_origins = "http://localhost:5173,http://localhost:4173"
        origins = tuple(value.strip() for value in os.getenv("API_CORS_ORIGINS", default_origins).split(",") if value.strip())
        if environment == "production" and any("localhost" in value or "127.0.0.1" in value for value in origins):
            raise RuntimeError("Production API_CORS_ORIGINS must not contain localhost")
        upload_root = Path(os.getenv("UPLOAD_ROOT", str(Path(__file__).resolve().with_name("uploads")))).resolve()
        auth_mode = os.getenv("AUTH_MODE", "development" if environment != "production" else "trusted_proxy").strip().lower()
        if auth_mode not in {"development", "trusted_proxy"}:
            raise RuntimeError("AUTH_MODE must be development or trusted_proxy")
        trusted_proxy_secret = os.getenv("TRUSTED_PROXY_SECRET")
        if environment == "production" and (auth_mode != "trusted_proxy" or not trusted_proxy_secret):
            raise RuntimeError("Production requires AUTH_MODE=trusted_proxy and TRUSTED_PROXY_SECRET")
        document_storage_backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "filesystem").strip().lower()
        if document_storage_backend != "filesystem":
            raise RuntimeError("DOCUMENT_STORAGE_BACKEND currently supports filesystem only")
        document_storage_durable = _bool("DOCUMENT_STORAGE_DURABLE", environment != "production")
        if environment == "production" and not document_storage_durable:
            raise RuntimeError("Production filesystem uploads require DOCUMENT_STORAGE_DURABLE=true and a durable UPLOAD_ROOT")
        ai_provider = os.getenv("AI_PROVIDER", "local").strip().lower()
        if ai_provider not in {"local", "openai"}:
            raise RuntimeError("AI_PROVIDER must be local or openai")
        ai_api_key = os.getenv("OPENAI_API_KEY") or None
        ai_model = os.getenv("AI_MODEL") or None
        ai_external_data_approved = _bool("AI_EXTERNAL_DATA_APPROVED", False)
        if ai_provider == "openai" and (not ai_api_key or not ai_model):
            raise RuntimeError("AI_PROVIDER=openai requires OPENAI_API_KEY and AI_MODEL")
        if ai_provider == "openai" and not ai_external_data_approved:
            raise RuntimeError("AI_PROVIDER=openai requires AI_EXTERNAL_DATA_APPROVED=true")
        ai_max_sources = int(os.getenv("AI_MAX_SOURCES", "8"))
        if not 1 <= ai_max_sources <= 20:
            raise RuntimeError("AI_MAX_SOURCES must be between 1 and 20")
        return cls(
            environment=environment,
            database_url=database_url,
            repository_backend=os.getenv("STAKEHOLDER_REPOSITORY", "database").strip().lower(),
            require_database=_bool("REQUIRE_DATABASE", environment == "production"),
            seed_demo_data=_bool("SEED_DEMO_DATA", False),
            auto_create_schema=_bool("AUTO_CREATE_SCHEMA", environment != "production"),
            cors_origins=origins,
            upload_root=upload_root,
            auth_mode=auth_mode,
            trusted_proxy_secret=trusted_proxy_secret,
            development_actor=os.getenv("DEVELOPMENT_ACTOR", "local-developer").strip(),
            development_roles=tuple(value.strip() for value in os.getenv("DEVELOPMENT_ROLES", "Account Admin").split(",") if value.strip()),
            document_storage_backend=document_storage_backend,
            document_storage_durable=document_storage_durable,
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_api_key=ai_api_key,
            ai_external_data_approved=ai_external_data_approved,
            ai_max_sources=ai_max_sources,
        )


settings = Settings.from_environment()
