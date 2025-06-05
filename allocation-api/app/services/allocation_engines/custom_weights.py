"""Custom weights allocation engine implementation"""

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


class CustomWeightsAllocationEngine(AllocationEngine):
    """
    Custom weights allocation engine that allocates based on user-defined weights
    """
    
    def __init__(self):
        super().__init__("CustomWeightsAllocation")
    
    async def allocate(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        parameters: Dict[str, Any],
        constraints: AllocationConstraints
    ) -> AllocationResult:
        """
        Perform allocation based on custom weights
        
        Parameters:
            weights: Dict[account_id, weight] - weights must sum to 1.0
        """
        # Start timing
        start_time = datetime.utcnow()
        
        # Validate inputs
        errors = self.validate_inputs(order, security, accounts, constraints)
        if errors:
            return self._create_error_result(order, accounts, errors)
        
        # Get and validate weights
        weights_dict = parameters.get("weights", {})
        weight_errors = self._validate_weights(weights_dict, accounts)
        if weight_errors:
            return self._create_error_result(order, accounts, weight_errors)
        
        self.logger.info(
            "Starting custom weights allocation",
            order_quantity=order.quantity,
            num_accounts=len(accounts),
            num_weights=len(weights_dict)
        )
        
        # Perform allocation
        allocations = {}
        total_allocated = 0
        warnings = []
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # First pass: allocate based on weights
        for account_id, weight in weights_dict.items():
            if account_id not in account_lookup:
                warnings.append(AllocationWarning(
                    type=AllocationWarningType.COMPLIANCE,
                    account_id=account_id,
                    message=f"Account {account_id} in weights not found in account list"
                ))
                continue
            
            account = account_lookup[account_id]
            
            # Calculate target allocation
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
                allocations[account_id] = allocated_quantity
                total_allocated += allocated_quantity
        
        # Handle unallocated quantity
        if total_allocated < order.quantity:
            unallocated = order.quantity - total_allocated
            self._handle_unallocated(
                unallocated=unallocated,
                allocations=allocations,
                weights_dict=weights_dict,
                account_lookup=account_lookup,
                security=security,
                order=order,
                constraints=constraints,
                warnings=warnings
            )
            total_allocated = sum(allocations.values())
        
        # Create allocation results
        allocation_results = []
        for account_id, allocated_qty in allocations.items():
            account = account_lookup[account_id]
            allocation_results.append(self._create_account_allocation(
                account=account,
                allocated_quantity=allocated_qty,
                security=security,
                order=order
            ))
        
        # Add warnings for accounts with weights but no allocation
        for account_id, weight in weights_dict.items():
            if weight > 0 and account_id not in allocations and account_id in account_lookup:
                account = account_lookup[account_id]
                warnings.extend(self.create_allocation_warnings(
                    [account], {}, security, constraints
                ))
        
        # Create summary
        summary = AllocationSummary(
            total_allocated=total_allocated,
            unallocated=order.quantity - total_allocated,
            allocation_rate=total_allocated / order.quantity if order.quantity > 0 else 0,
            accounts_allocated=len(allocation_results),
            accounts_skipped=len([w for w in weights_dict.values() if w > 0]) - len(allocation_results)
        )
        
        # Log completion
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(
            "Custom weights allocation completed",
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
                "elapsed_seconds": elapsed_time,
                "weights_provided": len(weights_dict)
            }
        )
    
    def _validate_weights(self, weights_dict: Dict[str, float], accounts: List[Account]) -> List[AllocationError]:
        """Validate custom weights"""
        errors = []
        
        if not weights_dict:
            errors.append(AllocationError(
                code="NO_WEIGHTS",
                message="No weights provided for custom allocation"
            ))
            return errors
        
        # Check weight values
        total_weight = sum(weights_dict.values())
        if abs(total_weight - 1.0) > 0.001:  # Allow small rounding errors
            errors.append(AllocationError(
                code="INVALID_WEIGHT_SUM",
                message=f"Weights must sum to 1.0, got {total_weight:.4f}",
                details={"total_weight": total_weight}
            ))
        
        # Check for negative weights
        for account_id, weight in weights_dict.items():
            if weight < 0:
                errors.append(AllocationError(
                    code="NEGATIVE_WEIGHT",
                    message=f"Negative weight {weight} for account {account_id}",
                    details={"account_id": account_id, "weight": weight}
                ))
            elif weight > 1:
                errors.append(AllocationError(
                    code="WEIGHT_EXCEEDS_ONE",
                    message=f"Weight {weight} exceeds 1.0 for account {account_id}",
                    details={"account_id": account_id, "weight": weight}
                ))
        
        return errors
    
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
            if target_quantity > 0:  # Only warn if weight was non-zero
                warnings.append(AllocationWarning(
                    type=AllocationWarningType.MIN_LOT_SIZE,
                    account_id=account.account_id,
                    message=f"Target allocation {allocated_quantity:.2f} below minimum {constraints.min_allocation}"
                ))
            return 0
        
        # Check cash constraint for buys
        if order.side == "BUY" and constraints.respect_cash:
            price = order.price or security.price
            cash_needed = allocated_quantity * price
            
            if cash_needed > account.available_cash:
                # Try to allocate what account can afford
                affordable_qty = account.available_cash / price
                new_quantity = self.round_to_denomination(
                    affordable_qty, security.min_denomination
                )
                
                if new_quantity < constraints.min_allocation:
                    warnings.append(AllocationWarning(
                        type=AllocationWarningType.INSUFFICIENT_CASH,
                        account_id=account.account_id,
                        message=f"Insufficient cash for minimum allocation. Available: ${account.available_cash:,.2f}"
                    ))
                    return 0
                
                allocated_quantity = new_quantity
        
        # Check position constraint for sells
        elif order.side == "SELL":
            if allocated_quantity > account.current_position:
                allocated_quantity = self.round_to_denomination(
                    account.current_position, security.min_denomination
                )
                
                if allocated_quantity < target_quantity:
                    warnings.append(AllocationWarning(
                        type=AllocationWarningType.COMPLIANCE,
                        account_id=account.account_id,
                        message=f"Reduced allocation due to position limit. Position: {account.current_position:.2f}"
                    ))
        
        return allocated_quantity
    
    def _handle_unallocated(
        self,
        unallocated: float,
        allocations: Dict[str, float],
        weights_dict: Dict[str, float],
        account_lookup: Dict[str, Account],
        security: Security,
        order: Order,
        constraints: AllocationConstraints,
        warnings: List[AllocationWarning]
    ) -> None:
        """Distribute unallocated quantity proportionally to accounts that got allocation"""
        if unallocated < security.min_denomination or not allocations:
            return
        
        # Calculate pro-rata distribution of unallocated based on successful allocations
        total_allocated = sum(allocations.values())
        
        for account_id, current_allocation in list(allocations.items()):
            if unallocated < security.min_denomination:
                break
            
            account = account_lookup[account_id]
            
            # Calculate additional allocation proportional to current allocation
            proportion = current_allocation / total_allocated if total_allocated > 0 else 0
            additional = unallocated * proportion
            additional_rounded = self.round_to_denomination(additional, security.min_denomination)
            
            if additional_rounded >= security.min_denomination:
                # Check if account can accept additional
                new_total = current_allocation + additional_rounded
                
                # Verify constraints still met
                if order.side == "BUY" and constraints.respect_cash:
                    price = order.price or security.price
                    if new_total * price <= account.available_cash:
                        allocations[account_id] = new_total
                        unallocated -= additional_rounded
                elif order.side == "SELL":
                    if new_total <= account.current_position:
                        allocations[account_id] = new_total
                        unallocated -= additional_rounded
    
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