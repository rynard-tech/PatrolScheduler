"""Database engine and deterministic schema initialization helpers."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session

from backend.models import Base, SchemaVersion

SCHEMA_VERSION = 1


def create_database_engine(url: str = "sqlite:///patrol_scheduler.db") -> Engine:
    """Create an engine without relying on SQLite-only ORM behavior."""
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def initialize_schema(engine: Engine) -> None:
    """Create the current schema idempotently and record its version."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        version = session.scalar(select(SchemaVersion).where(SchemaVersion.id == 1))
        if version is None:
            session.add(SchemaVersion(id=1, version=SCHEMA_VERSION))
        elif version.version != SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version.version} is not supported; "
                f"expected {SCHEMA_VERSION}."
            )
        session.commit()


def initialize_sqlite(path: str | Path) -> Engine:
    """Initialize a file-backed SQLite database and return its engine."""
    engine = create_database_engine(f"sqlite:///{Path(path)}")
    initialize_schema(engine)
    return engine
