"""Mock portfolio groups data"""

from typing import Dict, List, Optional
from .generator import MockDataGenerator

# Mock portfolio groups with generic names
MOCK_PORTFOLIO_GROUPS = [
    {
        "ticker": "ALPHA-CORE",
        "name": "Alpha Core Fixed Income",
        "description": "Core fixed income investment portfolio",
        "strategy": "CORE",
        "totalNav": 4500000000.00,
        "manager": "Sarah Johnson",
        "createdDate": "2022-03-15",
        "account_count": 12
    },
    {
        "ticker": "INST-PRIME",
        "name": "Institutional Prime",
        "description": "Prime institutional investor portfolio group",
        "strategy": "CORE_PLUS",
        "totalNav": 8200000000.00,
        "manager": "Michael Chen",
        "createdDate": "2021-01-10",
        "account_count": 6
    },
    {
        "ticker": "DURATION-PRO",
        "name": "Duration Professional",
        "description": "Long duration professional bond portfolio",
        "strategy": "LDI",
        "totalNav": 12500000000.00,
        "manager": "Jennifer Martinez",
        "createdDate": "2020-06-01",
        "account_count": 11
    },
    {
        "ticker": "BALANCED-SELECT",
        "name": "Balanced Select Portfolio",
        "description": "Select balanced investment portfolio",
        "strategy": "BALANCED",
        "totalNav": 3100000000.00,
        "manager": "David Thompson",
        "createdDate": "2023-02-20",
        "account_count": 2
    }
]

# Generate mock accounts for each portfolio group
MOCK_ACCOUNTS = {}

# ALPHA-CORE accounts (12 core fixed income accounts)
MOCK_ACCOUNTS["ALPHA-CORE"] = [
    {
        "memberTicker": f"ALPHA{str(i).zfill(3)}",
        "memberName": f"Alpha Account {i}",
        "nav": MockDataGenerator.generate_nav(100_000_000, 500_000_000),
        "cashAvailable": 0,  # Will be calculated based on NAV
        "strategy": "PREFERRED",
        "restrictions": ["NO_TOBACCO", "ESG_COMPLIANT"] if i % 3 == 0 else [],
        "target_asd": 5.5 + (i % 5) * 0.2,
        "target_duration": 5.8 + (i % 5) * 0.2,
        "target_oas": 75 + (i % 4) * 10
    }
    for i in range(1, 13)
]

# INST-PRIME accounts (6 large institutional accounts)
INST_PRIME_NAMES = ["Prime Capital", "Elite Investments", "Premier Holdings", "Select Partners", "Strategic Fund", "Executive Management"]
MOCK_ACCOUNTS["INST-PRIME"] = [
    {
        "memberTicker": f"INST{str(i).zfill(3)}",
        "memberName": INST_PRIME_NAMES[i-1],
        "nav": MockDataGenerator.generate_nav(800_000_000, 2_000_000_000),
        "cashAvailable": 0,
        "strategy": "CORE_PLUS",
        "restrictions": ["NO_EMERGING_MARKETS"] if i % 2 == 0 else [],
        "target_asd": 6.0 + (i % 3) * 0.3,
        "target_duration": 6.2 + (i % 3) * 0.3,
        "target_oas": 95 + (i % 3) * 15
    }
    for i in range(1, 7)
]

# DURATION-PRO accounts (11 duration-focused accounts)
MOCK_ACCOUNTS["DURATION-PRO"] = [
    {
        "memberTicker": f"DUR{str(i).zfill(3)}",
        "memberName": f"Duration Portfolio {i}",
        "nav": MockDataGenerator.generate_nav(200_000_000, 1_000_000_000),
        "cashAvailable": 0,
        "strategy": "LDI",
        "restrictions": ["INVESTMENT_GRADE_ONLY"],
        "target_asd": 8.5 + (i % 6) * 0.4,  # Longer duration for pension funds
        "target_duration": 9.0 + (i % 6) * 0.4,
        "target_oas": 65 + (i % 5) * 8
    }
    for i in range(1, 12)
]

# BALANCED-SELECT accounts (2 balanced portfolio accounts)
MOCK_ACCOUNTS["BALANCED-SELECT"] = [
    {
        "memberTicker": f"BAL{str(i).zfill(3)}",
        "memberName": f"Balanced Account {i}",
        "nav": MockDataGenerator.generate_nav(150_000_000, 400_000_000),
        "cashAvailable": 0,
        "strategy": "BALANCED",
        "restrictions": ["NO_HIGH_YIELD"] if i % 4 == 0 else [],
        "target_asd": 4.8 + (i % 4) * 0.25,
        "target_duration": 5.0 + (i % 4) * 0.25,
        "target_oas": 85 + (i % 4) * 12
    }
    for i in range(1, 3)
]

# Calculate cash for each account based on NAV
for group_id, accounts in MOCK_ACCOUNTS.items():
    for account in accounts:
        # Conservative cash for pension funds, normal for others
        conservative = group_id == "DURATION-PRO"
        cash_pct = MockDataGenerator.generate_cash_percentage(conservative)
        account["cashAvailable"] = round(account["nav"] * cash_pct, -3)  # Round to nearest thousand


def get_mock_portfolio_groups() -> List[Dict]:
    """Get all mock portfolio groups"""
    return MOCK_PORTFOLIO_GROUPS.copy()


def get_mock_portfolio_group(group_id: str) -> Optional[Dict]:
    """Get a specific mock portfolio group"""
    for group in MOCK_PORTFOLIO_GROUPS:
        if group["ticker"] == group_id:
            return group.copy()
    return None


def get_mock_portfolio_group_accounts(group_id: str) -> List[Dict]:
    """Get mock accounts for a portfolio group"""
    return MOCK_ACCOUNTS.get(group_id, []).copy()


def get_portfolio_group_accounts(group_id: str) -> List[Dict]:
    """Get accounts for a portfolio group (alias for API compatibility)"""
    accounts = MOCK_ACCOUNTS.get(group_id, []).copy()
    # Transform to expected format for API
    return [{
        "account_id": acc["memberTicker"],
        "account_name": acc["memberName"],
        "nav": acc["nav"],
        "available_cash": acc["cashAvailable"],
        "strategy": acc.get("strategy", ""),
        "restrictions": acc.get("restrictions", [])
    } for acc in accounts]