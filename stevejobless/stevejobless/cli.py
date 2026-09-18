from __future__ import annotations

import argparse
import json

from sqlalchemy import select

from .db import SessionLocal, init_db
from .engine import reconcile_all, reconcile_project, run_autopilot_all, run_autopilot_project
from .models import Project
from .seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(prog="steve", description="SteveJobless studio operations OS")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("projects")
    rec = sub.add_parser("reconcile")
    rec.add_argument("slug", nargs="?")
    auto = sub.add_parser("autopilot")
    auto.add_argument("slug", nargs="?")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    init_db()
    if args.cmd == "init":
        with SessionLocal() as db: seed(db)
        print("SteveJobless initialized.")
    elif args.cmd == "projects":
        with SessionLocal() as db:
            seed(db)
            rows = db.scalars(select(Project).order_by(Project.id)).all()
            for p in rows: print(f"{p.slug:12} {p.name:16} {p.domain or '-'}")
    elif args.cmd == "reconcile":
        with SessionLocal() as db:
            seed(db)
            if args.slug:
                p = db.scalar(select(Project).where(Project.slug == args.slug))
                if not p: raise SystemExit(f"Unknown project: {args.slug}")
                result = reconcile_project(db, p)
            else:
                result = reconcile_all(db)
            print(json.dumps(result, indent=2))
    elif args.cmd == "autopilot":
        with SessionLocal() as db:
            seed(db)
            if args.slug:
                p = db.scalar(select(Project).where(Project.slug == args.slug))
                if not p: raise SystemExit(f"Unknown project: {args.slug}")
                result = run_autopilot_project(db, p)
            else:
                result = run_autopilot_all(db)
            print(json.dumps(result, indent=2))
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("stevejobless.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
