"""Base allocation engine interface and data structures"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class AllocationMethod(Enum):
    """Supported allocation methods"""
    PRO_RATA = "PRO_RATA"
    CUSTOM_WEIGHTS = "CUSTOM_WEIGHTS"
    MIN_DISPERSION = "MIN_DISPERSION"


class AllocationWarningType(Enum):
    """Types of allocation warnings"""
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    MIN_LOT_SIZE = "MIN_LOT_SIZE"
    COMPLIANCE = "COMPLIANCE"
    ROUNDING = "ROUNDING"


@dataclass
class Account:
    """Account data for allocation"""
    account_id: str
    account_name: str
    nav: float
    available_cash: float
    current_position: float = 0.0
    active_spread_duration: float = 0.0
    portfolio_duration: float = 0.0
    spread_duration: float = 0.0
    oas: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Security:
    """Security data for allocation"""
    cusip: str
    ticker: Optional[str]
    description: str
    price: float
    duration: float
    spread_duration: float
    oas: float
    min_denomination: float
    coupon: float
    maturity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Order details for allocation"""
    security_id: str
    side: str  # BUY or SELL
    quantity: float
    settlement_date: datetime
    price: Optional[float] = None  # Override price if provided
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationConstraints:
    """Constraints for allocation"""
    respect_cash: bool = True
    min_allocation: float = 1000.0
    compliance_check: bool = True
    round_to_denomination: bool = True
    max_concentration: Optional[float] = None  # As percentage of portfolio
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeMetrics:
    """Pre/post trade metrics for an account"""
    active_spread_duration: float
    contribution_to_duration: float
    duration: float
    oas: float
    spread_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountAllocationResult:
    """Result of allocation for a single account"""
    account_id: str
    account_name: str
    allocated_quantity: float
    allocated_notional: float
    available_cash: float
    post_trade_cash: float
    pre_trade_metrics: TradeMetrics
    post_trade_metrics: TradeMetrics
    cash_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationWarning:
    """Warning generated during allocation"""
    type: AllocationWarningType
    account_id: Optional[str]
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationError:
    """Error during allocation"""
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispersionMetrics:
    """Dispersion metrics for allocation"""
    pre_trade_std_dev: float
    post_trade_std_dev: float
    improvement: float
    max_deviation: float
    min_deviation: float
    target_value: float
    within_tolerance: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationSummary:
    """Summary of allocation results"""
    total_allocated: float
    unallocated: float
    allocation_rate: float
    accounts_allocated: int
    accounts_skipped: int
    dispersion_metrics: Optional[DispersionMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationResult:
    """Complete allocation result"""
    allocation_id: str
    timestamp: datetime
    order: Order
    allocations: List[AccountAllocationResult]
    summary: AllocationSummary
    warnings: List[AllocationWarning] = field(default_factory=list)
    errors: List[AllocationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AllocationEngine(ABC):
    """Abstract base class for allocation engines"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"{__name__}.{name}")
    
    @abstractmethod
    async def allocate(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        parameters: Dict[str, Any],
        constraints: AllocationConstraints
    ) -> AllocationResult:
        """
        Perform allocation across accounts
        
        Args:
            order: Order details
            security: Security details
            accounts: List of accounts to allocate across
            parameters: Engine-specific parameters
            constraints: Allocation constraints
            
        Returns:
            AllocationResult with allocations and metrics
        """
        pass
    
    def validate_inputs(
        self,
        order: Order,
        security: Security,
        accounts: List[Account],
        constraints: AllocationConstraints
    ) -> List[AllocationError]:
        """
        Validate inputs before allocation
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not accounts:
            errors.append(AllocationError(
                code="NO_ACCOUNTS",
                message="No accounts provided for allocation"
            ))
        
        if order.quantity <= 0:
            errors.append(AllocationError(
                code="INVALID_QUANTITY",
                message=f"Invalid order quantity: {order.quantity}"
            ))
        
        if security.price <= 0:
            errors.append(AllocationError(
                code="INVALID_PRICE",
                message=f"Invalid security price: {security.price}"
            ))
        
        if constraints.min_allocation < security.min_denomination:
            errors.append(AllocationError(
                code="INVALID_MIN_ALLOCATION",
                message=f"Minimum allocation {constraints.min_allocation} is less than security minimum denomination {security.min_denomination}"
            ))
        
        return errors
    
    def round_to_denomination(self, quantity: float, min_denomination: float) -> float:
        """Round quantity to minimum denomination"""
        import numpy as np
        return np.floor(quantity / min_denomination) * min_denomination
    
    def calculate_pre_trade_metrics(
        self,
        account: Account,
        security: Security
    ) -> TradeMetrics:
        """Calculate pre-trade metrics for an account"""
        return TradeMetrics(
            active_spread_duration=account.active_spread_duration,
            contribution_to_duration=account.portfolio_duration * (account.nav / 1000000),  # Simplified
            duration=account.portfolio_duration,
            oas=account.oas,
            spread_duration=account.spread_duration
        )
    
    def calculate_post_trade_metrics(
        self,
        account: Account,
        security: Security,
        allocated_quantity: float,
        side: str
    ) -> TradeMetrics:
        """Calculate post-trade metrics for an account"""
        # This is a simplified calculation - in production would be more complex
        position_change = allocated_quantity if side == "BUY" else -allocated_quantity
        new_position = account.current_position + position_change
        
        # Simple weighted average calculation
        if new_position > 0:
            old_weight = account.current_position / (account.current_position + position_change) if account.current_position > 0 else 0
            new_weight = position_change / (account.current_position + position_change)
            
            new_spread_duration = (
                account.spread_duration * old_weight +
                security.spread_duration * new_weight
            )
        else:
            new_spread_duration = account.spread_duration
        
        # Calculate new ASD contribution (simplified)
        position_value = new_position * security.price
        new_asd = (position_value / account.nav) * new_spread_duration if account.nav > 0 else 0
        
        return TradeMetrics(
            active_spread_duration=new_asd,
            contribution_to_duration=account.portfolio_duration * (account.nav / 1000000),
            duration=account.portfolio_duration,  # Simplified - would recalculate in production
            oas=security.oas,  # Simplified
            spread_duration=new_spread_duration
        )
    
    def create_allocation_warnings(
        self,
        accounts: List[Account],
        allocations: Dict[str, float],
        security: Security,
        constraints: AllocationConstraints
    ) -> List[AllocationWarning]:
        """Generate warnings for allocation results"""
        warnings = []
        
        for account in accounts:
            allocated = allocations.get(account.account_id, 0)
            
            # Check cash constraint
            if account.account_id not in allocations and constraints.respect_cash:
                cash_needed = constraints.min_allocation * security.price
                if account.available_cash < cash_needed:
                    warnings.append(AllocationWarning(
                        type=AllocationWarningType.INSUFFICIENT_CASH,
                        account_id=account.account_id,
                        message=f"Account {account.account_name} has insufficient cash. Available: ${account.available_cash:,.2f}, Needed: ${cash_needed:,.2f}"
                    ))
            
            # Check minimum lot size
            if 0 < allocated < constraints.min_allocation:
                warnings.append(AllocationWarning(
                    type=AllocationWarningType.MIN_LOT_SIZE,
                    account_id=account.account_id,
                    message=f"Account {account.account_name} allocation ${allocated:,.2f} is below minimum ${constraints.min_allocation:,.2f}"
                ))
        
        return warnings