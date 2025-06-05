# Order Allocation System - Implementation Plan

## 1. Technology Stack Decision

### Backend: Python/Flask
- **Framework**: Flask with Flask-RESTful
- **Database**: SQLAlchemy ORM with Snowflake connector
- **API Documentation**: Flask-RESTX (Swagger integration)
- **Async Processing**: Celery with Redis for long-running Aladdin operations
- **Authentication**: Flask-JWT-Extended
- **Validation**: Marshmallow
- **HTTP Client**: httpx for Aladdin API calls

### Frontend: React
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit with RTK Query
- **UI Components**: Material-UI (MUI) v5
- **Data Grid**: AG-Grid for allocation preview
- **Charts**: Recharts for dispersion metrics
- **Forms**: React Hook Form with Yup validation
- **Build Tool**: Vite

## 2. API Contract (Frontend ↔ Backend)

### Base URL Structure
```
https://api.allocation-system.com/v1
```

### Authentication
```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

Response:
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "user": {
    "id": "string",
    "username": "string",
    "permissions": ["string"]
  }
}
```

### Core API Endpoints

#### 1. Portfolio Groups
```http
GET /portfolio-groups
Authorization: Bearer {token}

Response:
{
  "portfolio_groups": [
    {
      "group_id": "string",
      "group_name": "string",
      "account_count": 0,
      "accounts": [
        {
          "account_id": "string",
          "account_name": "string"
        }
      ]
    }
  ]
}
```

#### 2. Security Search
```http
GET /securities/search?query={cusip_or_ticker}
Authorization: Bearer {token}

Response:
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
      "min_denomination": 1000
    }
  ]
}
```

#### 3. Calculate Allocation (Preview)
```http
POST /allocations/preview
Authorization: Bearer {token}
Content-Type: application/json

{
  "order": {
    "security_id": "string",
    "side": "BUY|SELL",
    "quantity": 0,
    "settlement_date": "2025-01-01"
  },
  "allocation_method": "PRO_RATA|CUSTOM_WEIGHTS|MIN_DISPERSION",
  "portfolio_groups": ["string"],
  "parameters": {
    // For PRO_RATA
    "base_metric": "NAV|CUSTOM",
    
    // For CUSTOM_WEIGHTS
    "weights": {
      "account_id": 0.0
    },
    
    // For MIN_DISPERSION
    "target_metric": "ACTIVE_SPREAD_DURATION",
    "tolerance": 0.05,
    "max_iterations": 1000
  },
  "constraints": {
    "respect_cash": true,
    "min_allocation": 1000,
    "compliance_check": true
  }
}

Response:
{
  "allocation_id": "string",
  "timestamp": "2025-01-01T00:00:00Z",
  "order": {
    "security_id": "string",
    "side": "BUY",
    "total_quantity": 0,
    "settlement_date": "2025-01-01"
  },
  "allocations": [
    {
      "account_id": "string",
      "account_name": "string",
      "allocated_quantity": 0,
      "allocated_notional": 0.0,
      "available_cash": 0.0,
      "post_trade_cash": 0.0,
      "pre_trade_metrics": {
        "active_spread_duration": 0.0,
        "contribution_to_duration": 0.0
      },
      "post_trade_metrics": {
        "active_spread_duration": 0.0,
        "contribution_to_duration": 0.0
      }
    }
  ],
  "summary": {
    "total_allocated": 0,
    "unallocated": 0,
    "allocation_rate": 0.0,
    "accounts_allocated": 0,
    "accounts_skipped": 0,
    "dispersion_metrics": {
      "pre_trade_std_dev": 0.0,
      "post_trade_std_dev": 0.0,
      "improvement": 0.0
    }
  },
  "warnings": [
    {
      "type": "INSUFFICIENT_CASH|MIN_LOT_SIZE|COMPLIANCE",
      "account_id": "string",
      "message": "string"
    }
  ],
  "errors": []
}
```

#### 4. Commit Allocation
```http
POST /allocations/{allocation_id}/commit
Authorization: Bearer {token}
Content-Type: application/json

{
  "comment": "string",
  "override_warnings": false
}

Response:
{
  "status": "SUCCESS|FAILED",
  "aladdin_order_ids": ["string"],
  "allocations": [
    {
      "account_id": "string",
      "aladdin_order_id": "string",
      "status": "SUBMITTED|FAILED",
      "message": "string"
    }
  ],
  "audit_id": "string"
}
```

#### 5. Modify Order
```http
PUT /orders/{order_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "quantity": 0,
  "comment": "string"
}

Response:
{
  "status": "SUCCESS|FAILED",
  "aladdin_order_id": "string",
  "message": "string"
}
```

#### 6. Cancel Order
```http
DELETE /orders/{order_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "string"
}

Response:
{
  "status": "SUCCESS|FAILED",
  "message": "string"
}
```

#### 7. Market Data Endpoints
```http
GET /positions/{account_id}?as_of=SOD
Authorization: Bearer {token}

Response:
{
  "positions": [
    {
      "account_id": "string",
      "cusip": "string",
      "quantity": 0,
      "market_value": 0.0,
      "duration": 0.0,
      "spread_duration": 0.0
    }
  ]
}

GET /cash/{account_id}
Authorization: Bearer {token}

Response:
{
  "cash_positions": [
    {
      "currency": "USD",
      "settled_cash": 0.0,
      "available_cash": 0.0
    }
  ]
}
```

## 3. Backend Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Project Setup
```python
# Project structure
order-allocation-backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── allocations.py
│   │   ├── orders.py
│   │   ├── portfolios.py
│   │   └── market_data.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── portfolio.py
│   │   ├── order.py
│   │   └── allocation.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── aladdin_client.py
│   │   ├── allocation_engine.py
│   │   └── compliance_engine.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── order_schema.py
│   │   └── allocation_schema.py
│   └── utils/
│       ├── __init__.py
│       └── calculations.py
├── tests/
├── requirements.txt
└── docker-compose.yml
```

#### 1.2 Core Services

**Aladdin Client Service**
```python
# app/services/aladdin_client.py
import httpx
from typing import Dict, List, Optional
from app.core.config import settings

class AladdinClient:
    def __init__(self):
        self.base_url = settings.ALADDIN_BASE_URL
        self.client = httpx.AsyncClient(
            headers={
                "VND.com.blackrock.Request-ID": self._generate_request_id(),
                "VND.com.blackrock.Origin-Timestamp": self._get_timestamp()
            }
        )
    
    async def get_positions(self, portfolio_ticker: str, pos_type: str = "SOD+Trades") -> List[Dict]:
        """Fetch positions from Aladdin"""
        response = await self.client.get(
            f"{self.base_url}/portfolio-mgmt/positions/v1/position",
            params={"portGroup": portfolio_ticker, "posType": pos_type}
        )
        return response.json()
    
    async def get_cash(self, account_id: str) -> Dict:
        """Fetch cash positions from Aladdin"""
        # Implementation based on Aladdin API
        pass
    
    async def submit_order(self, order_data: Dict) -> Dict:
        """Submit order to Aladdin"""
        response = await self.client.post(
            f"{self.base_url}/trading/order-management/order/v1/order:post",
            json=order_data
        )
        return response.json()
```

