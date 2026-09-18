"""Import an existing domain as an influencer project. Usage:
python3 dash/import_domains.py <slug> <name> <domain> [--done handles,mailbox,...]
Reconciles once and prints honest states. Rerun-safe: existing slugs are skipped unless --update.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.cmail import models as M
from core.cmail.engine import reconcile_project
from core.cmail.influencer import influencer_passport
from dash.store import DB_PATH

EXTRA = {"drawdle": ("Drawdle", "drawdle.dev"), "feedify": ("Feedify", "feedify.dev"),
         "breadup": ("Breadup", "breadup.dev")}


def import_domain(slug, name, domain, done_keys=(), update=False, db_path=DB_PATH):
    eng = create_engine(f"sqlite:///{db_path}")
    M.Base.metadata.create_all(bind=eng)
    s = sessionmaker(bind=eng)()
    try:
        p = s.scalar(select(M.Project).where(M.Project.slug == slug))
        if p is not None and not update:
            print(f"SKIP {slug}: exists (use --update to refresh passport)")
            return False
        done = {k: True for k in done_keys}
        done.setdefault("name", True)
        passport = influencer_passport(slug.replace("-", ""), domain, done)
        if p is None:
            p = M.Project(slug=slug, name=name, domain=domain, passport=passport)
            s.add(p)
        else:
            p.passport = passport
        s.commit()
        out = reconcile_project(s, p)
        print(f"OK {slug}: {out['counts']} progress={out['progress']}%")
        return True
    finally:
        s.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv[1:]
    done_keys = []
    for a in sys.argv[1:]:
        if a.startswith("--done="):
            done_keys = a.split("=", 1)[1].split(",")
    if len(args) == 0:
        for slug, (name, domain) in EXTRA.items():
            import_domain(slug, name, domain, done_keys, update)
    elif len(args) == 3:
        import_domain(args[0], args[1], args[2], done_keys, update)
    else:
        raise SystemExit("usage: import_domains.py [slug name domain] [--done=k1,k2] [--update]")
