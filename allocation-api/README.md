# Allocator Backend

Order Allocation System backend for fixed income portfolio management. This system helps portfolio managers allocate bond orders across multiple accounts using various allocation strategies.

## Features

- **Multiple Allocation Algorithms**
  - Pro-Rata: NAV-based proportional allocation
  - Custom Weights: User-defined percentage allocation
  - Minimum Dispersion: Optimization to minimize spread duration dispersion

- **BlackRock Aladdin Integration** (Mock data available for development)
  - Portfolio groups and accounts
  - Security data and analytics
  - Order management

- **Snowflake Database**
  - Allocation history and audit trail
  - User activity tracking
  - Compliance reporting

## Tech Stack

- **Backend**: Python 3.10+ with Flask
- **Database**: Snowflake
- **Authentication**: JWT
- **API Documentation**: Swagger/OpenAPI
- **Testing**: pytest

## Project Structure

```
backend/
├── allocation-api/          # Main application
│   ├── app/                # Application code
│   │   ├── api/           # REST API endpoints
│   │   ├── core/          # Core functionality
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utilities
│   ├── tests/             # Test suite
│   ├── requirements.txt   # Python dependencies
│   └── run.py            # Application entry point
├── api-schema-contract.txt # API specification
├── implementation-plan.md  # Technical architecture
└── min-dispersion-algorithm.py # Reference algorithm
```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jlancaster7/allocator-backend.git
   cd allocator-backend/allocation-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the API**
   - API: http://localhost:5000/v1
   - Swagger Docs: http://localhost:5000/docs

## Development

### Mock Data Mode

The system includes comprehensive mock data for development without Aladdin access:
- Portfolio groups: PUBLICPRE, BIG6, DP-LB-USD, OPNIC
- Securities with full analytics including spread duration
- Account data with positions and cash

### Authentication

For development, use the demo credentials:
```json
{
  "username": "demo_user",
  "password": "demo_password"
}
```

### Running Tests

```bash
python -m pytest tests/
```

## API Endpoints

### Authentication
- `POST /v1/auth/login` - User login
- `POST /v1/auth/refresh` - Refresh token
- `POST /v1/auth/logout` - Logout
- `GET /v1/auth/me` - Current user info

### Portfolio Management
- `GET /v1/portfolio-groups` - List portfolio groups
- `GET /v1/portfolio-groups/{id}` - Get portfolio group details
- `GET /v1/portfolio-groups/{id}/accounts` - Get group accounts

### Securities
- `GET /v1/securities/search` - Search securities
- `GET /v1/securities/{id}` - Get security details
- `GET /v1/securities/{id}/analytics` - Get security analytics

### Allocations
- `POST /v1/allocations/preview` - Preview allocation
- `POST /v1/allocations/{id}/commit` - Commit allocation

## Configuration

Key environment variables:
- `FLASK_ENV` - Development/production mode
- `SNOWFLAKE_*` - Database connection
- `ALADDIN_*` - Aladdin API (optional)
- `JWT_SECRET_KEY` - Authentication secret
- `MOCK_ALADDIN_DATA` - Enable mock data mode

## License

Proprietary - All rights reserved