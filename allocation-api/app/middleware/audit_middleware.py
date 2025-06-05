"""Audit middleware for tracking API requests"""

from flask import request, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from datetime import datetime
import time
from typing import Optional
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AuditMiddleware:
    """Middleware for auditing API requests"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with the Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Called before each request"""
        # Record start time
        g.start_time = time.time()
        
        # Try to get user info if authenticated
        try:
            verify_jwt_in_request(optional=True)
            g.current_user_id = get_jwt_identity()
        except:
            g.current_user_id = None
        
        # Log request info
        logger.info(
            "API Request",
            extra={
                "method": request.method,
                "endpoint": request.endpoint,
                "path": request.path,
                "user_id": g.current_user_id,
                "ip_address": request.remote_addr
            }
        )
    
    def after_request(self, response):
        """Called after each request"""
        # Calculate response time
        response_time_ms = int((time.time() - g.start_time) * 1000)
        
        # Skip audit logging if database is not available
        if not hasattr(g, 'db') or settings.MOCK_ALADDIN_DATA.lower() == "true":
            return response
        
        try:
            from app.services.audit_service import AuditService
            
            # Get request body (sanitized)
            request_body = None
            if request.is_json:
                request_body = request.get_json()
            
            # Get response summary
            response_summary = {
                "status_code": response.status_code,
                "content_length": response.content_length
            }
            
            # Log API activity
            if g.current_user_id:
                AuditService.log_api_activity(
                    db=g.db,
                    user_id=g.current_user_id,
                    username=g.get('current_username', g.current_user_id),
                    endpoint=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    request_body=request_body,
                    response_summary=response_summary
                )
            
            # Log specific actions
            if request.endpoint == 'allocations.preview_allocation' and response.status_code == 200:
                AuditService.log_action(
                    db=g.db,
                    user_id=g.current_user_id or "anonymous",
                    username=g.get('current_username', 'anonymous'),
                    action="PREVIEW_ALLOCATION",
                    entity_type="allocation",
                    entity_id=response.get_json().get('allocation_id'),
                    changes={"method": request.get_json().get('allocation_method')}
                )
            
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Failed to log audit: {e}")
        
        # Add response headers
        response.headers['X-Response-Time-MS'] = str(response_time_ms)
        
        return response


def create_audit_middleware(app):
    """Factory function to create audit middleware"""
    return AuditMiddleware(app)