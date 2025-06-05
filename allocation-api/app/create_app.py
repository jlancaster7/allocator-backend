"""Flask application factory"""

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_restx import Api
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_db

logger = get_logger(__name__)


def create_app() -> Flask:
    """Create and configure Flask application"""
    
    # Setup logging first
    setup_logging()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure app
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = settings.JWT_ACCESS_TOKEN_EXPIRES
    app.config["JWT_ALGORITHM"] = settings.JWT_ALGORITHM
    app.config["RESTX_MASK_SWAGGER"] = False
    app.config["ERROR_INCLUDE_MESSAGE"] = False
    
    # Initialize extensions
    jwt = JWTManager(app)
    CORS(app, origins=settings.CORS_ORIGINS)
    
    # Create API with versioning
    api = Api(
        app,
        version="1.0.0",
        title="Order Allocation System API",
        description="API for order allocation system integrating with BlackRock Aladdin",
        doc="/docs",
        prefix=settings.API_V1_STR
    )
    
    # Register namespaces
    from app.api import auth, portfolios, securities, allocations
    
    api.add_namespace(auth.ns, path="/auth")
    api.add_namespace(portfolios.ns, path="/portfolio-groups")
    api.add_namespace(securities.ns, path="/securities")
    api.add_namespace(allocations.ns, path="/allocations")
    
    # TODO: Add these once implemented
    # api.add_namespace(orders.ns, path="/orders")
    # api.add_namespace(market_data.ns, path="/")
    
    # Initialize database
    with app.app_context():
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register JWT callbacks
    register_jwt_callbacks(jwt)
    
    logger.info("Flask application created successfully")
    
    return app


def register_error_handlers(app: Flask):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad Request", "message": str(error)}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized", "message": "Authentication required"}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden", "message": "Insufficient permissions"}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not Found", "message": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {"error": "Internal Server Error", "message": "An unexpected error occurred"}, 500


def register_jwt_callbacks(jwt: JWTManager):
    """Register JWT callbacks"""
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"error": "Token expired", "message": "The token has expired"}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": "Invalid token", "message": "The token is invalid"}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": "Authorization required", "message": "Request does not contain an access token"}, 401