**Allocation Engine**
```python
# app/services/allocation_engine.py
from abc import ABC, abstractmethod
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional

class AllocationStrategy(ABC):
    @abstractmethod
    async def allocate(self, order: Dict, accounts: List[Dict], 
                      constraints: Dict) -> List[Dict]:
        pass

class ProRataAllocation(AllocationStrategy):
    async def allocate(self, order: Dict, accounts: List[Dict], 
                      constraints: Dict) -> List[Dict]:
        """Implement pro-rata allocation logic"""
        total_nav = sum(acc['nav'] for acc in accounts)
        allocations = []
        
        for account in accounts:
            weight = account['nav'] / total_nav
            allocated_qty = order['quantity'] * weight
            
            # Round to minimum denomination
            min_denom = constraints.get('min_denomination', 1000)
            allocated_qty = np.floor(allocated_qty / min_denom) * min_denom
            
            if allocated_qty >= min_denom:
                allocations.append({
                    'account_id': account['account_id'],
                    'allocated_quantity': allocated_qty
                })
        
        return allocations

class MinimumDispersionAllocation(AllocationStrategy):
    def __init__(self, target_metric: str = 'active_spread_duration', 
                 tolerance: float = 0.05):
        self.target_metric = target_metric
        self.tolerance = tolerance
    
    async def allocate(self, order: Dict, accounts: List[Dict], 
                      constraints: Dict) -> List[Dict]:
        """Implement minimum dispersion allocation using optimization"""
        # Define objective function (minimize standard deviation)
        def objective(allocations):
            # Calculate post-trade metric for each account
            post_trade_metrics = []
            for i, alloc in enumerate(allocations):
                # Simplified calculation - would need full implementation
                metric = accounts[i][self.target_metric] + alloc * order['impact']
                post_trade_metrics.append(metric)
            
            return np.std(post_trade_metrics)
        
        # Set up constraints
        n_accounts = len(accounts)
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - order['quantity']},  # Sum equals total
        ]
        
        # Add cash constraints
        for i, account in enumerate(accounts):
            constraints_list.append({
                'type': 'ineq', 
                'fun': lambda x, i=i: account['available_cash'] - x[i] * order['price']
            })
        
        # Initial guess (pro-rata)
        x0 = np.array([order['quantity'] / n_accounts] * n_accounts)
        
        # Bounds (0 to max based on cash)
        bounds = [(0, min(order['quantity'], acc['available_cash'] / order['price'])) 
                  for acc in accounts]
        
        # Optimize
        result = minimize(objective, x0, method='SLSQP', 
                         bounds=bounds, constraints=constraints_list)
        
        # Convert to allocations
        allocations = []
        for i, qty in enumerate(result.x):
            if qty > constraints.get('min_denomination', 1000):
                allocations.append({
                    'account_id': accounts[i]['account_id'],
                    'allocated_quantity': qty
                })
        
        return allocations
```

### Phase 2: API Implementation (Week 3-4)

#### 2.1 Flask API Routes
```python
# app/api/allocations.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.allocation_engine import AllocationEngineFactory
from app.services.aladdin_client import AladdinClient
from app.schemas.allocation_schema import AllocationRequestSchema, AllocationResponseSchema

allocations_bp = Blueprint('allocations', __name__)

@allocations_bp.route('/allocations/preview', methods=['POST'])
@jwt_required()
async def preview_allocation():
    """Calculate allocation preview"""
    # Validate request
    schema = AllocationRequestSchema()
    data = schema.load(request.json)
    
    # Get allocation engine
    engine = AllocationEngineFactory.create(data['allocation_method'])
    
    # Fetch required data
    aladdin = AladdinClient()
    accounts = await get_accounts_with_data(data['portfolio_groups'])
    
    # Calculate allocation
    allocations = await engine.allocate(
        order=data['order'],
        accounts=accounts,
        constraints=data['constraints']
    )
    
    # Calculate metrics
    summary = calculate_allocation_summary(allocations, accounts)
    
    # Store preview in cache
    allocation_id = store_preview(allocations, data)
    
    return jsonify({
        'allocation_id': allocation_id,
        'allocations': allocations,
        'summary': summary
    })

@allocations_bp.route('/allocations/<allocation_id>/commit', methods=['POST'])
@jwt_required()
async def commit_allocation(allocation_id: str):
    """Commit allocation to Aladdin"""
    # Retrieve preview
    allocation_data = get_preview(allocation_id)
    
    # Submit to Aladdin
    aladdin = AladdinClient()
    results = []
    
    for allocation in allocation_data['allocations']:
        order_data = build_aladdin_order(allocation, allocation_data['order'])
        result = await aladdin.submit_order(order_data)
        results.append(result)
    
    # Store audit trail
    audit_id = store_audit_trail(allocation_data, results, get_jwt_identity())
    
    return jsonify({
        'status': 'SUCCESS',
        'aladdin_order_ids': [r['order_id'] for r in results],
        'audit_id': audit_id
    })
```

### Phase 3: Integration & Testing (Week 5-6)

