"""Test allocation engines with mock data"""

import asyncio
from datetime import datetime
from typing import List

# Add the app directory to the Python path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.allocation_engines import (
    Account,
    Security,
    Order,
    AllocationConstraints,
    AllocationEngineFactory
)


def create_mock_accounts() -> List[Account]:
    """Create mock accounts for testing"""
    return [
        Account(
            account_id="ACC001",
            account_name="Large Cap Fund",
            nav=100_000_000,
            available_cash=5_000_000,
            current_position=1_000_000,
            active_spread_duration=5.2,
            portfolio_duration=4.8,
            spread_duration=5.0,
            oas=120
        ),
        Account(
            account_id="ACC002",
            account_name="Mid Cap Fund",
            nav=150_000_000,
            available_cash=8_000_000,
            current_position=2_000_000,
            active_spread_duration=4.8,
            portfolio_duration=5.1,
            spread_duration=4.9,
            oas=115
        ),
        Account(
            account_id="ACC003",
            account_name="Small Cap Fund",
            nav=80_000_000,
            available_cash=3_000_000,
            current_position=500_000,
            active_spread_duration=5.5,
            portfolio_duration=4.5,
            spread_duration=5.3,
            oas=125
        ),
        Account(
            account_id="ACC004",
            account_name="International Fund",
            nav=50_000_000,
            available_cash=1_000_000,
            current_position=0,
            active_spread_duration=5.0,
            portfolio_duration=4.9,
            spread_duration=5.1,
            oas=118
        )
    ]


def create_mock_security() -> Security:
    """Create mock security for testing"""
    return Security(
        cusip="912828YW0",
        ticker="T 2.5 08/31/25",
        description="US Treasury Note 2.5% 08/31/2025",
        price=0.985,  # Price per $1 face value (98.5% of par)
        duration=4.2,
        spread_duration=3.8,
        oas=110,
        min_denomination=1000,
        coupon=2.5,
        maturity=datetime(2025, 8, 31)
    )


def create_mock_order(quantity: float) -> Order:
    """Create mock order for testing"""
    return Order(
        security_id="912828YW0",
        side="BUY",
        quantity=quantity,
        settlement_date=datetime.now(),
        price=0.985  # Price per $1000 face value
    )


async def test_pro_rata_allocation():
    """Test pro-rata allocation engine"""
    print("\n" + "=" * 60)
    print("Testing Pro-Rata Allocation Engine")
    print("=" * 60)
    
    # Create test data
    accounts = create_mock_accounts()
    security = create_mock_security()
    order = create_mock_order(10_000_000)  # $10MM order
    
    # Create engine
    engine = AllocationEngineFactory.create_from_string("PRO_RATA")
    
    # Set up parameters and constraints
    parameters = {"base_metric": "NAV"}
    constraints = AllocationConstraints(
        respect_cash=True,
        min_allocation=1000,
        compliance_check=True,
        round_to_denomination=True
    )
    
    # Run allocation
    result = await engine.allocate(order, security, accounts, parameters, constraints)
    
    # Display results
    print(f"\nOrder: {order.side} ${order.quantity:,.0f} of {security.ticker}")
    print(f"Total NAV across accounts: ${sum(acc.nav for acc in accounts):,.0f}")
    
    print("\nAllocation Results:")
    print("-" * 80)
    print(f"{'Account':<20} {'NAV':<15} {'Weight':<10} {'Allocated':<15} {'Notional':<15}")
    print("-" * 80)
    
    total_nav = sum(acc.nav for acc in accounts)
    for allocation in result.allocations:
        account = next(acc for acc in accounts if acc.account_id == allocation.account_id)
        weight = account.nav / total_nav
        print(f"{allocation.account_name:<20} "
              f"${account.nav:>12,.0f} "
              f"{weight:>9.1%} "
              f"{allocation.allocated_quantity:>14,.0f} "
              f"${allocation.allocated_notional:>13,.2f}")
    
    print("-" * 80)
    print(f"{'Total Allocated:':<47} {result.summary.total_allocated:>14,.0f}")
    print(f"{'Unallocated:':<47} {result.summary.unallocated:>14,.0f}")
    print(f"{'Allocation Rate:':<47} {result.summary.allocation_rate:>14.1%}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning.message}")
    
    return result.summary.allocation_rate > 0.9  # Should allocate at least 90%


