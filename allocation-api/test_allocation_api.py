#!/usr/bin/env python3
"""Test script for allocation API endpoints"""

import requests
import json
import sys

# API base URL
BASE_URL = "http://localhost:5000/v1"

# Test credentials
USERNAME = "demo_user"
PASSWORD = "demo_password"

def login():
    """Login and get JWT token"""
    print("1. Logging in...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Login successful! User: {data['user']['username']}")
        return data["access_token"]
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

def get_portfolio_groups(token):
    """Get available portfolio groups"""
    print("\n2. Fetching portfolio groups...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/portfolio-groups", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {len(data['portfolio_groups'])} portfolio groups:")
        for group in data['portfolio_groups']:
            print(f"   - {group['id']}: {group['name']} ({group['account_count']} accounts, NAV: ${group['total_nav']:,.0f})")
        return data['portfolio_groups']
    else:
        print(f"✗ Failed to get portfolio groups: {response.status_code}")
        print(response.text)
        return []

def test_pro_rata_allocation(token, portfolio_groups):
    """Test PRO_RATA allocation method"""
    print("\n3. Testing PRO_RATA allocation...")
    
    # Select first two portfolio groups
    selected_groups = [g['id'] for g in portfolio_groups[:2]]
    print(f"   Selected groups: {selected_groups}")
    
    allocation_request = {
        "order": {
            "security_id": "912828ZW8",  # 30-Year Treasury
            "side": "BUY",
            "quantity": 10000000,  # $10M face value
            "settlement_date": "2024-01-15"
        },
        "allocation_method": "PRO_RATA",
        "portfolio_groups": selected_groups,
        "parameters": {
            "base_metric": "NAV"
        },
        "constraints": {
            "respect_cash": True,
            "min_allocation": 10000,
            "compliance_check": True,
            "round_to_denomination": True
        }
    }
    
    print(f"   Order: BUY $10M of 912828ZW8 (30-Year Treasury)")
    print(f"   Method: PRO_RATA based on NAV")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/allocations/preview", 
                           json=allocation_request, 
                           headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Allocation preview successful!")
        print(f"   Allocation ID: {data['allocation_id']}")
        print(f"   Total allocated: ${data['summary']['total_allocated']:,.0f}")
        print(f"   Accounts allocated: {data['summary']['accounts_allocated']}")
        print(f"   Allocation rate: {data['summary']['allocation_rate']*100:.1f}%")
        
        print("\n   Top 5 allocations:")
        for i, alloc in enumerate(data['allocations'][:5]):
            print(f"   {i+1}. {alloc['account_id']} ({alloc['account_name']})")
            print(f"      Allocated: ${alloc['allocated_quantity']:,.0f} (${alloc['allocated_notional']:,.2f})")
            print(f"      Available cash: ${alloc['available_cash']:,.2f}")
            print(f"      Post-trade cash: ${alloc['post_trade_cash']:,.2f}")
        
        if data.get('warnings'):
            print(f"\n   Warnings: {len(data['warnings'])}")
            for warn in data['warnings'][:3]:
                print(f"   - {warn['type']}: {warn['message']}")
        
        return data
    else:
        print(f"✗ Allocation preview failed: {response.status_code}")
        print(response.text)
        return None

def test_custom_weights_allocation(token, portfolio_groups):
    """Test CUSTOM_WEIGHTS allocation method"""
    print("\n4. Testing CUSTOM_WEIGHTS allocation...")
    
    # Get accounts for first portfolio group
    group_id = portfolio_groups[0]['id']
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/portfolio-groups/{group_id}/accounts", headers=headers)
    
    if response.status_code != 200:
        print(f"✗ Failed to get accounts for {group_id}")
        return None
    
    accounts = response.json()['accounts'][:5]  # Use first 5 accounts
    
    # Create custom weights (60%, 20%, 10%, 5%, 5%)
    weights = {}
    weight_values = [0.6, 0.2, 0.1, 0.05, 0.05]
    for i, account in enumerate(accounts):
        weights[account['account_id']] = weight_values[i]
    
    print(f"   Using custom weights for {len(weights)} accounts")
    
    allocation_request = {
        "order": {
            "security_id": "912828YK5",  # 5-Year Treasury
            "side": "BUY",
            "quantity": 5000000,  # $5M face value
            "settlement_date": "2024-01-15"
        },
        "allocation_method": "CUSTOM_WEIGHTS",
        "portfolio_groups": [group_id],
        "parameters": {
            "weights": weights
        },
        "constraints": {
            "respect_cash": True,
            "min_allocation": 10000,
            "compliance_check": True,
            "round_to_denomination": True
        }
    }
    
    print(f"   Order: BUY $5M of 912828YK5 (5-Year Treasury)")
    print(f"   Method: CUSTOM_WEIGHTS")
    
    response = requests.post(f"{BASE_URL}/allocations/preview", 
                           json=allocation_request, 
                           headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Custom weights allocation successful!")
        print(f"   Total allocated: ${data['summary']['total_allocated']:,.0f}")
        
        print("\n   Allocations by weight:")
        for alloc in data['allocations']:
            weight = weights.get(alloc['account_id'], 0)
            print(f"   - {alloc['account_id']}: {weight*100:.0f}% weight -> ${alloc['allocated_quantity']:,.0f}")
        
        return data
    else:
        print(f"✗ Custom weights allocation failed: {response.status_code}")
        print(response.text)
        return None

def test_min_dispersion_allocation(token, portfolio_groups):
    """Test MIN_DISPERSION allocation method"""
    print("\n5. Testing MIN_DISPERSION allocation...")
    
    selected_groups = [portfolio_groups[0]['id']]  # Use one group for min dispersion
    
    allocation_request = {
        "order": {
            "security_id": "912828XE9",  # 10-Year Treasury
            "side": "BUY",
            "quantity": 8000000,  # $8M face value
            "settlement_date": "2024-01-15"
        },
        "allocation_method": "MIN_DISPERSION",
        "portfolio_groups": selected_groups,
        "parameters": {
            "target_metric": "ACTIVE_SPREAD_DURATION",
            "tolerance": 0.05,
            "max_iterations": 1000
        },
        "constraints": {
            "respect_cash": True,
            "min_allocation": 10000,
            "compliance_check": True,
            "round_to_denomination": True
        }
    }
    
    print(f"   Order: BUY $8M of 912828XE9 (10-Year Treasury)")
    print(f"   Method: MIN_DISPERSION targeting ACTIVE_SPREAD_DURATION")
    print(f"   Portfolio group: {selected_groups[0]}")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/allocations/preview", 
                           json=allocation_request, 
                           headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Min dispersion allocation successful!")
        print(f"   Total allocated: ${data['summary']['total_allocated']:,.0f}")
        print(f"   Accounts allocated: {data['summary']['accounts_allocated']}")
        
        if data['summary'].get('dispersion_metrics'):
            metrics = data['summary']['dispersion_metrics']
            print(f"\n   Dispersion metrics:")
            print(f"   - Pre-trade std dev: {metrics['pre_trade_std_dev']:.3f}")
            print(f"   - Post-trade std dev: {metrics['post_trade_std_dev']:.3f}")
            print(f"   - Improvement: {metrics['improvement']:.3f}")
        
        return data
    else:
        print(f"✗ Min dispersion allocation failed: {response.status_code}")
        print(response.text)
        return None

def test_allocation_commit(token, allocation_id):
    """Test committing an allocation"""
    print(f"\n6. Testing allocation commit...")
    print(f"   Allocation ID: {allocation_id}")
    
    commit_request = {
        "comment": "Test allocation commit",
        "override_warnings": False
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/allocations/{allocation_id}/commit", 
                           json=commit_request, 
                           headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Allocation committed successfully!")
        print(f"   Status: {data['status']}")
        print(f"   Aladdin order IDs: {len(data['aladdin_order_ids'])} orders created")
        print(f"   Audit ID: {data['audit_id']}")
        
        print("\n   First 3 order results:")
        for i, result in enumerate(data['allocations'][:3]):
            print(f"   {i+1}. Account {result['account_id']}: {result['status']} - {result['aladdin_order_id']}")
        
        return data
    else:
        print(f"✗ Allocation commit failed: {response.status_code}")
        print(response.text)
        return None

def main():
    """Run all tests"""
    print("=" * 60)
    print("ORDER ALLOCATION API TEST SUITE")
    print("=" * 60)
    
    # Login
    token = login()
    
    # Get portfolio groups
    portfolio_groups = get_portfolio_groups(token)
    
    if not portfolio_groups:
        print("No portfolio groups found. Exiting.")
        return
    
    # Test different allocation methods
    allocation1 = test_pro_rata_allocation(token, portfolio_groups)
    
    allocation2 = test_custom_weights_allocation(token, portfolio_groups)
    
    allocation3 = test_min_dispersion_allocation(token, portfolio_groups)
    
    # Test commit on the first successful allocation
    if allocation1:
        test_allocation_commit(token, allocation1['allocation_id'])
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()