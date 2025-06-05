"""Pro-rata allocation engine implementation"""

import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import uuid

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
    AllocationError
)


class ProRataAllocationEngine(AllocationEngine):
    """
    Pro-rata allocation engine that allocates based on NAV or custom metric
    """
    
    def __init__(self):
        super().__init__("ProRataAllocation")
    
    async def allocate(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        parameters: Dict[str, Any],
        constraints: AllocationConstraints
    ) -> AllocationResult:
        """
        Perform pro-rata allocation across accounts
        
        Parameters:
            base_metric: NAV, MARKET_VALUE, or CUSTOM (default: NAV)
        """
        # Start timing
        start_time = datetime.utcnow()
        
        # Validate inputs
        errors = self.validate_inputs(order, security, accounts, constraints)
        if errors:
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
        
        # Get allocation parameters
        base_metric = parameters.get("base_metric", "NAV")
        
        self.logger.info(
            "Starting pro-rata allocation",
            order_quantity=order.quantity,
            num_accounts=len(accounts),
            base_metric=base_metric
        )
        
        # Calculate weights based on metric
        weights = self._calculate_weights(accounts, base_metric)
        
        # Perform allocation
        allocations = {}
        total_allocated = 0
        warnings = []
        
        for account, weight in zip(accounts, weights):
            if weight == 0:
                continue
            
            # Calculate initial allocation
            target_quantity = order.quantity * weight
            
            # Apply constraints
            allocated_quantity = self._apply_constraints(
                account=account,
                target_quantity=target_quantity,
                security=security,
                order=order,
                constraints=constraints,
                warnings=warnings
            )
            
            if allocated_quantity > 0:
                allocations[account.account_id] = allocated_quantity
                total_allocated += allocated_quantity
        
        # Handle rounding differences
        if total_allocated < order.quantity:
            remainder = order.quantity - total_allocated
            self._distribute_remainder(
                remainder=remainder,
                allocations=allocations,
                accounts=accounts,
                security=security,
                constraints=constraints
            )
            total_allocated = sum(allocations.values())
        
        # Create allocation results
        allocation_results = []
        for account in accounts:
            if account.account_id in allocations:
                allocated_qty = allocations[account.account_id]
                allocation_results.append(self._create_account_allocation(
                    account=account,
                    allocated_quantity=allocated_qty,
                    security=security,
                    order=order
                ))
        
        # Add warnings for skipped accounts
        warnings.extend(self.create_allocation_warnings(
            accounts, allocations, security, constraints
        ))
        
        # Create summary
        summary = AllocationSummary(
            total_allocated=total_allocated,
            unallocated=order.quantity - total_allocated,
            allocation_rate=total_allocated / order.quantity if order.quantity > 0 else 0,
            accounts_allocated=len(allocation_results),
            accounts_skipped=len(accounts) - len(allocation_results)
        )
        
        # Log completion
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(
            "Pro-rata allocation completed",
            allocation_id=str(uuid.uuid4()),
            total_allocated=total_allocated,
            accounts_allocated=len(allocation_results),
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
                "base_metric": base_metric,
                "elapsed_seconds": elapsed_time
            }
        )
    
    def _calculate_weights(self, accounts: List[Account], base_metric: str) -> np.ndarray:
        """Calculate allocation weights based on specified metric"""
        if base_metric == "NAV":
            values = np.array([acc.nav for acc in accounts])
        elif base_metric == "MARKET_VALUE":
            # In practice, would calculate total market value
            values = np.array([acc.nav for acc in accounts])
        elif base_metric == "CUSTOM":
            # Would use custom metric from account metadata
            values = np.array([acc.metadata.get("custom_metric", acc.nav) for acc in accounts])
        else:
            # Default to NAV
            values = np.array([acc.nav for acc in accounts])
        
        # Handle zero total
        total_value = np.sum(values)
        if total_value == 0:
            return np.zeros(len(accounts))
        
        return values / total_value
    
    def _apply_constraints(
        self,
        account: Account,
        target_quantity: float,
        security: Security,
        order: Order,
        constraints: AllocationConstraints,
        warnings: List[AllocationWarning]
    ) -> float:
        """Apply constraints to target allocation"""
        allocated_quantity = target_quantity
        
        # Round to denomination
        if constraints.round_to_denomination:
            allocated_quantity = self.round_to_denomination(
                allocated_quantity, security.min_denomination
            )
        
        # Check minimum allocation
        if allocated_quantity < constraints.min_allocation:
            return 0
        
        # Check cash constraint for buys
        if order.side == "BUY" and constraints.respect_cash:
            price = order.price or security.price
            cash_needed = allocated_quantity * price
            if cash_needed > account.available_cash:
                # Reduce to what account can afford
                affordable_qty = account.available_cash / price
                allocated_quantity = self.round_to_denomination(
                    affordable_qty, security.min_denomination
                )
                
                if allocated_quantity < constraints.min_allocation:
                    return 0
        
        # Check position constraint for sells
        elif order.side == "SELL":
            if allocated_quantity > account.current_position:
                allocated_quantity = self.round_to_denomination(
                    account.current_position, security.min_denomination
                )
        
        # Check concentration limit
        if constraints.max_concentration:
            price = order.price or security.price
            position_value = allocated_quantity * price
            concentration = position_value / account.nav if account.nav > 0 else 0
            
            if concentration > constraints.max_concentration:
                max_value = account.nav * constraints.max_concentration
                allocated_quantity = self.round_to_denomination(
                    max_value / price, security.min_denomination
                )
        
        return allocated_quantity
    
    def _distribute_remainder(
        self,
        remainder: float,
        allocations: Dict[str, float],
        accounts: List[Account],
        security: Security,
        constraints: AllocationConstraints
    ) -> None:
        """Distribute remainder to accounts that can accept it"""
        min_denom = security.min_denomination
        
        if remainder < min_denom:
            return
        
        # Sort accounts by NAV (largest first)
        sorted_accounts = sorted(
            [acc for acc in accounts if acc.account_id in allocations],
            key=lambda x: x.nav,
            reverse=True
        )
        
        for account in sorted_accounts:
            if remainder < min_denom:
                break
            
            # Try to add one denomination
            current_alloc = allocations[account.account_id]
            new_alloc = current_alloc + min_denom
            
            # Check if account can accept more
            if constraints.respect_cash:
                price = security.price
                if new_alloc * price <= account.available_cash:
                    allocations[account.account_id] = new_alloc
                    remainder -= min_denom
    
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