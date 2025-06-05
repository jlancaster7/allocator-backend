# Minimum Dispersion Allocation Algorithm Implementation
# app/services/allocation_algorithms/minimum_dispersion.py

import numpy as np
from scipy.optimize import minimize, LinearConstraint
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Account:
    """Account data structure"""
    account_id: str
    nav: float
    available_cash: float
    current_position: float  # Current position in the security
    active_spread_duration: float  # Current ASD contribution
    portfolio_duration: float  # Portfolio duration
    
    
@dataclass
class Security:
    """Security data structure"""
    cusip: str
    price: float
    duration: float
    spread_duration: float
    min_denomination: float
    

@dataclass
class AllocationResult:
    """Result of allocation for an account"""
    account_id: str
    allocated_quantity: float
    allocated_notional: float
    pre_trade_asd: float
    post_trade_asd: float
    cash_used: float
    

class MinimumDispersionAllocator:
    """
    Implements minimum dispersion allocation algorithm that equalizes
    active spread duration contribution across accounts
    """
    
    def __init__(self, 
                 tolerance: float = 0.05,
                 max_iterations: int = 1000,
                 convergence_threshold: float = 1e-6):
        """
        Initialize the allocator
        
        Args:
            tolerance: Acceptable deviation from target (e.g., 0.05 = 5%)
            max_iterations: Maximum optimization iterations
            convergence_threshold: Convergence threshold for optimizer
        """
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        
    def allocate(self,
                 order_quantity: float,
                 security: Security,
                 accounts: List[Account],
                 side: str = 'BUY') -> Tuple[List[AllocationResult], Dict[str, any]]:
        """
        Allocate order quantity across accounts to minimize dispersion
        
        Args:
            order_quantity: Total quantity to allocate
            security: Security details
            accounts: List of accounts with their data
            side: BUY or SELL
            
        Returns:
            Tuple of (allocations, summary_metrics)
        """
        n_accounts = len(accounts)
        
        if n_accounts == 0:
            return [], {"error": "No accounts provided"}
            
        # Calculate current metrics
        current_asds = self._calculate_current_asds(accounts)
        target_asd = np.mean(current_asds)
        
        # Set up optimization problem
        initial_guess = self._get_initial_allocation(
            order_quantity, security, accounts, side
        )
        
        # Define bounds for each account
        bounds = self._get_allocation_bounds(
            order_quantity, security, accounts, side
        )
        
        # Define constraints
        constraints = self._get_constraints(
            order_quantity, security, accounts, side
        )
        
        # Define objective function
        def objective(allocations):
            """Minimize standard deviation of post-trade ASDs"""
            post_trade_asds = self._calculate_post_trade_asds(
                allocations, security, accounts, side
            )
            return np.std(post_trade_asds)
        
        # Run optimization
        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={
                'maxiter': self.max_iterations,
                'ftol': self.convergence_threshold,
                'disp': False
            }
        )
        
        # Process results
        if not result.success:
            logger.warning(f"Optimization did not converge: {result.message}")
            # Fall back to pro-rata allocation
            allocations = self._fallback_prorata_allocation(
                order_quantity, security, accounts, side
            )
        else:
            allocations = result.x
            
        # Round to minimum denominations
        rounded_allocations = self._round_to_denominations(
            allocations, security.min_denomination
        )
        
        # Create results
        allocation_results = self._create_allocation_results(
            rounded_allocations, security, accounts, side
        )
        
        # Calculate summary metrics
        summary = self._calculate_summary_metrics(
            allocation_results, current_asds, order_quantity
        )
        
        return allocation_results, summary
    
    def _calculate_current_asds(self, accounts: List[Account]) -> np.ndarray:
        """Calculate current active spread duration for each account"""
        return np.array([acc.active_spread_duration for acc in accounts])
    
    def _calculate_post_trade_asds(self,
                                   allocations: np.ndarray,
                                   security: Security,
                                   accounts: List[Account],
                                   side: str) -> np.ndarray:
        """Calculate post-trade active spread duration for each account"""
        post_trade_asds = []
        
        for i, (alloc, account) in enumerate(zip(allocations, accounts)):
            if alloc == 0:
                post_trade_asds.append(account.active_spread_duration)
                continue
                
            # Calculate change in position
            position_change = alloc if side == 'BUY' else -alloc
            
            # Calculate new market value
            current_mv = account.current_position * security.price
            new_mv = (account.current_position + position_change) * security.price
            
            # Calculate portfolio market value (simplified)
            portfolio_mv = account.nav
            
            # Calculate new ASD contribution
            # ASD = (Security MV / Portfolio MV) * Security Spread Duration
            new_asd_contribution = (new_mv / portfolio_mv) * security.spread_duration
            old_asd_contribution = (current_mv / portfolio_mv) * security.spread_duration
            
            # Update account ASD
            new_asd = account.active_spread_duration - old_asd_contribution + new_asd_contribution
            post_trade_asds.append(new_asd)
            
        return np.array(post_trade_asds)
    
    def _get_initial_allocation(self,
                                order_quantity: float,
                                security: Security,
                                accounts: List[Account],
                                side: str) -> np.ndarray:
        """Get initial allocation guess (pro-rata by NAV)"""
        total_nav = sum(acc.nav for acc in accounts)
        allocations = []
        
        for account in accounts:
            weight = account.nav / total_nav
            allocation = order_quantity * weight
            allocations.append(allocation)
            
        return np.array(allocations)
    
    def _get_allocation_bounds(self,
                               order_quantity: float,
                               security: Security,
                               accounts: List[Account],
                               side: str) -> List[Tuple[float, float]]:
        """Get bounds for each account's allocation"""
        bounds = []
        
        for account in accounts:
            # Minimum is 0 or minimum denomination
            min_alloc = 0
            
            # Maximum is limited by available cash (for buys) or position (for sells)
            if side == 'BUY':
                max_cash_alloc = account.available_cash / security.price
                max_alloc = min(order_quantity, max_cash_alloc)
            else:
                max_alloc = min(order_quantity, account.current_position)
                
            bounds.append((min_alloc, max_alloc))
            
        return bounds
    
    def _get_constraints(self,
                        order_quantity: float,
                        security: Security,
                        accounts: List[Account],
                        side: str) -> List[dict]:
        """Define optimization constraints"""
        constraints = []
        
        # Sum of allocations must equal order quantity
        constraints.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - order_quantity
        })
        
        # Cash constraints for each account (for buys)
        if side == 'BUY':
            for i, account in enumerate(accounts):
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, i=i, acc=account: acc.available_cash - x[i] * security.price
                })
                
        # Position constraints for sells
        else:
            for i, account in enumerate(accounts):
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, i=i, acc=account: acc.current_position - x[i]
                })
                
        return constraints
    
    def _round_to_denominations(self,
                                allocations: np.ndarray,
                                min_denomination: float) -> np.ndarray:
        """Round allocations to minimum denominations"""
        rounded = np.floor(allocations / min_denomination) * min_denomination
        
        # Handle remainder
        total_allocated = np.sum(rounded)
        remainder = np.sum(allocations) - total_allocated
        
        if remainder >= min_denomination:
            # Allocate remainder to account with best post-trade metric
            # (In practice, this would be more sophisticated)
            max_idx = np.argmax(allocations - rounded)
            rounded[max_idx] += min_denomination
            
        return rounded
    
    def _fallback_prorata_allocation(self,
                                    order_quantity: float,
                                    security: Security,
                                    accounts: List[Account],
                                    side: str) -> np.ndarray:
        """Fallback to pro-rata allocation if optimization fails"""
        logger.info("Using pro-rata allocation as fallback")
        return self._get_initial_allocation(order_quantity, security, accounts, side)
    
    def _create_allocation_results(self,
                                   allocations: np.ndarray,
                                   security: Security,
                                   accounts: List[Account],
                                   side: str) -> List[AllocationResult]:
        """Create allocation result objects"""
        results = []
        current_asds = self._calculate_current_asds(accounts)
        post_trade_asds = self._calculate_post_trade_asds(
            allocations, security, accounts, side
        )
        
        for i, (alloc, account) in enumerate(zip(allocations, accounts)):
            if alloc > 0:
                result = AllocationResult(
                    account_id=account.account_id,
                    allocated_quantity=alloc,
                    allocated_notional=alloc * security.price,
                    pre_trade_asd=current_asds[i],
                    post_trade_asd=post_trade_asds[i],
                    cash_used=alloc * security.price if side == 'BUY' else 0
                )
                results.append(result)
                
        return results
    
    def _calculate_summary_metrics(self,
                                   allocation_results: List[AllocationResult],
                                   current_asds: np.ndarray,
                                   order_quantity: float) -> Dict[str, any]:
        """Calculate summary metrics for the allocation"""
        if not allocation_results:
            return {
                "total_allocated": 0,
                "unallocated": order_quantity,
                "allocation_rate": 0,
                "accounts_allocated": 0,
                "pre_trade_asd_std": np.std(current_asds),
                "post_trade_asd_std": np.std(current_asds),
                "improvement": 0
            }
            
        total_allocated = sum(r.allocated_quantity for r in allocation_results)
        post_trade_asds = [r.post_trade_asd for r in allocation_results]
        
        pre_std = np.std(current_asds)
        post_std = np.std(post_trade_asds)
        improvement = (pre_std - post_std) / pre_std if pre_std > 0 else 0
        
        return {
            "total_allocated": total_allocated,
            "unallocated": order_quantity - total_allocated,
            "allocation_rate": total_allocated / order_quantity,
            "accounts_allocated": len(allocation_results),
            "pre_trade_asd_std": pre_std,
            "post_trade_asd_std": post_std,
            "improvement": improvement,
            "target_asd": np.mean(post_trade_asds),
            "max_deviation": max(abs(asd - np.mean(post_trade_asds)) for asd in post_trade_asds),
            "within_tolerance": all(
                abs(asd - np.mean(post_trade_asds)) / np.mean(post_trade_asds) <= self.tolerance
                for asd in post_trade_asds
            ) if np.mean(post_trade_asds) > 0 else False
        }


