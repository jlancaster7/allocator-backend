"""Audit and activity tracking models"""

from sqlalchemy import Column, String, Integer, JSON
from .base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Audit log for tracking all system changes"""
    __tablename__ = "audit_log"
    
    audit_id = Column(String(100), primary_key=True)
    user_id = Column(String(100), nullable=False)
    username = Column(String(100))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(100))
    changes = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "audit_id": self.audit_id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class UserActivity(Base, TimestampMixin):
    """User activity tracking for API usage"""
    __tablename__ = "user_activity"
    
    activity_id = Column(String(100), primary_key=True)
    user_id = Column(String(100), nullable=False)
    username = Column(String(100))
    session_id = Column(String(100))
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    request_body = Column(JSON)
    response_summary = Column(JSON)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "activity_id": self.activity_id,
            "user_id": self.user_id,
            "username": self.username,
            "session_id": self.session_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "request_body": self.request_body,
            "response_summary": self.response_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }