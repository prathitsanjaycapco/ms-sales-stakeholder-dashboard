from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


APP_NAME = "Stakeholder Dashboard"
DEFAULT_IMPORT = "import.json"


def executable_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def data_root() -> Path:
    return executable_root() / "data"


def configure_environment(database: Path, uploads: Path, static_root: Path) -> None:
    values = {
        "APP_ENV": "development",
        "DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "STAKEHOLDER_REPOSITORY": "database",
        "REQUIRE_DATABASE": "true",
        "SEED_DEMO_DATA": "false",
        "AUTO_CREATE_SCHEMA": "false",
        "API_CORS_ORIGINS": "http://127.0.0.1",
        "UPLOAD_ROOT": str(uploads),
        "AUTH_MODE": "development",
        "DEVELOPMENT_ACTOR": "portable-user",
        "DEVELOPMENT_ROLES": "Account Admin",
        "DOCUMENT_STORAGE_BACKEND": "filesystem",
        "DOCUMENT_STORAGE_DURABLE": "true",
        "PORTABLE_STATIC_ROOT": str(static_root),
    }
    for key, value in values.items():
        os.environ[key] = value


def available_port(start: int = 8765, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available local port was found. Close another copy of the dashboard and try again.")


def open_browser_when_ready(url: str) -> None:
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"{url}/api/health/live", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.25)


def counts_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{value} {name.replace('_', ' ')}" for name, value in counts.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run or load data for {APP_NAME}")
    parser.add_argument("command", choices=("serve", "validate", "import"), nargs="?", default="serve")
    parser.add_argument("file", nargs="?", help="JSON import file; defaults to data/import.json")
    args = parser.parse_args()

    package_data = data_root()
    database = package_data / "dashboard.db"
    uploads = package_data / "uploads"
    resources = resource_root()
    static_root = resources / "frontend_dist"
    package_data.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)
    configure_environment(database, uploads, static_root)

    from app.portable_import import _migrate, replace_portable_database

    source = Path(args.file).expanduser().resolve() if args.file else package_data / DEFAULT_IMPORT
    if args.command in {"validate", "import"}:
        if not source.is_file():
            raise FileNotFoundError(f"Import file was not found: {source}")
        counts = replace_portable_database(source, database, resources, validate_only=args.command == "validate")
        action = "Validated" if args.command == "validate" else "Imported"
        print(f"{action} {counts_text(counts)} from {source}")
        if args.command == "validate":
            print("The active database was not changed.")
        else:
            print(f"Database ready at {database}")
        return 0

    if not database.exists():
        if not source.is_file():
            print(f"First-run data is required. Put the prepared JSON at:\n  {source}")
            print("Then run 'Import Data.cmd' or start this application again.")
            return 2
        counts = replace_portable_database(source, database, resources)
        print(f"Created the first database with {counts_text(counts)}.")
    else:
        _migrate(database, resources)

    port = available_port()
    url = f"http://127.0.0.1:{port}"
    print(f"\n{APP_NAME} is starting at {url}")
    print("Keep this window open while using the dashboard. Close it or press Ctrl+C to stop.\n")
    if os.getenv("PORTABLE_NO_BROWSER", "").strip().lower() not in {"1", "true", "yes"}:
        threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, loop="asyncio", http="h11", log_level="warning")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as error:
        print(f"\n{APP_NAME} could not continue:\n{error}")
        if getattr(sys, "frozen", False):
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass
        raise SystemExit(1)
