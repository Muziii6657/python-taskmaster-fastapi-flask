# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models

    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized.")


def _get_task_columns() -> set[str]:
    inspector = inspect(engine)
    if not inspector.has_table("tasks"):
        return set()
    return {col["name"] for col in inspector.get_columns("tasks")}


def ensure_task_order_column():
    """Add and backfill tasks.order for older schemas that predate ordering support."""
    columns = _get_task_columns()
    if not columns:
        return

    with engine.begin() as connection:
        if "order" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN `order` INTEGER NOT NULL DEFAULT 0"))

        rows = connection.execute(text("SELECT id, `order` FROM tasks")).fetchall()
        sorted_rows = sorted(
            rows,
            key=lambda item: (
                item[1] if item[1] is not None and item[1] > 0 else 10**9,
                item[0],
            ),
        )

        for index, row in enumerate(sorted_rows, start=1):
            if row[1] != index:
                connection.execute(
                    text("UPDATE tasks SET `order` = :new_order WHERE id = :task_id"),
                    {"new_order": index, "task_id": row[0]},
                )


def ensure_task_ai_columns():
    columns = _get_task_columns()
    if not columns:
        return

    alter_statements = {
        "parent_task_id": "ALTER TABLE tasks ADD COLUMN `parent_task_id` INTEGER NULL",
        "dependency_ids": "ALTER TABLE tasks ADD COLUMN `dependency_ids` TEXT NULL",
        "ai_suggested_priority": "ALTER TABLE tasks ADD COLUMN `ai_suggested_priority` VARCHAR(50) NULL",
        "estimated_hours": "ALTER TABLE tasks ADD COLUMN `estimated_hours` FLOAT NULL",
        "ai_generated": "ALTER TABLE tasks ADD COLUMN `ai_generated` BOOLEAN NOT NULL DEFAULT FALSE",
        "execution_notes": "ALTER TABLE tasks ADD COLUMN `execution_notes` TEXT NULL",
        "actual_hours": "ALTER TABLE tasks ADD COLUMN `actual_hours` FLOAT NULL",
    }

    with engine.begin() as connection:
        for column_name, statement in alter_statements.items():
            if column_name not in columns:
                connection.execute(text(statement))
