"""Database configuration and session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
import logging

from app.core.config import settings
from app.core.logging import get_logger

# Apply Snowflake JSON patch
from app.core import snowflake_patch

logger = get_logger(__name__)

# Create engine with NullPool for Snowflake
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Recommended for Snowflake
    echo=settings.DEBUG,
    connect_args={
        "json_result_force_utf8_decoding": True
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Ensures session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables"""
    try:
        # Import models to ensure they're registered
        from app.models import Base, Allocation, AllocationDetail, AuditLog, UserActivity
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT CURRENT_VERSION()")
            version = result.scalar()
            logger.info(f"Connected to Snowflake version: {version}")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def close_db() -> None:
    """Close database connections"""
    engine.dispose()