#### 3.1 Integration Tests
```python
# tests/test_allocation_engine.py
import pytest
from app.services.allocation_engine import MinimumDispersionAllocation

@pytest.mark.asyncio
async def test_minimum_dispersion_allocation():
    engine = MinimumDispersionAllocation(tolerance=0.05)
    
    order = {
        'quantity': 10000000,
        'price': 100,
        'impact': 0.1
    }
    
    accounts = [
        {'account_id': 'ACC1', 'nav': 100000000, 'active_spread_duration': 5.2, 'available_cash': 5000000},
        {'account_id': 'ACC2', 'nav': 150000000, 'active_spread_duration': 4.8, 'available_cash': 8000000},
        {'account_id': 'ACC3', 'nav': 80000000, 'active_spread_duration': 5.5, 'available_cash': 3000000}
    ]
    
    allocations = await engine.allocate(order, accounts, {'min_denomination': 1000})
    
    assert sum(a['allocated_quantity'] for a in allocations) <= order['quantity']
    assert all(a['allocated_quantity'] >= 1000 for a in allocations)
```

## 4. Frontend Implementation Plan

### Phase 1: Core UI Components (Week 1-2)

#### 4.1 Project Structure
```
order-allocation-frontend/
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   └── endpoints.ts
│   ├── components/
│   │   ├── allocation/
│   │   │   ├── AllocationWorkbench.tsx
│   │   │   ├── OrderEntry.tsx
│   │   │   ├── AllocationMethodSelector.tsx
│   │   │   ├── AllocationPreview.tsx
│   │   │   └── DispersionMetrics.tsx
│   │   ├── common/
│   │   │   ├── SecuritySearch.tsx
│   │   │   └── PortfolioGroupSelector.tsx
│   ├── features/
│   │   ├── allocation/
│   │   │   ├── allocationSlice.ts
│   │   │   └── allocationApi.ts
│   ├── hooks/
│   ├── types/
│   └── utils/
```

#### 4.2 Main Components

**Allocation Workbench Component**
```typescript
// src/components/allocation/AllocationWorkbench.tsx
import React, { useState } from 'react';
import { Box, Stepper, Step, StepLabel, Paper } from '@mui/material';
import OrderEntry from './OrderEntry';
import AllocationMethodSelector from './AllocationMethodSelector';
import AllocationPreview from './AllocationPreview';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';

const AllocationWorkbench: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const dispatch = useAppDispatch();
  
  const steps = ['Order Entry', 'Allocation Method', 'Preview & Commit'];
  
  const handleNext = () => {
    setActiveStep((prevStep) => prevStep + 1);
  };
  
  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
  };
  
  return (
    <Box sx={{ width: '100%' }}>
      <Stepper activeStep={activeStep}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      
      <Paper sx={{ mt: 3, p: 3 }}>
        {activeStep === 0 && <OrderEntry onNext={handleNext} />}
        {activeStep === 1 && (
          <AllocationMethodSelector 
            onNext={handleNext} 
            onBack={handleBack} 
          />
        )}
        {activeStep === 2 && (
          <AllocationPreview 
            onBack={handleBack}
            onCommit={handleCommit}
          />
        )}
      </Paper>
    </Box>
  );
};
```

**Allocation Preview Grid**
```typescript
// src/components/allocation/AllocationPreview.tsx
import React, { useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { Box, Button, Alert } from '@mui/material';
import { usePreviewAllocationQuery, useCommitAllocationMutation } from '../../features/allocation/allocationApi';

const AllocationPreview: React.FC<Props> = ({ onBack, onCommit }) => {
  const { data: preview, isLoading, error } = usePreviewAllocationQuery();
  const [commitAllocation, { isLoading: isCommitting }] = useCommitAllocationMutation();
  
  const columnDefs = [
    { field: 'account_id', headerName: 'Account' },
    { field: 'account_name', headerName: 'Account Name' },
    { 
      field: 'allocated_quantity', 
      headerName: 'Allocated Qty',
      valueFormatter: (params) => params.value.toLocaleString()
    },
    {
      field: 'allocated_notional',
      headerName: 'Notional',
      valueFormatter: (params) => `$${params.value.toLocaleString()}`
    },
    {
      field: 'post_trade_metrics.active_spread_duration',
      headerName: 'Post-Trade ASD',
      valueFormatter: (params) => params.value.toFixed(2)
    }
  ];
  
  const handleCommit = async () => {
    try {
      await commitAllocation({ 
        allocation_id: preview.allocation_id 
      }).unwrap();
      onCommit();
    } catch (error) {
      console.error('Failed to commit allocation:', error);
    }
  };
  
  return (
    <Box>
      {preview?.warnings.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {preview.warnings.length} warnings found. Review before committing.
        </Alert>
      )}
      
      <Box sx={{ height: 400, width: '100%' }}>
        <AgGridReact
          rowData={preview?.allocations}
          columnDefs={columnDefs}
          defaultColDef={{
            sortable: true,
            filter: true,
            resizable: true
          }}
        />
      </Box>
      
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button onClick={onBack}>Back</Button>
        <Button 
          variant="contained" 
          onClick={handleCommit}
          disabled={isCommitting}
        >
          Commit Allocation
        </Button>
      </Box>
    </Box>
  );
};
```

