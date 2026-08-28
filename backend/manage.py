from __future__ import annotations

import argparse

from .config import settings
from .persistence import PersistentStakeholderRepository


def import_legacy() -> None:
    repository = PersistentStakeholderRepository(
        settings.database_url, seed_demo_data=False, auto_create_schema=True,
    )
    if repository.backend_name != "normalized-sql":
        raise RuntimeError("Legacy import did not produce a normalized SQL repository")
    repository._persist_normalized()
    print(f"Imported {len(repository.stakeholders)} stakeholders, {len(repository.meetings)} meetings, and {len(repository.opportunities)} opportunities into canonical tables.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Account database administration")
    parser.add_argument("command", choices=["import-legacy"])
    args = parser.parse_args()
    if args.command == "import-legacy":
        import_legacy()


if __name__ == "__main__":
    main()
