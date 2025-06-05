"""Mock securities data"""

from typing import Dict, List, Optional
from .generator import MockDataGenerator

# Create a diverse set of mock securities
MOCK_SECURITIES = [
    # US Treasuries
    {
        "cusip": "912828ZW8",
        "ticker": "T 2.5 05/31/25",
        "description": "US Treasury Note 2.5% Due 05/31/2025",
        "issuer": "US Treasury",
        "coupon": 2.5,
        "maturityDate": "2025-05-31",
        "duration": 2.3,
        "oas": 0,
        "minDenomination": 1000.0,
        "assetType": "GOVT",
        "rating": "AAA",
        "price": 0.98750
    },
    {
        "cusip": "912828A89",
        "ticker": "T 3.0 08/15/27",
        "description": "US Treasury Note 3.0% Due 08/15/2027",
        "issuer": "US Treasury",
        "coupon": 3.0,
        "maturityDate": "2027-08-15",
        "duration": 4.2,
        "oas": 0,
        "minDenomination": 1000.0,
        "assetType": "GOVT",
        "rating": "AAA",
        "price": 0.99125
    },
    {
        "cusip": "912828B45",
        "ticker": "T 4.0 11/30/30",
        "description": "US Treasury Bond 4.0% Due 11/30/2030",
        "issuer": "US Treasury",
        "coupon": 4.0,
        "maturityDate": "2030-11-30",
        "duration": 7.8,
        "oas": 0,
        "minDenomination": 1000.0,
        "assetType": "GOVT",
        "rating": "AAA",
        "price": 1.02500
    },
    
    # Investment Grade Corporates
    {
        "cusip": "459200JX0",
        "ticker": "IBM 3.45 02/19/26",
        "description": "IBM Corp 3.45% Due 02/19/2026",
        "issuer": "IBM Corp",
        "coupon": 3.45,
        "maturityDate": "2026-02-19",
        "duration": 3.8,
        "oas": 85,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "A+",
        "price": 0.97250
    },
    {
        "cusip": "037833CY7",
        "ticker": "AAPL 4.25 05/10/29",
        "description": "Apple Inc 4.25% Due 05/10/2029",
        "issuer": "Apple Inc",
        "coupon": 4.25,
        "maturityDate": "2029-05-10",
        "duration": 6.5,
        "oas": 65,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "AA+",
        "price": 1.01875
    },
    {
        "cusip": "594918BP8",
        "ticker": "MSFT 3.7 08/08/28",
        "description": "Microsoft Corp 3.7% Due 08/08/2028",
        "issuer": "Microsoft Corp",
        "coupon": 3.7,
        "maturityDate": "2028-08-08",
        "duration": 5.4,
        "oas": 55,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "AAA",
        "price": 0.99500
    },
    {
        "cusip": "06051GHZ8",
        "ticker": "BAC 4.0 04/01/27",
        "description": "Bank of America Corp 4.0% Due 04/01/2027",
        "issuer": "Bank of America",
        "coupon": 4.0,
        "maturityDate": "2027-04-01",
        "duration": 4.1,
        "oas": 120,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "A-",
        "price": 0.96750
    },
    {
        "cusip": "46625HKA7",
        "ticker": "JPM 3.9 07/15/26",
        "description": "JPMorgan Chase & Co 3.9% Due 07/15/2026",
        "issuer": "JPMorgan Chase",
        "coupon": 3.9,
        "maturityDate": "2026-07-15",
        "duration": 3.2,
        "oas": 95,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "A-",
        "price": 0.98125
    },
    
    # Utilities
    {
        "cusip": "89352HAL4",
        "ticker": "SO 4.5 03/15/31",
        "description": "Southern Company 4.5% Due 03/15/2031",
        "issuer": "Southern Company",
        "coupon": 4.5,
        "maturityDate": "2031-03-15",
        "duration": 8.2,
        "oas": 110,
        "minDenomination": 1000.0,
        "assetType": "CORP",
        "rating": "BBB+",
        "price": 0.95500
    },
    {
        "cusip": "293795HN5",
        "ticker": "NEE 3.8 09/01/28",
        "description": "NextEra Energy Inc 3.8% Due 09/01/2028",
        "issuer": "NextEra Energy",
        "coupon": 3.8,
        "maturityDate": "2028-09-01",
        "duration": 5.6,
        "oas": 90,
        "minDenomination": 1000.0,
        "assetType": "CORP",
        "rating": "A-",
        "price": 0.97875
    },
    
    # Agencies
    {
        "cusip": "3135G0T45",
        "ticker": "FNMA 3.0 10/15/27",
        "description": "Fannie Mae 3.0% Due 10/15/2027",
        "issuer": "FNMA",
        "coupon": 3.0,
        "maturityDate": "2027-10-15",
        "duration": 4.5,
        "oas": 25,
        "minDenomination": 1000.0,
        "assetType": "AGENCY",
        "rating": "AA+",
        "price": 0.98625
    },
    {
        "cusip": "3137EAEP3",
        "ticker": "FHLMC 3.5 06/01/29",
        "description": "Freddie Mac 3.5% Due 06/01/2029",
        "issuer": "FHLMC",
        "coupon": 3.5,
        "maturityDate": "2029-06-01",
        "duration": 6.1,
        "oas": 30,
        "minDenomination": 1000.0,
        "assetType": "AGENCY",
        "rating": "AA+",
        "price": 0.99250
    },
    
    # High Yield (for testing restrictions)
    {
        "cusip": "345370CQ9",
        "ticker": "F 5.5 12/15/28",
        "description": "Ford Motor Credit 5.5% Due 12/15/2028",
        "issuer": "Ford Motor Credit",
        "coupon": 5.5,
        "maturityDate": "2028-12-15",
        "duration": 5.2,
        "oas": 350,
        "minDenomination": 2000.0,
        "assetType": "CORP",
        "rating": "BB+",
        "price": 0.94250
    }
]


