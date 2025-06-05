# Changelog

All notable changes to the Order Allocation API project.

## [0.1.0] - 2025-06-04

### Added

#### Core Infrastructure
- Flask application structure with application factory pattern
- Configuration management using environment variables
- Structured logging with JSON output via structlog
- SQLAlchemy database setup with Snowflake connector
- CORS support for cross-origin requests

#### Authentication & Security
- JWT-based authentication system with access and refresh tokens
- Password hashing using bcrypt
- Permission-based authorization decorators
- Mock user for development/testing
- Token expiration: access (1 hour), refresh (7 days)

#### Aladdin API Integration
- Complete Aladdin API client with:
  - OAuth2 authentication with automatic token refresh
  - Rate limiting (100 requests/minute)
  - Exponential backoff retry logic (3 attempts)
  - Response caching with configurable TTL
  - Required headers (Request-ID, Origin-Timestamp)
- Implemented methods:
  - Portfolio groups and members
  - Security search and details
  - Security analytics
  - Position and cash queries
  - Order submission and management

#### Allocation Engines
- **Pro-Rata Allocation Engine**:
  - NAV-based proportional allocation
  - Minimum denomination handling
  - Remainder distribution logic
  - 97% allocation rate in tests
  
- **Custom Weights Allocation Engine**:
  - User-defined percentage allocation
  - Weight validation and normalization
  - Unallocated amount redistribution
  - 100% allocation rate in tests
  
- **Minimum Dispersion Allocation Engine**:
  - Scipy-based optimization (SLSQP method)
  - Minimizes standard deviation of target metrics
  - Supports ASD, Duration, and OAS optimization
  - Fallback to pro-rata on failure
  - 90.3% dispersion improvement in tests

- **Factory Pattern** for engine selection

#### API Endpoints
- Authentication:
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - GET /api/v1/auth/me

- Portfolio Groups:
  - GET /api/v1/portfolio-groups
  - GET /api/v1/portfolio-groups/{group_id}
  - GET /api/v1/portfolio-groups/{group_id}/accounts

- Securities:
  - GET /api/v1/securities/search
  - GET /api/v1/securities/{security_id}
  - GET /api/v1/securities/{security_id}/analytics

#### Documentation
- Swagger/OpenAPI documentation at /docs
- Comprehensive README with setup instructions
- Development log tracking progress
- API documentation with examples
- Test summary with results

#### Testing
- Setup verification tests (6/6 passing)
- Allocation engine tests (3/3 passing)
- API endpoint tests (3/4 passing)
- Test scripts that work without external dependencies

#### Development Tools
- Virtual environment with all dependencies
- Black code formatter configuration
- Flake8 linting configuration
- MyPy type checking support
- Pre-commit hooks ready

### Fixed
- SQLAlchemy version conflict with snowflake-sqlalchemy (downgraded to 1.4.49)
- Tenacity import errors (removed unsupported callbacks)
- Flask async/await compatibility issues
- Werkzeug compatibility with Flask-RESTX (upgraded to 1.3.0)
- Bond pricing representation in tests

### Changed
- Moved all application files to allocation-api subdirectory
- Updated Flask-RESTX namespace registration
- Improved error handling with specific error types
- Enhanced logging with correlation IDs

### Security
- JWT tokens stored securely
- Passwords hashed with bcrypt
- Environment-based secret management
- Permission-based access control

### Dependencies
- Flask 2.3.3
- Flask-RESTX 1.3.0
- Flask-JWT-Extended 4.5.2
- SQLAlchemy 1.4.49
- httpx 0.25.0
- tenacity 8.2.3
- numpy 1.24.3
- scipy 1.11.2
- pandas 2.0.3
- structlog 23.1.0

## [0.2.0] - 2025-06-05

### Changed
- Updated portfolio group names from specific client names to generic identifiers:
  - PUBLICPRE → ALPHA-CORE
  - BIG6 → INST-PRIME
  - DP-LB-USD → DURATION-PRO
  - OPNIC → BALANCED-SELECT
- Updated all associated account prefixes to match new portfolio group names
- Fixed API contract mismatch in portfolio-groups endpoint (id/name → group_id/group_name)
- Fixed bond pricing from percentage to decimal format (98.75 → 0.98750)
- Increased mock account cash percentages from 2-8% to 10-20% for better allocation coverage
- Removed mock store logic in favor of real Snowflake database for allocation commits

### Fixed
- Allocation engine now properly handles bond prices instead of assuming $100
- Allocation commit endpoint now uses real Snowflake database instead of returning 404
- Portfolio group API response now matches frontend expectations

### Added
- Git repository initialization with proper .gitignore
- Organized project structure with separate folders for API docs and technical documentation

## [Unreleased]

### To Do
- Implement allocation preview and commit endpoints
- Add order modification and cancellation endpoints
- Create market data endpoints (positions, cash)
- Set up Celery for async task processing
- Design and implement Snowflake database schema
- Create SQLAlchemy models for persistence
- Implement audit trail functionality
- Add comprehensive pytest suite
- Create Docker configuration
- Set up CI/CD pipeline
- Add WebSocket support for real-time updates
- Implement circuit breaker for external APIs
- Add request validation middleware
- Create performance monitoring
- Implement proper error recovery mechanisms

### Known Issues
- JWT error handler returns 500 instead of 401 in test environment
- Swagger docs URL in tests needs correction
- No actual user database (using mock user)
- External service calls fail without credentials (expected)