# Allocator Backend

Fixed income order allocation system backend for portfolio management.

## Overview

This repository contains the backend implementation of an order allocation system designed to help fixed income portfolio managers allocate bond orders across multiple accounts using various allocation strategies.

## Repository Structure

```
allocator-backend/
├── allocation-api/           # Main Flask application
│   ├── app/                 # Application code
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
├── aladdin-api-docs/        # BlackRock Aladdin API documentation
├── technical-documentation/ # Technical specs and architecture
│   ├── api-schema-contract.txt
│   ├── implementation-plan.md
│   ├── development_log.md
│   └── min-dispersion-algorithm.py
└── README.md               # This file
```

## Features

- **Multiple Allocation Methods**: Pro-rata, custom weights, and minimum dispersion optimization
- **BlackRock Aladdin Integration**: Portfolio and security data (with mock data for development)
- **Snowflake Database**: Allocation history and audit trail
- **JWT Authentication**: Secure API access
- **RESTful API**: Well-documented endpoints with Swagger UI

## Quick Start

See [allocation-api/README.md](allocation-api/README.md) for detailed setup instructions.

```bash
cd allocation-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## Documentation

- **API Documentation**: Available at http://localhost:5000/docs when running
- **Technical Architecture**: See `technical-documentation/implementation-plan.md`
- **Development History**: See `technical-documentation/development_log.md`
- **API Contract**: See `technical-documentation/api-schema-contract.txt`

## License

Proprietary - All rights reserved