async def test_custom_weights_allocation():
    """Test custom weights allocation engine"""
    print("\n" + "=" * 60)
    print("Testing Custom Weights Allocation Engine")
    print("=" * 60)
    
    # Create test data
    accounts = create_mock_accounts()
    security = create_mock_security()
    order = create_mock_order(5_000_000)  # $5MM order
    
    # Create engine
    engine = AllocationEngineFactory.create_from_string("CUSTOM_WEIGHTS")
    
    # Set up custom weights
    weights = {
        "ACC001": 0.4,   # 40%
        "ACC002": 0.3,   # 30%
        "ACC003": 0.2,   # 20%
        "ACC004": 0.1    # 10%
    }
    
    parameters = {"weights": weights}
    constraints = AllocationConstraints(
        respect_cash=True,
        min_allocation=1000,
        compliance_check=True,
        round_to_denomination=True
    )
    
    # Run allocation
    result = await engine.allocate(order, security, accounts, parameters, constraints)
    
    # Display results
    print(f"\nOrder: {order.side} ${order.quantity:,.0f} of {security.ticker}")
    
    print("\nAllocation Results:")
    print("-" * 80)
    print(f"{'Account':<20} {'Target Weight':<15} {'Target Qty':<15} {'Allocated':<15}")
    print("-" * 80)
    
    for allocation in result.allocations:
        weight = weights.get(allocation.account_id, 0)
        target_qty = order.quantity * weight
        print(f"{allocation.account_name:<20} "
              f"{weight:>14.1%} "
              f"{target_qty:>14,.0f} "
              f"{allocation.allocated_quantity:>14,.0f}")
    
    print("-" * 80)
    print(f"{'Total Allocated:':<51} {result.summary.total_allocated:>14,.0f}")
    print(f"{'Allocation Rate:':<51} {result.summary.allocation_rate:>14.1%}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning.message}")
    
    return result.summary.allocation_rate > 0.8  # Should allocate at least 80%


async def test_minimum_dispersion_allocation():
    """Test minimum dispersion allocation engine"""
    print("\n" + "=" * 60)
    print("Testing Minimum Dispersion Allocation Engine")
    print("=" * 60)
    
    # Create test data
    accounts = create_mock_accounts()
    security = create_mock_security()
    order = create_mock_order(8_000_000)  # $8MM order
    
    # Create engine
    engine = AllocationEngineFactory.create_from_string("MIN_DISPERSION")
    
    # Set up parameters
    parameters = {
        "target_metric": "ACTIVE_SPREAD_DURATION",
        "tolerance": 0.05,
        "max_iterations": 1000
    }
    constraints = AllocationConstraints(
        respect_cash=True,
        min_allocation=1000,
        compliance_check=True,
        round_to_denomination=True
    )
    
    # Run allocation
    result = await engine.allocate(order, security, accounts, parameters, constraints)
    
    # Display results
    print(f"\nOrder: {order.side} ${order.quantity:,.0f} of {security.ticker}")
    print(f"Target Metric: {parameters['target_metric']}")
    print(f"Tolerance: {parameters['tolerance']:.1%}")
    
    print("\nAllocation Results:")
    print("-" * 90)
    print(f"{'Account':<20} {'Pre-ASD':<10} {'Post-ASD':<10} {'Allocated':<15} {'Cash Used':<15}")
    print("-" * 90)
    
    for allocation in result.allocations:
        print(f"{allocation.account_name:<20} "
              f"{allocation.pre_trade_metrics.active_spread_duration:>9.3f} "
              f"{allocation.post_trade_metrics.active_spread_duration:>9.3f} "
              f"{allocation.allocated_quantity:>14,.0f} "
              f"${allocation.cash_used:>13,.2f}")
    
    print("-" * 90)
    
    if result.summary.dispersion_metrics:
        dm = result.summary.dispersion_metrics
        print(f"\nDispersion Metrics:")
        print(f"Pre-trade Std Dev:  {dm.pre_trade_std_dev:.4f}")
        print(f"Post-trade Std Dev: {dm.post_trade_std_dev:.4f}")
        print(f"Improvement:        {dm.improvement:.1%}")
        print(f"Within Tolerance:   {'Yes' if dm.within_tolerance else 'No'}")
    
    print(f"\nTotal Allocated: {result.summary.total_allocated:,.0f}")
    print(f"Allocation Rate: {result.summary.allocation_rate:.1%}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning.message}")
    
    # Check if dispersion improved
    if result.summary.dispersion_metrics:
        return result.summary.dispersion_metrics.improvement > 0
    return False


async def main():
    """Run all allocation engine tests"""
    print("=" * 60)
    print("Allocation Engine Tests")
    print("=" * 60)
    
    tests = [
        ("Pro-Rata Allocation", test_pro_rata_allocation),
        ("Custom Weights Allocation", test_custom_weights_allocation),
        ("Minimum Dispersion Allocation", test_minimum_dispersion_allocation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<40} {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All allocation engine tests passed!")
    else:
        print("\n❌ Some tests failed. Check the output above.")


if __name__ == "__main__":
    asyncio.run(main())