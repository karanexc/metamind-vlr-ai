"""Database session factory + schema bootstrap with migrations."""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from .models import Base

log = logging.getLogger(__name__)

engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# --- Schema migrations ----------------------------------------------------
# Lightweight migration system: a list of (name, SQL) pairs that get applied
# in order. Each migration is idempotent (uses IF NOT EXISTS / IF EXISTS).
# When you add a new column or index, add a migration here. We avoid Alembic
# to keep the project simple — this list is short and unlikely to grow much.

_MIGRATIONS: list[tuple[str, str]] = [
    # Iteration 7b — events.tier
    ("add_events_tier",
     "ALTER TABLE events ADD COLUMN IF NOT EXISTS tier VARCHAR(32)"),
    # Iteration 9 Drop 1 — teams.region
    ("add_teams_region",
     "ALTER TABLE teams ADD COLUMN IF NOT EXISTS region VARCHAR(64)"),
    # Iteration 9 Drop 2 — player photos + flags + team logos
    ("add_players_image_url",
     "ALTER TABLE players ADD COLUMN IF NOT EXISTS image_url VARCHAR(512)"),
    ("add_players_country",
     "ALTER TABLE players ADD COLUMN IF NOT EXISTS country VARCHAR(64)"),
    ("add_players_real_name",
     "ALTER TABLE players ADD COLUMN IF NOT EXISTS real_name VARCHAR(255)"),
    ("add_teams_logo_url",
     "ALTER TABLE teams ADD COLUMN IF NOT EXISTS logo_url VARCHAR(512)"),
    ("add_teams_country",
     "ALTER TABLE teams ADD COLUMN IF NOT EXISTS country VARCHAR(64)"),
]


def _apply_migrations() -> None:
    """Apply any pending column-level migrations.

    Postgres `IF NOT EXISTS` makes every statement safe to re-run, so this
    is idempotent even on a fully-up-to-date DB.
    """
    with engine.connect() as conn:
        # Skip migrations on a brand-new DB — the table won't exist yet
        # and create_all() will produce the current schema directly.
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())

        for name, sql in _MIGRATIONS:
            # Each migration targets a specific table — extract it from the SQL
            # to skip migrations against tables that don't exist yet.
            sql_lower = sql.lower()
            if "alter table " in sql_lower:
                target = sql_lower.split("alter table ", 1)[1].split()[0].strip()
                if target not in existing_tables:
                    log.debug("Skipping migration %s — table %s does not exist yet", name, target)
                    continue
            try:
                conn.execute(text(sql))
                conn.commit()
                log.debug("Applied migration: %s", name)
            except Exception:
                conn.rollback()
                log.exception("Migration failed: %s", name)
                raise


def init_db() -> None:
    """Create all tables and apply column migrations. Safe to call repeatedly."""
    Base.metadata.create_all(engine)
    _apply_migrations()


def get_session() -> Session:
    return SessionLocal()
