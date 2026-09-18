from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stevejobless.db import Base
from stevejobless.engine import project_summary, reconcile_project, run_autopilot_project
from stevejobless.models import Project


def test_reconcile_static_resources():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        p=Project(slug="test-app", name="Test App", passport={"resources":[
            {"key":"icon","kind":"static","label":"Icon","desired":{"label":"Icon","done":True}},
            {"key":"privacy","kind":"static","label":"Privacy","desired":{"label":"Privacy","done":False,"executor":"HUMAN"}},
        ]})
        db.add(p); db.commit()
        result=reconcile_project(db,p)
        assert result["progress"]==50
        summary=project_summary(p)
        assert len(summary["actions"])==1
        assert summary["actions"][0]["resource_key"]=="privacy"


def test_autopilot_writes_local_artifact(tmp_path):
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine, expire_on_commit=False)
    target=tmp_path/"privacy.md"
    with Session() as db:
        p=Project(slug="auto-app", name="Auto App", passport={"resources":[
            {"key":"privacy","kind":"local_artifact","label":"Privacy","desired":{"path":str(target),"content":"# Privacy"}},
        ]})
        db.add(p); db.commit()
        result=run_autopilot_project(db,p)
        assert target.read_text()=="# Privacy"
        assert result["verified"]["progress"]==100
