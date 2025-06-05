"""Authentication dependencies and utilities"""

from typing import Optional, Dict, Any
from flask import request, g
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt,
    get_jwt_identity,
    create_access_token as jwt_create_access_token,
    create_refresh_token as jwt_create_refresh_token
)
from functools import wraps
from app.core.security import decode_token
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AuthError(Exception):
    """Authentication error"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_current_user() -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token
    
    Returns:
        User information from token
        
    Raises:
        AuthError: If no valid user found
    """
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
        claims = get_jwt()
        
        return {
            "user_id": identity,
            "username": claims.get("username"),
            "permissions": claims.get("permissions", []),
            "email": claims.get("email")
        }
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        raise AuthError("Invalid or expired token")


def require_auth(f):
    """
    Decorator to require authentication for a route
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            user = g.current_user
            return {"message": f"Hello {user['username']}"}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            g.current_user = get_current_user()
            return f(*args, **kwargs)
        except AuthError as e:
            return {"error": e.message}, e.status_code
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            return {"error": "Authentication required"}, 401
    
    return decorated_function


def require_permissions(*required_permissions):
    """
    Decorator to require specific permissions for a route
    
    Usage:
        @app.route('/admin')
        @require_auth
        @require_permissions('admin', 'write')
        def admin_route():
            return {"message": "Admin access granted"}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return {"error": "Authentication required"}, 401
            
            user_permissions = g.current_user.get('permissions', [])
            
            if not all(perm in user_permissions for perm in required_permissions):
                logger.warning(
                    "Permission denied",
                    user_id=g.current_user.get('user_id'),
                    required=required_permissions,
                    user_permissions=user_permissions
                )
                return {"error": "Insufficient permissions"}, 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def create_user_tokens(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create access and refresh tokens for a user
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        Dictionary with access_token and refresh_token
    """
    # Create identity and additional claims
    identity = user_data["user_id"]
    additional_claims = {
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "permissions": user_data.get("permissions", [])
    }
    
    # Create tokens using Flask-JWT-Extended
    access_token = jwt_create_access_token(
        identity=identity,
        additional_claims=additional_claims
    )
    
    refresh_token = jwt_create_refresh_token(
        identity=identity,
        additional_claims={"username": user_data.get("username")}
    )
    
    logger.info(
        "User tokens created",
        user_id=identity,
        username=user_data.get("username")
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


def extract_token_from_header() -> Optional[str]:
    """
    Extract JWT token from Authorization header
    
    Returns:
        Token string or None if not found
    """
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    return None


def validate_api_key(api_key: str) -> bool:
    """
    Validate an API key (for service-to-service communication)
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    # In production, this would check against a database or service
    # For now, we'll use a simple check against environment variable
    valid_keys = settings.ALADDIN_CLIENT_ID  # Example
    return api_key == valid_keys if valid_keys else False


class MockUser:
    """Mock user for development/testing"""
    def __init__(self):
        self.user_id = "dev-user-001"
        self.username = "dev_user"
        self.email = "dev@example.com"
        self.permissions = ["read", "write", "allocate", "commit"]
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "permissions": self.permissions
        }