### Phase 2: State Management & API Integration (Week 3-4)

#### 4.3 Redux Store Setup
```typescript
// src/features/allocation/allocationSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AllocationRequest, AllocationPreview } from '../../types/allocation';

interface AllocationState {
  currentRequest: AllocationRequest | null;
  preview: AllocationPreview | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: AllocationState = {
  currentRequest: null,
  preview: null,
  isLoading: false,
  error: null
};

const allocationSlice = createSlice({
  name: 'allocation',
  initialState,
  reducers: {
    setOrderDetails: (state, action: PayloadAction<OrderDetails>) => {
      state.currentRequest = {
        ...state.currentRequest,
        order: action.payload
      };
    },
    setAllocationMethod: (state, action: PayloadAction<AllocationMethod>) => {
      state.currentRequest = {
        ...state.currentRequest,
        allocation_method: action.payload.method,
        parameters: action.payload.parameters
      };
    }
  }
});
```

#### 4.4 API Integration
```typescript
// src/features/allocation/allocationApi.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { AllocationRequest, AllocationPreview } from '../../types/allocation';

export const allocationApi = createApi({
  reducerPath: 'allocationApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    }
  }),
  endpoints: (builder) => ({
    previewAllocation: builder.mutation<AllocationPreview, AllocationRequest>({
      query: (request) => ({
        url: '/allocations/preview',
        method: 'POST',
        body: request
      })
    }),
    commitAllocation: builder.mutation<CommitResponse, { allocation_id: string }>({
      query: ({ allocation_id }) => ({
        url: `/allocations/${allocation_id}/commit`,
        method: 'POST'
      })
    }),
    searchSecurities: builder.query<Security[], string>({
      query: (query) => `/securities/search?query=${query}`
    })
  })
});

export const {
  usePreviewAllocationMutation,
  useCommitAllocationMutation,
  useSearchSecuritiesQuery
} = allocationApi;
```

## 5. Deployment Strategy

### 5.1 Backend Deployment
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
      - SNOWFLAKE_USER=${SNOWFLAKE_USER}
      - SNOWFLAKE_PASSWORD=${SNOWFLAKE_PASSWORD}
      - ALADDIN_API_KEY=${ALADDIN_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
      
  celery:
    build: .
    command: celery -A app.celery worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
```

### 5.2 Frontend Deployment
```dockerfile
# Frontend Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 6. Testing Strategy

### 6.1 Backend Testing
- Unit tests for allocation algorithms
- Integration tests for Aladdin API calls
- Load testing for concurrent allocations
- Mock Aladdin responses for development

### 6.2 Frontend Testing
- Component testing with React Testing Library
- E2E tests with Cypress
- Visual regression testing
- Performance testing with Lighthouse

## 7. Monitoring & Observability

### 7.1 Logging
- Structured logging with correlation IDs
- Audit trail for all allocations
- Error tracking with Sentry

### 7.2 Metrics
- API response times
- Allocation calculation performance
- Aladdin API success rates
- User interaction analytics

## 8. Timeline Summary

**Total Duration: 6 weeks**

- **Week 1-2**: Backend core infrastructure & allocation engines
- **Week 3-4**: API implementation & frontend core components
- **Week 5**: Integration, testing, and bug fixes
- **Week 6**: Deployment setup, documentation, and training

## 9. Risk Mitigation

1. **Aladdin API Rate Limits**: Implement caching and request queuing
2. **Calculation Performance**: Use Celery for async processing
3. **Data Consistency**: Implement optimistic locking
4. **Compliance Integration**: Modular design for easy rule addition