"""Audit service for tracking user actions and API activity"""

import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from flask import request
from app.models import AuditLog, UserActivity
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for audit logging"""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: str,
        username: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        changes: Optional[Dict] = None
    ) -> AuditLog:
        """Log a user action"""
        audit_id = str(uuid.uuid4())
        
        # Get request info if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:500]  # Limit length
        
        # Use raw SQL with PARSE_JSON for VARIANT columns
        stmt = text("""
            INSERT INTO audit_log (
                audit_id, user_id, username, action, entity_type, entity_id,
                changes, ip_address, user_agent, created_at
            )
            SELECT :audit_id, :user_id, :username, :action, :entity_type, :entity_id,
                PARSE_JSON(:changes), :ip_address, :user_agent, CURRENT_TIMESTAMP()
        """)
        
        db.execute(stmt, {
            "audit_id": audit_id,
            "user_id": user_id,
            "username": username,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "changes": json.dumps(changes) if changes else None,
            "ip_address": ip_address,
            "user_agent": user_agent
        })
        
        db.commit()
        
        # Fetch the created audit log
        audit = db.query(AuditLog).filter_by(audit_id=audit_id).first()
        
        logger.info(f"Audit log created: {action} by {username} on {entity_type}/{entity_id}")
        return audit
    
    @staticmethod
    def log_api_activity(
        db: Session,
        user_id: str,
        username: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        request_body: Optional[Dict] = None,
        response_summary: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> UserActivity:
        """Log API activity"""
        activity_id = str(uuid.uuid4())
        
        # Sanitize request body to remove sensitive data
        if request_body:
            sanitized_body = request_body.copy()
            if 'password' in sanitized_body:
                sanitized_body['password'] = '***'
            if 'token' in sanitized_body:
                sanitized_body['token'] = '***'
        else:
            sanitized_body = None
        
        # Use raw SQL with PARSE_JSON for VARIANT columns
        stmt = text("""
            INSERT INTO user_activity (
                activity_id, user_id, username, session_id, endpoint, method,
                status_code, response_time_ms, request_body, response_summary, created_at
            )
            SELECT :activity_id, :user_id, :username, :session_id, :endpoint, :method,
                :status_code, :response_time_ms, PARSE_JSON(:request_body), 
                PARSE_JSON(:response_summary), CURRENT_TIMESTAMP()
        """)
        
        db.execute(stmt, {
            "activity_id": activity_id,
            "user_id": user_id,
            "username": username,
            "session_id": session_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "request_body": json.dumps(sanitized_body) if sanitized_body else None,
            "response_summary": json.dumps(response_summary) if response_summary else None
        })
        
        db.commit()
        
        # Fetch the created activity
        activity = db.query(UserActivity).filter_by(activity_id=activity_id).first()
        
        return activity
    
    @staticmethod
    def get_user_activities(
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent user activities"""
        query = db.query(UserActivity)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        activities = query.order_by(UserActivity.created_at.desc()).limit(limit).all()
        
        return [activity.to_dict() for activity in activities]
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit logs with filters"""
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if entity_id:
            query = query.filter_by(entity_id=entity_id)
        
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [log.to_dict() for log in logs]