from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import settings
from .persistence import PersistentStakeholderRepository
from .models import CandidateCreate, ResourceRequirementCreate
from .resourcing_store import ResourcingStore
from .executive_store import ExecutiveAnalyticsStore
from .pod_store import PodOperatingStore
from .executive_import import ExecutiveImportBatch, import_executive_batch


def seed_demo() -> None:
    if settings.environment == "production":
        raise RuntimeError("Demo data cannot be seeded in production")
    repository = PersistentStakeholderRepository(
        settings.database_url, seed_demo_data=True, auto_create_schema=settings.auto_create_schema,
    )
    executive_store = ExecutiveAnalyticsStore(
        repository.engine, repository, None, seed_demo_data=True,
        auto_create_schema=settings.auto_create_schema,
    )
    pod_store = PodOperatingStore(
        repository.engine, repository, seed_demo_data=True,
        auto_create_schema=settings.auto_create_schema,
    )
    executive_store.pod_store = pod_store
    ResourcingStore(
        repository.engine, repository, seed_demo_data=True,
        auto_create_schema=settings.auto_create_schema,
    )
    print(
        f"Demo dataset is available with {len(repository.stakeholders)} stakeholders, "
        f"{len(repository.meetings)} meetings, and {len(repository.opportunities)} opportunities."
    )


def import_legacy() -> None:
    repository = PersistentStakeholderRepository(
        settings.database_url, seed_demo_data=False, auto_create_schema=True,
    )
    if repository.backend_name != "normalized-sql":
        raise RuntimeError("Legacy import did not produce a normalized SQL repository")
    repository._persist_normalized()
    print(f"Imported {len(repository.stakeholders)} stakeholders, {len(repository.meetings)} meetings, and {len(repository.opportunities)} opportunities into canonical tables.")


def import_resourcing(file_path: str, dry_run: bool = False) -> None:
    source = Path(file_path).expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    requirement_rows = payload.get("requirements", [])
    candidate_rows = payload.get("candidates", [])
    validated_requirements = [(row.get("source_id"), ResourceRequirementCreate.model_validate(row)) for row in requirement_rows]
    validated_candidates = [(row.get("source_id"), CandidateCreate.model_validate(row)) for row in candidate_rows]
    if dry_run:
        print(f"Validated {len(validated_requirements)} requirements and {len(validated_candidates)} candidates from {source}; no records written.")
        return
    repository = PersistentStakeholderRepository(
        settings.database_url, seed_demo_data=False, auto_create_schema=settings.auto_create_schema,
    )
    store = ResourcingStore(repository.engine, repository, seed_demo_data=False, auto_create_schema=settings.auto_create_schema)
    requirement_ids = {}
    for source_id, model in validated_requirements:
        created = store.create_requirement(model.model_dump())
        if source_id:
            requirement_ids[source_id] = created["id"]
    for _, model in validated_candidates:
        values = model.model_dump()
        values["resource_requirement_id"] = requirement_ids.get(values["resource_requirement_id"], values["resource_requirement_id"])
        store.create_candidate(values)
    print(f"Imported {len(validated_requirements)} requirements and {len(validated_candidates)} candidates from {source}.")


def import_executive(file_path: str, dry_run: bool = False) -> None:
    source = Path(file_path).expanduser().resolve()
    batch = ExecutiveImportBatch.model_validate(json.loads(source.read_text(encoding="utf-8")))
    repository = PersistentStakeholderRepository(
        settings.database_url, seed_demo_data=False, auto_create_schema=settings.auto_create_schema,
    )
    counts = import_executive_batch(repository.engine, batch, dry_run=dry_run)
    action = "Validated" if dry_run else "Imported"
    detail = ", ".join(f"{count} {name.replace('_', ' ')}" for name, count in counts.items())
    print(f"{action} {detail} from {source}{'; no records written' if dry_run else ''}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Account database administration")
    parser.add_argument("command", choices=["seed-demo", "import-legacy", "import-resourcing", "import-executive"])
    parser.add_argument("--file", help="JSON file containing requirements and candidates")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing records")
    args = parser.parse_args()
    if args.command == "seed-demo":
        seed_demo()
    elif args.command == "import-legacy":
        import_legacy()
    elif args.command == "import-resourcing":
        if not args.file:
            parser.error("import-resourcing requires --file")
        import_resourcing(args.file, args.dry_run)
    elif args.command == "import-executive":
        if not args.file:
            parser.error("import-executive requires --file")
        import_executive(args.file, args.dry_run)


if __name__ == "__main__":
    main()
