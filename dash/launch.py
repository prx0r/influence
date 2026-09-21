#!/usr/bin/env python3
"""Launch a per-identity dashboard.

Usage:
  python dash/launch.py --slug pow-systems --port 8793
  python dash/launch.py --all  # launch all identities on sequential ports

Each identity gets:
  - Its own SQLite DB (identity-scoped)
  - Its own receipt log
  - Its own agent action history
  - Its own dependency graph state
  - A dash server on its own port
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
INFLUENCE = os.path.dirname(ROOT)
IDENTITIES_DIR = os.path.join(INFLUENCE, "identities")

# Ensure imports work
sys.path.insert(0, INFLUENCE)
sys.path.insert(0, ROOT)


def launch_identity(slug: str, port: int, token: str = ""):
    """Start a dash server for one identity."""
    from core.identity_store import IdentityStore

    store = IdentityStore(IDENTITIES_DIR, slug)
    identity = store.load_identity()
    if not identity:
        print(f"[ERROR] Identity '{slug}' not found in {IDENTITIES_DIR}")
        return

    name = identity.get("name", slug)
    print(f"\n{'='*60}")
    print(f"  DASHBOARD: {name}")
    print(f"  Slug: {slug}")
    print(f"  Port: {port}")
    print(f"  DB: {store.db_path}")
    print(f"  Receipts: {store.receipts_path}")
    print(f"{'='*60}\n")

    # Set environment for this instance
    os.environ["DASH_PORT"] = str(port)
    os.environ["DASH_DB"] = store.db_path
    os.environ["IDENTITY_SLUG"] = slug
    if token:
        os.environ["DASH_TOKEN"] = token

    # Import and run the server
    sys.path.insert(0, ROOT)
    from server import main
    main()


def launch_all(port_start: int = 8793, token: str = ""):
    """Launch all identities on sequential ports."""
    from core.identity_store import IdentityRegistry

    registry = IdentityRegistry(IDENTITIES_DIR)
    slugs = registry.list_slugs()

    if not slugs:
        print("No identities found. Create one first.")
        return

    print(f"Found {len(slugs)} identities: {', '.join(slugs)}")

    for i, slug in enumerate(slugs):
        port = port_start + i
        print(f"  {slug} → port {port}")

    print(f"\nStarting dashboards...")
    threads = []
    for i, slug in enumerate(slugs):
        port = port_start + i
        t = threading.Thread(target=launch_identity, args=(slug, port, token),
                             daemon=True, name=f"dash-{slug}")
        t.start()
        threads.append(t)
        time.sleep(0.5)

    print(f"\nAll {len(slugs)} dashboards running.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch per-identity dashboards")
    parser.add_argument("--slug", help="Identity slug to launch")
    parser.add_argument("--port", type=int, default=8793, help="Port (default 8793)")
    parser.add_argument("--all", action="store_true", help="Launch all identities")
    parser.add_argument("--token", default="", help="Auth token")
    args = parser.parse_args()

    if args.all:
        launch_all(args.port, args.token)
    elif args.slug:
        launch_identity(args.slug, args.port, args.token)
    else:
        parser.print_help()
