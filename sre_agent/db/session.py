import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env variables so we can grab the DB URL
load_dotenv()

# This will be provided by Supabase in their dashboard
DATABASE_URL = os.environ.get("DATABASE_URL")

# For local development without Supabase, fallback to SQLite
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found. Falling back to local SQLite database.")
    DATABASE_URL = "sqlite:///./sre_agent.db"
    
# Configure SQLAlchemy engine
# Note: For Supabase pooling, you usually need to append ?pool_timeout=... or use psycopg2
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database if they don't exist."""
    from sre_agent.db.models import Base
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
