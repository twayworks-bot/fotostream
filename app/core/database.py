from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# SQLite configuration with check_same_thread=False for async FastAPI usage
engine = create_engine(
    settings.effective_db_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.effective_db_url else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency for database session management."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database and ensure column schema integrity."""
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)

    # SQLite automatic lightweight migration for resolution column
    with engine.connect() as conn:
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(jobs)").fetchall()
            col_names = [row[1] for row in res]
            if "resolution" not in col_names:
                conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN resolution VARCHAR(20) DEFAULT '1080p'")
                conn.commit()
        except Exception:
            pass
