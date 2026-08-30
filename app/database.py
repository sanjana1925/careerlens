from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sync_schema() -> None:
    """Adds/drops columns so the database matches the current ORM models.

    There's no Alembic in this project, and `Base.metadata.create_all` only
    creates missing *tables* — it never alters an existing one. Without this,
    adding a column to a model (e.g. JobPosting.job_type) breaks every query
    against a pre-existing dev/prod database, and removing one (e.g.
    ResumeAnalysis.project_relevance_pct) leaves a stale NOT NULL column that
    breaks every insert since the ORM no longer supplies it. Runs once at
    startup; each ALTER is a no-op after the first run since we diff against
    the database's actual columns first. Dropping a column is destructive by
    nature — that's the intended behavior of "matches the current models",
    same as any migration would do for a removed field.
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            model_columns = {column.name for column in table.columns}

            for column in table.columns:
                if column.name in existing_columns:
                    continue
                ddl_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'))

            for column_name in existing_columns - model_columns:
                conn.execute(text(f'ALTER TABLE "{table.name}" DROP COLUMN "{column_name}"'))
