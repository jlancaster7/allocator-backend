"""Mock positions data"""

import random
from typing import Dict, List
from .securities import MOCK_SECURITIES
from .portfolio_groups import MOCK_ACCOUNTS

# Cache for generated positions
_positions_cache = {}


def get_mock_positions(account_id: str, pos_type: str = "SOD") -> List[Dict]:
    """Get mock positions for an account"""
    
    # Check cache first
    cache_key = f"{account_id}_{pos_type}"
    if cache_key in _positions_cache:
        return _positions_cache[cache_key].copy()
    
    # Find account to get its characteristics
    account_info = None
    for group_accounts in MOCK_ACCOUNTS.values():
        for account in group_accounts:
            if account["memberTicker"] == account_id:
                account_info = account
                break
        if account_info:
            break
    
    if not account_info:
        return []
    
    # Generate positions based on account strategy and restrictions
    positions = []
    total_market_value = 0
    nav = account_info["nav"]
    cash_available = account_info["cashAvailable"]
    invested_value = nav - cash_available
    
    # Filter securities based on restrictions
    eligible_securities = []
    for security in MOCK_SECURITIES:
        # Apply restrictions
        if "INVESTMENT_GRADE_ONLY" in account_info.get("restrictions", []):
            if security["rating"] in ["BB+", "BB", "B"]:
                continue
        
        if "NO_HIGH_YIELD" in account_info.get("restrictions", []):
            if security["rating"] in ["BB+", "BB", "B"]:
                continue
        
        if "NO_EMERGING_MARKETS" in account_info.get("restrictions", []):
            # In our mock data, we don't have EM bonds, so this is OK
            pass
        
        eligible_securities.append(security)
    
    # Select 15-30 securities for the portfolio
    num_positions = random.randint(15, 30)
    selected_securities = random.sample(
        eligible_securities, 
        min(num_positions, len(eligible_securities))
    )
    
    # Allocate invested value across positions
    # Use a power law distribution for more realistic position sizing
    weights = [random.random() ** 0.5 for _ in selected_securities]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    
    for i, security in enumerate(selected_securities):
        # Calculate position size
        position_value = invested_value * normalized_weights[i]
        
        # Calculate quantity (face value)
        price_decimal = security["price"] / 100  # Convert to decimal
        quantity = round(position_value / price_decimal, -3)  # Round to nearest 1000
        
        # Ensure minimum denomination
        min_denom = security["minDenomination"]
        if quantity < min_denom:
            quantity = min_denom
        
        # Recalculate market value with actual quantity
        market_value = quantity * price_decimal
        total_market_value += market_value
        
        # Create position record
        position = {
            "accountId": account_id,
            "assetId": security["cusip"],
            "ticker": security["ticker"],
            "description": security["description"],
            "quantity": quantity,
            "marketValue": round(market_value, 2),
            "price": security["price"],
            "costBasis": round(quantity * random.uniform(0.95, 1.05), 2),
            "duration": security["duration"],
            "spreadDuration": security["duration"] * 0.95,  # Approximate
            "oas": security["oas"],
            "percentageOfNav": round((market_value / nav) * 100, 2),
            "unrealizedPnl": round(random.uniform(-50000, 100000), 2),
            "posType": pos_type
        }
        
        positions.append(position)
    
    # Sort by market value descending
    positions.sort(key=lambda x: x["marketValue"], reverse=True)
    
    # Cache the result
    _positions_cache[cache_key] = positions
    
    return positions.copy()


def get_account_positions(account_id: str) -> List[Dict]:
    """Get positions for an account (alias for API compatibility)"""
    positions = get_mock_positions(account_id, "SOD")
    # Transform to simpler format if needed
    return [{
        "cusip": pos["assetId"],
        "ticker": pos.get("ticker", ""),
        "description": pos.get("description", ""),
        "quantity": pos["quantity"],
        "market_value": pos["marketValue"],
        "duration": pos.get("duration", 0),
        "spread_duration": pos.get("spreadDuration", 0),
        "oas": pos.get("oas", 0)
    } for pos in positions]