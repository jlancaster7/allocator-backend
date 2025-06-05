"""Authentication API endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.core.auth import MockUser, create_user_tokens
from app.core.security import verify_password
from app.core.logging import get_logger

logger = get_logger(__name__)

ns = Namespace("auth", description="Authentication operations")

# Models
login_model = ns.model("LoginRequest", {
    "username": fields.String(required=True, description="Username"),
    "password": fields.String(required=True, description="Password")
})

user_model = ns.model("User", {
    "id": fields.String(description="User ID"),
    "username": fields.String(description="Username"),
    "permissions": fields.List(fields.String, description="User permissions")
})

login_response_model = ns.model("LoginResponse", {
    "access_token": fields.String(description="JWT access token"),
    "refresh_token": fields.String(description="JWT refresh token"),
    "user": fields.Nested(user_model)
})

token_refresh_model = ns.model("TokenRefreshRequest", {
    "refresh_token": fields.String(required=True, description="Refresh token")
})

token_refresh_response_model = ns.model("TokenRefreshResponse", {
    "access_token": fields.String(description="New JWT access token")
})


@ns.route("/login")
class Login(Resource):
    @ns.doc("user_login")
    @ns.expect(login_model)
    @ns.marshal_with(login_response_model)
    @ns.response(200, "Login successful")
    @ns.response(401, "Invalid credentials")
    def post(self):
        """User login"""
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        logger.info(f"Login attempt for user: {username}")
        
        # In production, this would validate against a database
        # For now, we'll use a mock implementation
        if username == "demo_user" and password == "demo_password":
            # Create mock user
            user = MockUser()
            user.username = username
            
            # Create tokens
            tokens = create_user_tokens(user.to_dict())
            
            logger.info(f"Login successful for user: {username}")
            
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": {
                    "id": user.user_id,
                    "username": user.username,
                    "permissions": user.permissions
                }
            }
        else:
            logger.warning(f"Login failed for user: {username}")
            ns.abort(401, "Invalid username or password")


@ns.route("/refresh")
class TokenRefresh(Resource):
    @ns.doc("refresh_token")
    @ns.expect(token_refresh_model)
    @ns.marshal_with(token_refresh_response_model)
    @ns.response(200, "Token refreshed successfully")
    @ns.response(401, "Invalid refresh token")
    @jwt_required(refresh=True)
    def post(self):
        """Refresh access token"""
        identity = get_jwt_identity()
        
        # In production, would fetch user details from database
        # For now, create mock user
        user = MockUser()
        user.user_id = identity
        
        # Create new access token
        access_token = create_access_token(
            identity=identity,
            additional_claims={
                "username": user.username,
                "permissions": user.permissions
            }
        )
        
        logger.info(f"Token refreshed for user: {identity}")
        
        return {"access_token": access_token}


@ns.route("/logout")
class Logout(Resource):
    @ns.doc("user_logout")
    @ns.response(200, "Logout successful")
    @jwt_required()
    def post(self):
        """User logout"""
        # In production, would invalidate the token (e.g., add to blacklist)
        identity = get_jwt_identity()
        logger.info(f"User logged out: {identity}")
        
        return {"message": "Logout successful"}


@ns.route("/me")
class CurrentUser(Resource):
    @ns.doc("get_current_user")
    @ns.marshal_with(user_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @jwt_required()
    def get(self):
        """Get current user information"""
        from flask_jwt_extended import get_jwt
        
        identity = get_jwt_identity()
        claims = get_jwt()
        
        return {
            "id": identity,
            "username": claims.get("username"),
            "permissions": claims.get("permissions", [])
        }