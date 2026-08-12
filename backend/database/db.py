"""
Lightweight SQLite persistence layer (SQLAlchemy Core) so uploaded
sessions and generated reports survive server restarts.
"""
import json
from datetime import datetime
from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, Text, DateTime, insert, select
)
from core.config import get_settings

settings = get_settings()
engine = create_engine(f"sqlite:///{settings.SQLITE_PATH}", future=True)
metadata = MetaData()

sessions_table = Table(
    "sessions", metadata,
    Column("session_id", String, primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("files_json", Text),
)

reports_table = Table(
    "reports", metadata,
    Column("session_id", String, primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("report_json", Text),
)


def init_db():
    metadata.create_all(engine)


def _json_dumps_safe(obj) -> str:
    """Backstop serializer: everything that reaches this file should
    already be plain JSON-safe data (callers use model_dump(mode='json')),
    but `default=str` means any stray datetime/UUID/etc. that slips
    through gets stringified instead of crashing the request."""
    return json.dumps(obj, default=str)


def save_session_files(session_id: str, files: list[dict]):
    with engine.begin() as conn:
        conn.execute(
            sessions_table.delete().where(sessions_table.c.session_id == session_id)
        )
        conn.execute(
            insert(sessions_table).values(
                session_id=session_id, created_at=datetime.utcnow(), files_json=_json_dumps_safe(files)
            )
        )


def get_session_files(session_id: str) -> list[dict] | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(sessions_table.c.files_json).where(sessions_table.c.session_id == session_id)
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_report(session_id: str, report: dict):
    with engine.begin() as conn:
        conn.execute(
            reports_table.delete().where(reports_table.c.session_id == session_id)
        )
        conn.execute(
            insert(reports_table).values(
                session_id=session_id, created_at=datetime.utcnow(), report_json=_json_dumps_safe(report)
            )
        )


def get_report(session_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(reports_table.c.report_json).where(reports_table.c.session_id == session_id)
        ).fetchone()
        return json.loads(row[0]) if row else None
