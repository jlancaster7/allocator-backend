# Order Allocation System - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Frontend (React)                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │
│  │   Login    │  │ Portfolio  │  │ Allocation │  │   Order Mgmt   │   │
│  │   Screen   │  │   Groups   │  │   Wizard   │  │    Dashboard   │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Flask REST API                                   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    API Layer (/api/v1)                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │    │
│  │  │   Auth   │  │Portfolio │  │Securities│  │  Allocations │  │    │
│  │  │Endpoints │  │Endpoints │  │Endpoints │  │  Endpoints   │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                       Service Layer                             │    │
│  │  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐  │    │
│  │  │   Aladdin    │  │   Allocation    │  │   Order Mgmt    │  │    │
│  │  │   Client     │  │    Engines      │  │    Service      │  │    │
│  │  └──────────────┘  └─────────────────┘  └─────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                        Core Layer                               │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │    │
│  │  │   Auth   │  │  Config  │  │ Database │  │   Logging    │  │    │
│  │  │   JWT    │  │  Mgmt    │  │  Setup   │  │  Structured  │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                     │                    │                    │
                     ▼                    ▼                    ▼
         ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
         │  BlackRock     │    │   Snowflake    │    │     Redis      │
         │  Aladdin API   │    │   Database     │    │  Cache/Queue   │
         └────────────────┘    └────────────────┘    └────────────────┘
```

## Component Details

### 1. API Layer
- **Flask-RESTX**: Auto-generates Swagger documentation
- **JWT Authentication**: Protects all endpoints except login
- **Request Validation**: Marshmallow schemas (pending)
- **Error Handling**: Consistent error response format

### 2. Service Layer

#### Aladdin Client
- **OAuth2 Authentication**: Client credentials flow
- **Rate Limiting**: 100 requests/minute using asyncio
- **Retry Logic**: Exponential backoff with tenacity
- **Caching**: 5-minute TTL for GET requests
- **Async Operations**: httpx with asyncio

#### Allocation Engines
```
┌─────────────────────────────────────────┐
│          AllocationEngine (Base)         │
│  - validate_inputs()                     │
│  - check_constraints()                   │
│  - calculate_metrics()                   │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ ProRata  │  │  Custom  │  │   MinDisp    │
│  Engine  │  │ Weights  │  │   Engine     │
└──────────┘  └──────────┘  └──────────────┘
```

### 3. Core Layer
- **Configuration**: Environment-based with defaults
- **Security**: JWT tokens, bcrypt password hashing
- **Logging**: Structured JSON logs with correlation IDs
- **Database**: SQLAlchemy with connection pooling

### 4. Data Flow

#### Allocation Request Flow
```
1. User selects portfolio group and security
2. Frontend sends allocation request
3. API validates JWT token
4. Service fetches data from Aladdin:
   - Portfolio group members
   - Account positions and cash
   - Security details and analytics
5. Allocation engine calculates distribution
6. Preview returned to user
7. User confirms allocation
8. Orders submitted to Aladdin (async)
9. Status updates via polling/websocket
```

#### Authentication Flow
```
1. User provides credentials
2. Backend validates against user store
3. JWT access token (1hr) + refresh token (7d) issued
4. Frontend includes token in Authorization header
5. Backend validates token on each request
6. Refresh token used before access token expires
```

### 5. Security Considerations

- **Transport**: HTTPS only in production
- **Authentication**: JWT with short expiration
- **Authorization**: Permission-based access control
- **Secrets**: Environment variables, never in code
- **Input Validation**: All inputs validated
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **XSS Prevention**: Output encoding
- **CORS**: Configurable allowed origins

### 6. Scalability Considerations

- **Horizontal Scaling**: Stateless design allows multiple instances
- **Caching**: Redis for Aladdin responses
- **Async Processing**: Celery for long-running tasks
- **Database**: Snowflake handles large datasets
- **Rate Limiting**: Protects against abuse
- **Connection Pooling**: Efficient resource usage

### 7. Monitoring & Observability

- **Structured Logging**: JSON format for log aggregation
- **Correlation IDs**: Track requests across services
- **Health Checks**: /health endpoint (to be implemented)
- **Metrics**: Response times, error rates (to be implemented)
- **Alerts**: Based on error thresholds (to be implemented)

### 8. Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Load Balancer │────▶│   Flask App     │
└─────────────────┘     │   (Instance 1)  │
                        └─────────────────┘
                                │
                        ┌─────────────────┐
                        │   Flask App     │
                        │   (Instance 2)  │
                        └─────────────────┘
                                │
                        ┌─────────────────┐
                        │   Flask App     │
                        │   (Instance N)  │
                        └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│     Redis       │   │    Snowflake    │   │  Celery Workers │
│  (Cache/Queue)  │   │   (Database)    │   │  (Async Tasks)  │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### 9. Technology Choices Rationale

- **Flask**: Lightweight, flexible, great for APIs
- **SQLAlchemy**: Mature ORM with Snowflake support
- **JWT**: Stateless authentication, scalable
- **Redis**: Fast caching and message queue
- **Celery**: Robust async task processing
- **httpx**: Modern async HTTP client
- **structlog**: Structured logging for observability