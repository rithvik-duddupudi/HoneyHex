from __future__ import annotations

import os
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from honeyhex.registry.models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    return os.environ.get(
        "HONEYHEX_DATABASE_URL",
        "sqlite+pysqlite:///./honeyhex.db",
    )


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        echo = os.environ.get("HONEYHEX_SQL_ECHO", "").lower() in ("1", "true")
        if url.startswith("sqlite") and ":memory:" in url:
            _engine = create_engine(
                url,
                echo=echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        elif url.startswith("sqlite"):
            _engine = create_engine(
                url,
                echo=echo,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(url, echo=echo)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Test helper: clear cached engine/session factory."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
