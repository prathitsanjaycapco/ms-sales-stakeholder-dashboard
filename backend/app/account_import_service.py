"""Guarded, local SQLite account import and demo reset."""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock

from sqlalchemy import func, select

from .canonical_schema import audit_events, documents, meetings, notes, opportunities, stakeholders
from .executive_store import employees
from .portable_import import PortableImportBatch, insert_import_batch


_TOKENS: dict[str, tuple[str, datetime, tuple]] = {}
_LOCK = Lock()
_EXCLUDED = {"alembic_version", "audit_events"}


def _sqlite_path(engine) -> Path:
    if engine.dialect.name != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        raise ValueError("Excel account administration requires a local SQLite database")
    return Path(engine.url.database).resolve()


def _counts(connection) -> dict[str, int]:
    names = [row[0] for row in connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ) if row[0] not in _EXCLUDED]
    return {name: connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{name.replace(chr(34), chr(34) * 2)}"').scalar_one()
            for name in names}


def _fingerprint(connection) -> tuple:
    counts = _counts(connection)
    return tuple(sorted(counts.items()))


def _backup(database_path: Path) -> Path:
    folder = database_path.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{database_path.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{token_urlsafe(4)}.db"
    with closing(sqlite3.connect(database_path)) as source, closing(sqlite3.connect(target)) as destination:
        source.backup(destination)
    return target


def _demo_preview(connection) -> dict:
    counts = _counts(connection)
    if not connection.execute(select(func.count()).select_from(stakeholders)).scalar_one():
        raise ValueError("There is no demo stakeholder data to clear")
    for table in (stakeholders, employees, meetings, opportunities):
        sources = set(connection.execute(select(table.c.source_system).distinct()).scalars())
        if sources and sources != {"demo_seed"}:
            raise ValueError("This database contains non-demo records and cannot be cleared with the demo control")
    if connection.execute(select(func.count()).select_from(audit_events)).scalar_one():
        raise ValueError("This database has recorded user changes. Restore a clean demo database or clear it offline after reviewing a backup")
    for table, pattern in ((notes, r"note-\d+"), (documents, r"document-seed-.+")):
        ids = connection.execute(select(table.c.id)).scalars()
        if any(not re.fullmatch(pattern, record_id) for record_id in ids):
            raise ValueError("This database contains manually added notes or documents and cannot be cleared as demo only")
    return {"counts": counts, "total_rows": sum(counts.values())}


def preview_demo_clear(engine, actor: str) -> dict:
    _sqlite_path(engine)
    with engine.connect() as connection:
        preview = _demo_preview(connection)
        fingerprint = _fingerprint(connection)
    token = token_urlsafe(32)
    with _LOCK:
        _TOKENS.clear()
        _TOKENS[token] = (actor, datetime.now(timezone.utc) + timedelta(minutes=5), fingerprint)
    return {**preview, "token": token, "confirmation_phrase": "CLEAR DEMO DATA"}


def clear_demo(engine, repository, actor: str, token: str, phrase: str) -> dict:
    if phrase != "CLEAR DEMO DATA":
        raise ValueError("Type CLEAR DEMO DATA exactly to continue")
    with _LOCK:
        challenge = _TOKENS.pop(token, None)
    if not challenge or challenge[0] != actor or challenge[1] < datetime.now(timezone.utc):
        raise ValueError("The confirmation expired. Preview the demo data again")
    database_path = _sqlite_path(engine)
    with engine.connect() as connection:
        preview = _demo_preview(connection)
        if _fingerprint(connection) != challenge[2]:
            raise ValueError("The database changed since the preview. Preview it again")
    backup = _backup(database_path)
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN IMMEDIATE")
        names = [row[0] for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall() if row[0] not in _EXCLUDED]
        counts = tuple(sorted((name, cursor.execute(f'SELECT COUNT(*) FROM "{name.replace(chr(34), chr(34) * 2)}"').fetchone()[0]) for name in names))
        if counts != challenge[2]:
            raise ValueError("The database changed since the preview. Preview it again")
        for table_name in names:
            safe_name = table_name.replace('"', '""')
            cursor.execute(f'DELETE FROM "{safe_name}"')
        if cursor.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("The database could not be cleared without violating references")
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.cursor().execute("PRAGMA foreign_keys=ON")
        raw.close()
    repository._load_normalized()
    return {"cleared": preview["counts"], "backup": str(backup)}


def import_account(engine, repository, batch: PortableImportBatch) -> dict:
    database_path = _sqlite_path(engine)
    with engine.connect() as connection:
        occupied = {name: count for name, count in _counts(connection).items() if count}
    if occupied:
        raise ValueError("The local account database is not empty. Use a clean database or clear the demo dataset first")
    backup = _backup(database_path)
    with engine.begin() as connection:
        if any(_counts(connection).values()):
            raise ValueError("The database changed during import. Preview it again")
        counts = insert_import_batch(connection, batch)
        connection.exec_driver_sql("INSERT INTO application_state (key, value) VALUES ('repository_generation', '1')")
        if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
            raise ValueError("Imported workbook has broken database references")
    repository._load_normalized()
    return {"imported": counts, "backup": str(backup)}
