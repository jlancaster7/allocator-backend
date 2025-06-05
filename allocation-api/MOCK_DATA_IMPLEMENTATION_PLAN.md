# Mock Data Implementation Plan

## Overview

Create a comprehensive mock data system for development/testing when Aladdin API is unavailable. The system should:
1. Detect when in development mode (no Aladdin credentials)
2. Return realistic mock data for all Aladdin endpoints
3. Support the full allocation workflow
4. Be easily toggleable via environment variable

## Key Design Decisions

### 1. Data Architecture
- **Real-time data**: From Aladdin API (portfolios, securities, positions, analytics)
- **Historical data**: Stored in Snowflake (audit trails, allocation history, compliance)
- **Mock mode**: Works without both Aladdin and Snowflake for development/demos
- **Production mode**: Requires both Aladdin (for data) and Snowflake (for persistence)

### 2. Mock Data Architecture
```
app/services/
├── aladdin_client.py         # Main client with mock detection
└── mock_data/
    ├── __init__.py
    ├── generator.py          # Mock data generation utilities
    ├── portfolio_groups.py   # Portfolio group mock data
    ├── securities.py         # Security mock data
    ├── positions.py          # Position mock data
    ├── accounts.py           # Account/cash mock data
    └── analytics.py          # Security analytics mock data
```

## Implementation Steps

### Phase 1: Mock Data Infrastructure

#### 1.1 Environment Detection
```python
# In app/core/config.py
MOCK_ALADDIN_DATA = os.getenv("MOCK_ALADDIN_DATA", "true" if not ALADDIN_CLIENT_ID else "false")
```

#### 1.2 Mock Data Base Classes
```python
# app/services/mock_data/generator.py
class MockDataGenerator:
    """Base class for generating realistic mock data"""
    
    @staticmethod
    def generate_cusip() -> str:
        """Generate realistic CUSIP"""
        
    @staticmethod
    def generate_price(min_price=90, max_price=110) -> float:
        """Generate realistic bond price"""
        
    @staticmethod
    def generate_duration(min_dur=1, max_dur=10) -> float:
        """Generate realistic duration"""
```

### Phase 2: Mock Data Implementation

#### 2.1 Portfolio Groups Mock Data
```python
# app/services/mock_data/portfolio_groups.py

MOCK_PORTFOLIO_GROUPS = [
    {
        "id": "PG001",
        "name": "Investment Grade Corporate",
        "description": "US Investment Grade Corporate Bond Portfolio",
        "strategy": "IG_CORP",
        "account_count": 15,
        "total_nav": 2500000000.00,
        "manager": "John Smith",
        "created_date": "2023-01-15"
    },
    {
        "id": "PG002",
        "name": "High Yield Fixed Income",
        "description": "High Yield Corporate Bond Portfolio",
        "strategy": "HY_CORP",
        "account_count": 8,
        "total_nav": 850000000.00,
        "manager": "Jane Doe",
        "created_date": "2023-03-20"
    },
    {
        "id": "PG003",
        "name": "Government Securities",
        "description": "US Treasury and Agency Portfolio",
        "strategy": "GOVT",
        "account_count": 12,
        "total_nav": 3200000000.00,
        "manager": "Mike Johnson",
        "created_date": "2022-11-01"
    }
]

MOCK_ACCOUNTS = {
    "PG001": [
        {
            "account_id": "ACC001",
            "account_name": "IG Corp Account 1",
            "nav": 250000000.00,
            "cash_available": 5000000.00,
            "strategy": "IG_CORP",
            "restrictions": [],
            "target_asd": 5.2,
            "target_duration": 5.5,
            "target_oas": 95
        },
        # ... more accounts
    ]
}
```

#### 2.2 Securities Mock Data
```python
# app/services/mock_data/securities.py

MOCK_SECURITIES = [
    {
        "cusip": "912828ZW8",
        "ticker": "T 2.5 05/31/25",
        "description": "US Treasury Note 2.5% 05/31/2025",
        "coupon": 2.5,
        "maturity": "2025-05-31",
        "duration": 2.3,
        "oas": 0,
        "min_denomination": 1000,
        "asset_type": "GOVT",
        "issuer": "US Treasury"
    },
    {
        "cusip": "459200JX0",
        "ticker": "IBM 3.45 02/19/26",
        "description": "IBM Corp 3.45% 02/19/2026",
        "coupon": 3.45,
        "maturity": "2026-02-19",
        "duration": 3.8,
        "oas": 85,
        "min_denomination": 1000,
        "asset_type": "CORP",
        "issuer": "IBM Corp",
        "rating": "A+"
    },
    # ... more securities with various characteristics
]
```

#### 2.3 Security Analytics Mock Data
```python
# app/services/mock_data/analytics.py

def generate_security_analytics(cusip: str) -> dict:
    """Generate realistic analytics for a security"""
    base_security = find_security_by_cusip(cusip)
    
    # Generate correlated metrics
    duration = base_security.get("duration", 5.0)
    spread_duration = duration * 0.95  # Spread duration typically slightly less
    convexity = duration * duration * 0.1
    
    return {
        "cusip": cusip,
        "price": random.uniform(95, 105),
        "yield": base_security["coupon"] + random.uniform(-0.5, 1.5),
        "duration": duration,
        "spread_duration": spread_duration,  # Key metric for min dispersion
        "convexity": convexity,
        "oas": base_security.get("oas", 0),
        "dv01": duration * 0.01,
        "asd": duration + random.uniform(-0.5, 0.5),  # Asset swap duration
        "modified_duration": duration * 0.98
    }
```