# Example usage
if __name__ == "__main__":
    # Create sample data
    accounts = [
        Account(
            account_id="ACC001",
            nav=100_000_000,
            available_cash=5_000_000,
            current_position=1_000_000,
            active_spread_duration=5.2,
            portfolio_duration=4.8
        ),
        Account(
            account_id="ACC002",
            nav=150_000_000,
            available_cash=8_000_000,
            current_position=2_000_000,
            active_spread_duration=4.8,
            portfolio_duration=5.1
        ),
        Account(
            account_id="ACC003",
            nav=80_000_000,
            available_cash=3_000_000,
            current_position=500_000,
            active_spread_duration=5.5,
            portfolio_duration=4.5
        )
    ]
    
    security = Security(
        cusip="912828YW0",
        price=98.5,
        duration=4.2,
        spread_duration=3.8,
        min_denomination=1000
    )
    
    # Create allocator
    allocator = MinimumDispersionAllocator(tolerance=0.05)
    
    # Run allocation
    results, summary = allocator.allocate(
        order_quantity=10_000_000,
        security=security,
        accounts=accounts,
        side='BUY'
    )
    
    # Print results
    print("Allocation Results:")
    print("-" * 80)
    for result in results:
        print(f"Account: {result.account_id}")
        print(f"  Allocated: {result.allocated_quantity:,.0f}")
        print(f"  Notional: ${result.allocated_notional:,.2f}")
        print(f"  Pre-trade ASD: {result.pre_trade_asd:.3f}")
        print(f"  Post-trade ASD: {result.post_trade_asd:.3f}")
        print(f"  Cash used: ${result.cash_used:,.2f}")
        print()
    
    print("\nSummary Metrics:")
    print("-" * 80)
    for key, value in summary.items():
        if isinstance(value, float):
            if key.endswith('_std') or key == 'improvement':
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")