def search_mock_securities(query: str, limit: int = 50) -> List[Dict]:
    """Search mock securities by CUSIP or ticker"""
    query_upper = query.upper()
    results = []
    
    for security in MOCK_SECURITIES:
        # Search in CUSIP, ticker, description, and issuer
        if (query_upper in security["cusip"].upper() or
            query_upper in security["ticker"].upper() or
            query_upper in security["description"].upper() or
            query_upper in security["issuer"].upper()):
            results.append(security.copy())
            
        if len(results) >= limit:
            break
    
    return results


def get_mock_security(cusip: str) -> Optional[Dict]:
    """Get a specific mock security by CUSIP"""
    for security in MOCK_SECURITIES:
        if security["cusip"] == cusip:
            return security.copy()
    return None


def get_mock_security_analytics(cusip: str) -> Optional[Dict]:
    """Get mock analytics for a security"""
    security = get_mock_security(cusip)
    if not security:
        return None
    
    # Generate correlated analytics
    duration = security["duration"]
    spread_duration = MockDataGenerator.generate_spread_duration(duration)
    convexity = MockDataGenerator.generate_convexity(duration)
    
    # Calculate yield based on coupon and price
    years_to_maturity = (int(security["maturityDate"].split("-")[0]) - 2025)
    if years_to_maturity > 0:
        # Simplified yield calculation
        ytm = security["coupon"] + ((100 - security["price"]) / years_to_maturity)
    else:
        ytm = security["coupon"]
    
    return {
        "assetId": cusip,
        "riskByCurrency": {
            "USD": {
                "currency": "USD",
                "price": security["price"],
                "yield": round(ytm, 3),
                "duration": duration,
                "spreadDuration": spread_duration,
                "convexity": convexity,
                "oas": security["oas"],
                "dv01": round(duration * security["price"] * 0.0001, 4),
                "modifiedDuration": round(duration * 0.98, 2),
                "yieldToMaturity": round(ytm, 3),
                "spreadToWorst": security["oas"],
                "optionAdjustedDuration": round(duration * 0.95, 2)
            }
        }
    }