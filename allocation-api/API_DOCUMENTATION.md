# Order Allocation API - Complete Documentation

## Base URL
```
http://localhost:5000/v1
```

## Authentication

All endpoints except `/auth/login` require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Implemented Endpoints

### Authentication Endpoints

#### 1. Login
```http
POST /v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

Response: 200 OK
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "user": {
    "id": "string",
    "username": "string",
    "permissions": ["view_portfolios", "create_allocations", "execute_trades"]
  }
}

Response: 401 Unauthorized
{
  "error": "Invalid credentials"
}
```

#### 2. Refresh Token
```http
POST /v1/auth/refresh
Authorization: Bearer <refresh_token>

Response: 200 OK
{
  "access_token": "new_jwt_token"
}
```

#### 3. Logout
```http
POST /v1/auth/logout
Authorization: Bearer <access_token>

Response: 200 OK
{
  "message": "Successfully logged out"
}
```

#### 4. Get Current User
```http
GET /v1/auth/me
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "string",
  "username": "string",
  "permissions": ["view_portfolios", "create_allocations", "execute_trades"]
}
```

### Portfolio Group Endpoints

#### 1. List Portfolio Groups
```http
GET /v1/portfolio-groups
Authorization: Bearer <access_token>

Response: 200 OK
{
  "portfolio_groups": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "account_count": 0,
      "total_nav": 0.0,
      "strategy": "string"
    }
  ]
}
```

#### 2. Get Portfolio Group Details
```http
GET /v1/portfolio-groups/{group_id}
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "string",
  "name": "string",
  "description": "string",
  "account_count": 0,
  "total_nav": 0.0,
  "strategy": "string",
  "created_date": "2025-01-01",
  "manager": "string"
}

Response: 404 Not Found
{
  "error": "Portfolio group not found"
}
```

#### 3. Get Portfolio Group Accounts
```http
GET /v1/portfolio-groups/{group_id}/accounts
Authorization: Bearer <access_token>

Response: 200 OK
{
  "accounts": [
    {
      "account_id": "string",
      "account_name": "string",
      "nav": 0.0,
      "cash_available": 0.0,
      "strategy": "string",
      "restrictions": ["string"]
    }
  ],
  "total_accounts": 0,
  "total_nav": 0.0
}
```

### Security Endpoints

#### 1. Search Securities
```http
GET /v1/securities/search?query={cusip_or_ticker}&limit=50
Authorization: Bearer <access_token>

Response: 200 OK
{
  "securities": [
    {
      "cusip": "string",
      "ticker": "string",
      "description": "string",
      "coupon": 0.0,
      "maturity": "2025-01-01",
      "duration": 0.0,
      "oas": 0.0,
      "min_denomination": 1000.0
    }
  ]
}
```

#### 2. Get Security Details
```http
GET /v1/securities/{security_id}
Authorization: Bearer <access_token>

Response: 200 OK
{
  "cusip": "string",
  "ticker": "string",
  "description": "string",
  "coupon": 0.0,
  "maturity": "2025-01-01",
  "duration": 0.0,
  "oas": 0.0,
  "min_denomination": 1000.0
}

Response: 404 Not Found
{
  "error": "Security not found"
}
```

#### 3. Get Security Analytics
```http
GET /v1/securities/{security_id}/analytics
Authorization: Bearer <access_token>

Response: 200 OK
{
  "cusip": "string",
  "price": 100.0,
  "yield": 0.0,
  "duration": 0.0,
  "spread_duration": 0.0,
  "convexity": 0.0,
  "oas": 0.0,
  "dv01": 0.0
}
```

## Pending Endpoints (To Be Implemented)

### Allocation Endpoints

#### 1. Create Allocation Preview
```http
POST /v1/allocations/preview
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "order_id": "string",
  "portfolio_group_id": "string",
  "security_id": "string",
  "total_amount": 0,
  "allocation_method": "pro_rata|custom_weights|minimum_dispersion",
  "custom_weights": {
    "account_id": 0.0
  },
  "constraints": {
    "respect_cash": true,
    "max_concentration": 0.1,
    "min_allocation": 1000
  }
}

Response: 200 OK
{
  "allocation_id": "string",
  "allocations": [
    {
      "account_id": "string",
      "account_name": "string",
      "allocated_amount": 0,
      "allocation_percentage": 0.0,
      "warnings": ["string"]
    }
  ],
  "summary": {
    "total_allocated": 0,
    "allocation_rate": 0.0,
    "accounts_allocated": 0,
    "pre_trade_dispersion": 0.0,
    "post_trade_dispersion": 0.0,
    "improvement": 0.0
  }
}
```

#### 2. Commit Allocation
```http
POST /v1/allocations/{allocation_id}/commit
Authorization: Bearer <access_token>

Response: 202 Accepted
{
  "message": "Allocation committed successfully",
  "task_id": "string",
  "orders": [
    {
      "order_id": "string",
      "account_id": "string",
      "status": "pending"
    }
  ]
}
```

### Order Management Endpoints

#### 1. Modify Order
```http
PUT /v1/orders/{order_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "quantity": 0,
  "limit_price": 0.0
}

Response: 200 OK
{
  "order_id": "string",
  "status": "modified",
  "new_quantity": 0,
  "new_limit_price": 0.0
}
```

#### 2. Cancel Order
```http
DELETE /v1/orders/{order_id}
Authorization: Bearer <access_token>

Response: 200 OK
{
  "order_id": "string",
  "status": "cancelled"
}
```

### Market Data Endpoints

#### 1. Get Account Positions
```http
GET /v1/positions/{account_id}
Authorization: Bearer <access_token>

Response: 200 OK
{
  "positions": [
    {
      "security_id": "string",
      "quantity": 0,
      "market_value": 0.0,
      "cost_basis": 0.0,
      "unrealized_pnl": 0.0,
      "percentage_of_nav": 0.0
    }
  ],
  "total_market_value": 0.0
}
```

#### 2. Get Account Cash
```http
GET /v1/cash/{account_id}
Authorization: Bearer <access_token>

Response: 200 OK
{
  "account_id": "string",
  "cash_balances": {
    "USD": 0.0,
    "available_cash": 0.0,
    "pending_trades": 0.0
  }
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Detailed error message",
  "details": {}
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "An unexpected error occurred",
  "request_id": "uuid"
}
```

## Rate Limiting

The API implements rate limiting:
- 100 requests per minute per user
- 429 Too Many Requests response when exceeded

## Development Notes

### Test Credentials
For development, use:
```json
{
  "username": "demo_user",
  "password": "demo_password"
}
```

### Swagger Documentation
Interactive API documentation is available at:
```
http://localhost:5000/docs
```

### External Dependencies
- **Aladdin API**: Required for portfolio, security, and market data
- **Snowflake**: Required for persistence (optional for development)
- **Redis**: Required for caching and Celery (optional for development)

### Response Times
- Authentication endpoints: < 100ms
- Portfolio/Security searches: 200-500ms (depends on Aladdin)
- Allocation calculations: 100-1000ms (depends on method and size)