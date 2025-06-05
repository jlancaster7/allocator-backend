"""Minimum dispersion allocation engine implementation"""

import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass

from app.services.allocation_engines.base import (
    AllocationEngine,
    AllocationResult,
    AllocationSummary,
    AccountAllocationResult,
    Account,
    Security,
    Order,
    AllocationConstraints,
    AllocationWarning,
    AllocationError,
    AllocationWarningType,
    DispersionMetrics
)


@dataclass
class OptimizationResult:
    """Result from optimization algorithm"""
    allocations: np.ndarray
    success: bool
    message: str
    iterations: int
    final_objective: float


class MinimumDispersionAllocationEngine(AllocationEngine):
    """
    Minimum dispersion allocation engine that minimizes standard deviation
    of a target metric (e.g., active spread duration) across accounts
    """
    
    def __init__(self):
        super().__init__("MinimumDispersionAllocation")
    
    async def allocate(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        parameters: Dict[str, Any],
        constraints: AllocationConstraints
    ) -> AllocationResult:
        """
        Perform minimum dispersion allocation
        
        Parameters:
            target_metric: ACTIVE_SPREAD_DURATION, DURATION, or OAS (default: ACTIVE_SPREAD_DURATION)
            tolerance: Acceptable deviation from target (default: 0.05 = 5%)
            max_iterations: Maximum optimization iterations (default: 1000)
        """
        # Start timing
        start_time = datetime.utcnow()
        
        # Validate inputs
        errors = self.validate_inputs(order, security, accounts, constraints)
        if errors:
            return self._create_error_result(order, accounts, errors)
        
        # Get parameters
        target_metric = parameters.get("target_metric", "ACTIVE_SPREAD_DURATION")
        tolerance = parameters.get("tolerance", 0.05)
        max_iterations = parameters.get("max_iterations", 1000)
        
        self.logger.info(
            "Starting minimum dispersion allocation",
            order_quantity=order.quantity,
            num_accounts=len(accounts),
            target_metric=target_metric,
            tolerance=tolerance
        )
        
        # Calculate current metrics
        current_metrics = self._extract_current_metrics(accounts, target_metric)
        
        # Run optimization
        optimization_result = self._optimize_allocation(
            order=order,
            security=security,
            accounts=accounts,
            current_metrics=current_metrics,
            target_metric=target_metric,
            constraints=constraints,
            max_iterations=max_iterations
        )
        
        # Process optimization results
        if not optimization_result.success:
            self.logger.warning(
                "Optimization failed, falling back to pro-rata",
                message=optimization_result.message
            )
            # Fall back to pro-rata allocation
            optimization_result = self._fallback_prorata(
                order, security, accounts, constraints
            )
        
        # Round allocations to denominations
        rounded_allocations = self._round_allocations(
            optimization_result.allocations,
            security.min_denomination,
            order.quantity
        )
        
        # Create allocation results
        allocations = {}
        warnings = []
        
        for i, (account, allocated_qty) in enumerate(zip(accounts, rounded_allocations)):
            if allocated_qty >= constraints.min_allocation:
                # Final constraint check
                final_qty = self._apply_final_constraints(
                    account, allocated_qty, security, order, constraints, warnings
                )
                if final_qty > 0:
                    allocations[account.account_id] = final_qty
        
        # Create account allocation results
        allocation_results = []
        post_trade_metrics = []
        
        for account in accounts:
            if account.account_id in allocations:
                allocated_qty = allocations[account.account_id]
                result = self._create_account_allocation(
                    account=account,
                    allocated_quantity=allocated_qty,
                    security=security,
                    order=order
                )
                allocation_results.append(result)
                post_trade_metrics.append(
                    self._extract_metric_value(result.post_trade_metrics, target_metric)
                )
        
        # Calculate dispersion metrics
        total_allocated = sum(allocations.values())
        dispersion_metrics = self._calculate_dispersion_metrics(
            current_metrics=current_metrics,
            post_trade_metrics=post_trade_metrics,
            tolerance=tolerance
        )
        
        # Add warnings for unallocated accounts
        warnings.extend(self.create_allocation_warnings(
            accounts, allocations, security, constraints
        ))
        
        # Create summary
        summary = AllocationSummary(
            total_allocated=total_allocated,
            unallocated=order.quantity - total_allocated,
            allocation_rate=total_allocated / order.quantity if order.quantity > 0 else 0,
            accounts_allocated=len(allocation_results),
            accounts_skipped=len(accounts) - len(allocation_results),
            dispersion_metrics=dispersion_metrics
        )
        
        # Log completion
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(
            "Minimum dispersion allocation completed",
            total_allocated=total_allocated,
            accounts_allocated=len(allocation_results),
            pre_trade_std=dispersion_metrics.pre_trade_std_dev,
            post_trade_std=dispersion_metrics.post_trade_std_dev,
            improvement=dispersion_metrics.improvement,
            elapsed_seconds=elapsed_time
        )
        
        return AllocationResult(
            allocation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            order=order,
            allocations=allocation_results,
            summary=summary,
            warnings=warnings,
            errors=[],
            metadata={
                "engine": self.name,
                "target_metric": target_metric,
                "tolerance": tolerance,
                "optimization_iterations": optimization_result.iterations,
                "optimization_success": optimization_result.success,
                "elapsed_seconds": elapsed_time
            }
        )
    
    def _extract_current_metrics(self, accounts: List[Account], target_metric: str) -> np.ndarray:
        """Extract current values of target metric from accounts"""
        if target_metric == "ACTIVE_SPREAD_DURATION":
            return np.array([acc.active_spread_duration for acc in accounts])
        elif target_metric == "DURATION":
            return np.array([acc.portfolio_duration for acc in accounts])
        elif target_metric == "OAS":
            return np.array([acc.oas for acc in accounts])
        else:
            # Default to ASD
            return np.array([acc.active_spread_duration for acc in accounts])
    
    def _optimize_allocation(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        current_metrics: np.ndarray,
        target_metric: str,
        constraints: AllocationConstraints,
        max_iterations: int
    ) -> OptimizationResult:
        """Run optimization to minimize dispersion"""
        n_accounts = len(accounts)
        
        # Define objective function
        def objective(allocations):
            """Minimize standard deviation of post-trade metrics"""
            post_trade_metrics = self._calculate_post_trade_metrics_array(
                allocations, accounts, security, order, current_metrics, target_metric
            )
            return np.std(post_trade_metrics)
        
        # Set up constraints
        optimization_constraints = []
        
        # Sum of allocations must equal order quantity
        optimization_constraints.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - order.quantity
        })
        
        # Cash constraints for buys
        if order.side == "BUY" and constraints.respect_cash:
            price = order.price or security.price
            for i, account in enumerate(accounts):
                optimization_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, i=i, acc=account: acc.available_cash - x[i] * price
                })
        
        # Position constraints for sells
        elif order.side == "SELL":
            for i, account in enumerate(accounts):
                optimization_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, i=i, acc=account: acc.current_position - x[i]
                })
        
        # Set up bounds
        bounds = []
        for account in accounts:
            min_alloc = 0
            
            if order.side == "BUY":
                price = order.price or security.price
                max_alloc = min(order.quantity, account.available_cash / price)
            else:
                max_alloc = min(order.quantity, account.current_position)
            
            bounds.append((min_alloc, max_alloc))
        
        # Initial guess (pro-rata by NAV)
        total_nav = sum(acc.nav for acc in accounts)
        if total_nav > 0:
            initial_guess = np.array([
                order.quantity * (acc.nav / total_nav) for acc in accounts
            ])
        else:
            initial_guess = np.full(n_accounts, order.quantity / n_accounts)
        
        # Run optimization
        try:
            result = minimize(
                objective,
                initial_guess,
                method='SLSQP',
                bounds=bounds,
                constraints=optimization_constraints,
                options={
                    'maxiter': max_iterations,
                    'ftol': 1e-6,
                    'disp': False
                }
            )
            
            return OptimizationResult(
                allocations=result.x,
                success=result.success,
                message=result.message if hasattr(result, 'message') else "",
                iterations=result.nit if hasattr(result, 'nit') else 0,
                final_objective=result.fun if hasattr(result, 'fun') else 0
            )
            
        except Exception as e:
            self.logger.error("Optimization error", error=str(e))
            return OptimizationResult(
                allocations=initial_guess,
                success=False,
                message=str(e),
                iterations=0,
                final_objective=np.inf
            )
    
    def _calculate_post_trade_metrics_array(
        self,
        allocations: np.ndarray,
        accounts: List[Account],
        security: Security,
        order: Order,
        current_metrics: np.ndarray,
        target_metric: str
    ) -> np.ndarray:
        """Calculate post-trade metrics for optimization"""
        post_trade_metrics = []
        price = order.price or security.price
        
        for i, (alloc, account) in enumerate(zip(allocations, accounts)):
            if alloc == 0:
                post_trade_metrics.append(current_metrics[i])
                continue
            
            # Calculate metric change based on allocation
            position_change = alloc if order.side == "BUY" else -alloc
            
            if target_metric == "ACTIVE_SPREAD_DURATION":
                # Simplified ASD calculation
                current_mv = account.current_position * price
                new_mv = (account.current_position + position_change) * price
                
                if account.nav > 0:
                    new_asd_contribution = (new_mv / account.nav) * security.spread_duration
                    old_asd_contribution = (current_mv / account.nav) * security.spread_duration
                    new_asd = account.active_spread_duration - old_asd_contribution + new_asd_contribution
                else:
                    new_asd = account.active_spread_duration
                
                post_trade_metrics.append(new_asd)
                
            elif target_metric == "DURATION":
                # Simplified duration calculation
                if account.nav > 0:
                    old_weight = (account.nav - current_mv) / account.nav
                    new_weight = new_mv / account.nav
                    new_duration = old_weight * account.portfolio_duration + new_weight * security.duration
                else:
                    new_duration = account.portfolio_duration
                
                post_trade_metrics.append(new_duration)
                
            elif target_metric == "OAS":
                # Simplified OAS calculation
                post_trade_metrics.append(security.oas)  # Very simplified
        
        return np.array(post_trade_metrics)
    
    def _fallback_prorata(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        constraints: AllocationConstraints
    ) -> OptimizationResult:
        """Fallback to pro-rata allocation"""
        total_nav = sum(acc.nav for acc in accounts)
        
        if total_nav > 0:
            allocations = np.array([
                order.quantity * (acc.nav / total_nav) for acc in accounts
            ])
        else:
            allocations = np.zeros(len(accounts))
        
        return OptimizationResult(
            allocations=allocations,
            success=True,
            message="Fallback to pro-rata",
            iterations=0,
            final_objective=0
        )
    
    def _round_allocations(
        self,
        allocations: np.ndarray,
        min_denomination: float,
        total_quantity: float
    ) -> np.ndarray:
        """Round allocations to minimum denominations"""
        # Round down to nearest denomination
        rounded = np.floor(allocations / min_denomination) * min_denomination
        
        # Distribute remainder
        total_rounded = np.sum(rounded)
        remainder = total_quantity - total_rounded
        
        if remainder >= min_denomination:
            # Sort by fractional part (largest first)
            fractional_parts = allocations - rounded
            sorted_indices = np.argsort(fractional_parts)[::-1]
            
            # Distribute remainder
            while remainder >= min_denomination:
                for idx in sorted_indices:
                    if remainder >= min_denomination:
                        rounded[idx] += min_denomination
                        remainder -= min_denomination
                    else:
                        break
        
        return rounded
    
    def _apply_final_constraints(
        self,
        account: Account,
        allocated_quantity: float,
        security: Security,
        order: Order,
        constraints: AllocationConstraints,
        warnings: List[AllocationWarning]
    ) -> float:
        """Apply final constraints before allocation"""
        # Check cash for buys
        if order.side == "BUY" and constraints.respect_cash:
            price = order.price or security.price
            if allocated_quantity * price > account.available_cash:
                return 0
        
        # Check position for sells
        elif order.side == "SELL":
            if allocated_quantity > account.current_position:
                return 0
        
        return allocated_quantity
    
    def _calculate_dispersion_metrics(
        self,
        current_metrics: np.ndarray,
        post_trade_metrics: List[float],
        tolerance: float
    ) -> DispersionMetrics:
        """Calculate dispersion metrics"""
        if not post_trade_metrics:
            return DispersionMetrics(
                pre_trade_std_dev=np.std(current_metrics) if len(current_metrics) > 0 else 0,
                post_trade_std_dev=np.std(current_metrics) if len(current_metrics) > 0 else 0,
                improvement=0,
                max_deviation=0,
                min_deviation=0,
                target_value=np.mean(current_metrics) if len(current_metrics) > 0 else 0,
                within_tolerance=False
            )
        
        post_array = np.array(post_trade_metrics)
        pre_std = np.std(current_metrics)
        post_std = np.std(post_array)
        target_value = np.mean(post_array)
        
        improvement = (pre_std - post_std) / pre_std if pre_std > 0 else 0
        
        deviations = np.abs(post_array - target_value)
        max_deviation = np.max(deviations) if len(deviations) > 0 else 0
        min_deviation = np.min(deviations) if len(deviations) > 0 else 0
        
        within_tolerance = all(
            dev / target_value <= tolerance for dev in deviations
        ) if target_value > 0 else False
        
        return DispersionMetrics(
            pre_trade_std_dev=pre_std,
            post_trade_std_dev=post_std,
            improvement=improvement,
            max_deviation=max_deviation,
            min_deviation=min_deviation,
            target_value=target_value,
            within_tolerance=within_tolerance
        )
    
    def _extract_metric_value(self, metrics: Any, target_metric: str) -> float:
        """Extract specific metric value from trade metrics"""
        if target_metric == "ACTIVE_SPREAD_DURATION":
            return metrics.active_spread_duration
        elif target_metric == "DURATION":
            return metrics.duration
        elif target_metric == "OAS":
            return metrics.oas
        else:
            return metrics.active_spread_duration
    
    def _create_account_allocation(
        self,
        account: Account,
        allocated_quantity: float,
        security: Security,
        order: Order
    ) -> AccountAllocationResult:
        """Create allocation result for an account"""
        price = order.price or security.price
        allocated_notional = allocated_quantity * price
        
        cash_used = allocated_notional if order.side == "BUY" else 0
        post_trade_cash = account.available_cash - cash_used
        
        pre_trade_metrics = self.calculate_pre_trade_metrics(account, security)
        post_trade_metrics = self.calculate_post_trade_metrics(
            account, security, allocated_quantity, order.side
        )
        
        return AccountAllocationResult(
            account_id=account.account_id,
            account_name=account.account_name,
            allocated_quantity=allocated_quantity,
            allocated_notional=allocated_notional,
            available_cash=account.available_cash,
            post_trade_cash=post_trade_cash,
            pre_trade_metrics=pre_trade_metrics,
            post_trade_metrics=post_trade_metrics,
            cash_used=cash_used
        )
    
    def _create_error_result(self, order: Order, accounts: List[Account], errors: List[AllocationError]) -> AllocationResult:
        """Create result for allocation with errors"""
        return AllocationResult(
            allocation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            order=order,
            allocations=[],
            summary=AllocationSummary(
                total_allocated=0,
                unallocated=order.quantity,
                allocation_rate=0,
                accounts_allocated=0,
                accounts_skipped=len(accounts)
            ),
            errors=errors
        )