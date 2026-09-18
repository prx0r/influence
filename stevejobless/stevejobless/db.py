from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}
engine = create_engine(settings.db_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401
    from . import vault  # noqa: F401
    from . import tradie  # noqa: F401
    from . import domain_deals  # noqa: F401
    from .publisher import models as pub_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    tradie.migrate(engine)
