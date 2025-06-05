"""Mock account and cash data"""

from typing import Dict, List, Optional
from .portfolio_groups import MOCK_ACCOUNTS


def get_mock_cash_positions(account_id: str) -> List[Dict]:
    """Get mock cash positions for an account"""
    
    # Find account info
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
    
    # Return cash position
    cash_available = account_info.get("cashAvailable", 0)
    
    return [
        {
            "currency": "USD",
            "settledCash": cash_available,
            "availableCash": cash_available,
            "pendingCash": 0.0,
            "reservedCash": 0.0
        }
    ]


def get_mock_account_details(account_id: str) -> Optional[Dict]:
    """Get detailed account information"""
    
    # Find account info
    for group_accounts in MOCK_ACCOUNTS.values():
        for account in group_accounts:
            if account["memberTicker"] == account_id:
                return {
                    "accountId": account["memberTicker"],
                    "accountName": account["memberName"],
                    "nav": account["nav"],
                    "cashAvailable": account["cashAvailable"],
                    "strategy": account["strategy"],
                    "restrictions": account.get("restrictions", []),
                    "targetMetrics": {
                        "asd": account.get("target_asd", 5.5),
                        "duration": account.get("target_duration", 5.5),
                        "oas": account.get("target_oas", 85)
                    }
                }
    
    return None


def get_account_cash_balance(account_id: str) -> float:
    """Get available cash balance for an account"""
    
    # Find account info
    for group_accounts in MOCK_ACCOUNTS.values():
        for account in group_accounts:
            if account["memberTicker"] == account_id:
                return account.get("cashAvailable", 0)
    
    return 0.0