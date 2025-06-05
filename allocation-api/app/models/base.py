"""Base model class for all database models"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin that adds timestamp fields to models"""
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.current_timestamp(),
        nullable=False
    )