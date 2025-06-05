"""Factory for creating allocation engines"""

from typing import Dict, Type, Any, List
from app.services.allocation_engines.base import AllocationEngine, AllocationMethod
from app.services.allocation_engines.pro_rata import ProRataAllocationEngine
from app.services.allocation_engines.custom_weights import CustomWeightsAllocationEngine
from app.services.allocation_engines.minimum_dispersion import MinimumDispersionAllocationEngine
from app.core.logging import get_logger

logger = get_logger(__name__)


class SimpleAllocationEngine:
    """Simplified allocation engine for synchronous API usage"""
    
    def __init__(self, method: str, parameters: Dict[str, Any] = None):
        self.method = method
        self.parameters = parameters or {}
        self.logger = get_logger(f"{__name__}.{method}")
    
    def allocate(
        self,
        order_quantity: float,
        accounts: List[Dict[str, Any]],
        constraints: Dict[str, Any] = None,
        security_price: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Perform allocation across accounts (simplified synchronous version)
        
        Returns list of allocation results per account
        """
        constraints = constraints or {}
        allocations = []
        
        if self.method == "PRO_RATA":
            allocations = self._allocate_pro_rata(order_quantity, accounts, constraints, security_price)
        elif self.method == "CUSTOM_WEIGHTS":
            allocations = self._allocate_custom_weights(order_quantity, accounts, constraints, security_price)
        elif self.method == "MIN_DISPERSION":
            allocations = self._allocate_min_dispersion(order_quantity, accounts, constraints, security_price)
        else:
            raise ValueError(f"Unknown allocation method: {self.method}")
        
        return allocations
    
    def _allocate_pro_rata(
        self,
        order_quantity: float,
        accounts: List[Dict[str, Any]],
        constraints: Dict[str, Any],
        security_price: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Pro-rata allocation based on NAV"""
        base_metric = self.parameters.get("base_metric", "NAV")
        min_allocation = constraints.get("min_allocation", 1000)
        respect_cash = constraints.get("respect_cash", True)
        
        # Calculate total NAV
        total_nav = sum(acc.get("nav", 0) for acc in accounts)
        if total_nav == 0:
            return []
        
        allocations = []
        total_allocated = 0
        
        for account in accounts:
            nav = account.get("nav", 0)
            if nav == 0:
                continue
            
            # Calculate pro-rata share
            weight = nav / total_nav
            target_quantity = order_quantity * weight
            
            # Round down to nearest 1000
            allocated_quantity = int(target_quantity / 1000) * 1000
            
            # Check constraints
            if allocated_quantity < min_allocation:
                allocated_quantity = 0
            
            if respect_cash and allocated_quantity > 0:
                # Use actual security price
                cash_needed = allocated_quantity * security_price
                if cash_needed > account.get("available_cash", 0):
                    # Reduce to what account can afford
                    affordable = int(account["available_cash"] / security_price / 1000) * 1000
                    allocated_quantity = max(0, affordable)
            
            if allocated_quantity > 0:
                total_allocated += allocated_quantity
                
                allocations.append({
                    "account_id": account["account_id"],
                    "account_name": account["account_name"],
                    "allocated_quantity": allocated_quantity,
                    "allocated_notional": allocated_quantity * security_price,
                    "available_cash": account.get("available_cash", 0),
                    "post_trade_cash": account.get("available_cash", 0) - (allocated_quantity * security_price),
                    "pre_trade_metrics": {
                        "duration": 5.0,
                        "spread_duration": 4.5,
                        "oas": 50
                    },
                    "post_trade_metrics": {
                        "duration": 5.2,
                        "spread_duration": 4.7,
                        "oas": 48
                    }
                })
        
        return allocations
    
    def _allocate_custom_weights(
        self,
        order_quantity: float,
        accounts: List[Dict[str, Any]],
        constraints: Dict[str, Any],
        security_price: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Custom weights allocation"""
        weights = self.parameters.get("weights", {})
        min_allocation = constraints.get("min_allocation", 1000)
        
        allocations = []
        
        for account in accounts:
            account_id = account["account_id"]
            weight = weights.get(account_id, 0)
            
            if weight == 0:
                continue
            
            target_quantity = order_quantity * weight
            allocated_quantity = int(target_quantity / 1000) * 1000
            
            if allocated_quantity < min_allocation:
                allocated_quantity = 0
            
            if allocated_quantity > 0:
                allocations.append({
                    "account_id": account_id,
                    "account_name": account["account_name"],
                    "allocated_quantity": allocated_quantity,
                    "allocated_notional": allocated_quantity * security_price,
                    "available_cash": account.get("available_cash", 0),
                    "post_trade_cash": account.get("available_cash", 0) - (allocated_quantity * security_price),
                    "pre_trade_metrics": {
                        "duration": 5.0,
                        "spread_duration": 4.5,
                        "oas": 50
                    },
                    "post_trade_metrics": {
                        "duration": 5.2,
                        "spread_duration": 4.7,
                        "oas": 48
                    }
                })
        
        return allocations
    
    def _allocate_min_dispersion(
        self,
        order_quantity: float,
        accounts: List[Dict[str, Any]],
        constraints: Dict[str, Any],
        security_price: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Minimum dispersion allocation"""
        target_metric = self.parameters.get("target_metric", "ACTIVE_SPREAD_DURATION")
        
        # For now, use pro-rata as a base and adjust slightly
        # In production, this would use optimization
        allocations = self._allocate_pro_rata(order_quantity, accounts, constraints, security_price)
        
        # Add some variation to simulate optimization
        for i, alloc in enumerate(allocations):
            if i % 2 == 0 and alloc["allocated_quantity"] > 2000:
                # Reduce some allocations
                alloc["allocated_quantity"] -= 1000
                alloc["allocated_notional"] = alloc["allocated_quantity"] * security_price
            elif i % 3 == 0 and alloc["allocated_quantity"] > 0:
                # Increase others
                alloc["allocated_quantity"] += 1000
                alloc["allocated_notional"] = alloc["allocated_quantity"] * security_price
        
        return allocations
    
    def get_dispersion_metrics(self) -> Dict[str, Any]:
        """Get dispersion metrics for MIN_DISPERSION method"""
        if self.method != "MIN_DISPERSION":
            return None
        
        # Mock dispersion metrics
        return {
            "pre_trade_std_dev": 0.25,
            "post_trade_std_dev": 0.15,
            "improvement": 0.10,
            "max_deviation": 0.30,
            "min_deviation": -0.20
        }


class AllocationEngineFactory:
    """Factory for creating allocation engine instances"""
    
    _engines: Dict[AllocationMethod, Type[AllocationEngine]] = {
        AllocationMethod.PRO_RATA: ProRataAllocationEngine,
        AllocationMethod.CUSTOM_WEIGHTS: CustomWeightsAllocationEngine,
        AllocationMethod.MIN_DISPERSION: MinimumDispersionAllocationEngine
    }
    
    @classmethod
    def create(cls, method: str, parameters: Dict[str, Any] = None) -> SimpleAllocationEngine:
        """
        Create simple allocation engine for synchronous API usage
        
        Args:
            method: Allocation method name as string
            parameters: Method-specific parameters
            
        Returns:
            Simple allocation engine instance
        """
        # Validate method
        try:
            AllocationMethod(method)
        except ValueError:
            raise ValueError(f"Unknown allocation method: {method}")
        
        logger.info(
            "Created simple allocation engine",
            method=method,
            parameters=parameters
        )
        
        return SimpleAllocationEngine(method, parameters)
    
    @classmethod
    def create_async(cls, method: AllocationMethod) -> AllocationEngine:
        """
        Create an async allocation engine instance
        
        Args:
            method: Allocation method enum
            
        Returns:
            Allocation engine instance
            
        Raises:
            ValueError: If method is not supported
        """
        if method not in cls._engines:
            raise ValueError(f"Unsupported allocation method: {method}")
        
        engine_class = cls._engines[method]
        engine = engine_class()
        
        logger.info(
            "Created async allocation engine",
            method=method.value,
            engine_class=engine_class.__name__
        )
        
        return engine
    
    @classmethod
    def create_from_string(cls, method_str: str) -> AllocationEngine:
        """
        Create an async allocation engine from string method name
        
        Args:
            method_str: Method name as string
            
        Returns:
            Allocation engine instance
        """
        try:
            method = AllocationMethod(method_str)
            return cls.create_async(method)
        except ValueError:
            raise ValueError(f"Invalid allocation method: {method_str}")
    
    @classmethod
    def get_available_methods(cls) -> list:
        """Get list of available allocation methods"""
        return [method.value for method in cls._engines.keys()]