#### 2.4 Positions Mock Data
```python
# app/services/mock_data/positions.py

def generate_positions(account_id: str) -> list:
    """Generate realistic position data for an account"""
    positions = []
    num_positions = random.randint(20, 50)
    
    for i in range(num_positions):
        security = random.choice(MOCK_SECURITIES)
        quantity = random.randint(100, 5000) * 1000  # In thousands
        
        positions.append({
            "account_id": account_id,
            "security_id": security["cusip"],
            "quantity": quantity,
            "market_value": quantity * security.get("price", 100) / 100,
            "cost_basis": quantity * random.uniform(95, 105) / 100,
            "percentage_of_nav": random.uniform(0.5, 5.0),
            "unrealized_pnl": random.uniform(-50000, 100000)
        })
    
    return positions
```

### Phase 3: Integration with Aladdin Client

#### 3.1 Modified Aladdin Client
```python
# app/services/aladdin_client.py

class AladdinClient:
    def __init__(self, config: Settings):
        self.config = config
        self.use_mock_data = config.MOCK_ALADDIN_DATA.lower() == "true"
        
        if self.use_mock_data:
            logger.info("Using mock Aladdin data for development")
            self._init_mock_data()
        else:
            self._init_real_client()
    
    async def get_portfolio_groups(self):
        if self.use_mock_data:
            return self._get_mock_portfolio_groups()
        return await self._get_real_portfolio_groups()
    
    async def search_securities(self, query: str, limit: int = 50):
        if self.use_mock_data:
            return self._search_mock_securities(query, limit)
        return await self._search_real_securities(query, limit)
```

### Phase 4: Test Data Scenarios

#### 4.1 Allocation Test Scenarios
1. **Large Order, Many Accounts**: Test with 50+ accounts
2. **Cash Constraints**: Some accounts with limited cash
3. **Minimum Denomination**: Test rounding and remainder distribution
4. **Optimization Targets**: Varying ASD, Duration, OAS targets

#### 4.2 Edge Cases
1. **Zero Cash Accounts**: Should be excluded
2. **Restricted Securities**: Some accounts can't buy certain securities
3. **Large Dispersion**: Accounts with very different characteristics
4. **Small Order Size**: Test minimum allocation thresholds

### Phase 5: Mock Data Management

#### 5.1 Data Refresh
```python
# Ability to regenerate mock data with different characteristics
def refresh_mock_data(scenario: str = "default"):
    """Regenerate mock data based on scenario"""
    if scenario == "high_dispersion":
        # Generate accounts with widely varying metrics
    elif scenario == "cash_constrained":
        # Generate accounts with limited cash
    elif scenario == "large_portfolio":
        # Generate 100+ accounts
```

#### 5.2 Persistence (Optional)
```python
# Save/load mock data state for consistent testing
def save_mock_state(filename: str):
    """Save current mock data state to file"""
    
def load_mock_state(filename: str):
    """Load mock data state from file"""
```

## Configuration

### Environment Variables
```bash
# .env.example additions
MOCK_ALADDIN_DATA=true  # Enable mock data
MOCK_DATA_SCENARIO=default  # Mock data scenario
MOCK_DATA_SEED=42  # Random seed for reproducibility
```

### Mock Data Toggles
```python
# Fine-grained control over mock data
MOCK_FEATURES = {
    "portfolio_groups": True,
    "securities": True,
    "analytics": True,
    "positions": True,
    "orders": True,
    "slow_responses": False,  # Simulate API latency
    "random_errors": False    # Simulate API errors
}
```

## Benefits

1. **No External Dependencies**: Can develop/demo without Aladdin access
2. **Realistic Data**: Mock data mirrors production characteristics
3. **Fast Development**: No API rate limits or latency
4. **Test Scenarios**: Easy to test edge cases
5. **Demo Ready**: Can showcase full functionality
6. **Cost Savings**: No API usage during development

## Implementation Timeline

1. **Day 1**: Create mock data infrastructure and base classes
2. **Day 2**: Implement portfolio groups and accounts mock data
3. **Day 3**: Implement securities and analytics mock data
4. **Day 4**: Integrate with Aladdin client and test
5. **Day 5**: Add edge cases and test scenarios

## Snowflake Schema Design (For Production)

### Required Tables
```sql
-- Allocation history
CREATE TABLE allocations (
    allocation_id VARCHAR PRIMARY KEY,
    order_id VARCHAR,
    portfolio_group_id VARCHAR,
    security_id VARCHAR,
    allocation_method VARCHAR,
    total_amount NUMBER,
    allocated_amount NUMBER,
    allocation_rate NUMBER,
    created_by VARCHAR,
    created_at TIMESTAMP,
    status VARCHAR,
    pre_trade_metrics VARIANT,
    post_trade_metrics VARIANT
);

-- Allocation details (line items)
CREATE TABLE allocation_details (
    allocation_detail_id VARCHAR PRIMARY KEY,
    allocation_id VARCHAR REFERENCES allocations,
    account_id VARCHAR,
    allocated_amount NUMBER,
    warnings VARIANT,
    created_at TIMESTAMP
);

-- Audit log
CREATE TABLE audit_log (
    audit_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    action VARCHAR,
    entity_type VARCHAR,
    entity_id VARCHAR,
    changes VARIANT,
    ip_address VARCHAR,
    user_agent VARCHAR,
    created_at TIMESTAMP
);

-- User activity
CREATE TABLE user_activity (
    activity_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    session_id VARCHAR,
    endpoint VARCHAR,
    method VARCHAR,
    status_code NUMBER,
    response_time_ms NUMBER,
    created_at TIMESTAMP
);
```

## Success Criteria

1. All API endpoints return realistic data in mock mode
2. Allocation engines work with mock data
3. Frontend can complete full workflow with mock data
4. Easy to switch between mock and real data
5. Mock data covers all test scenarios
6. Performance is fast (< 50ms response times)
7. In production: All allocations are properly audited in Snowflake