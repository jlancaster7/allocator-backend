"""Allocation related database models"""

from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from snowflake.sqlalchemy import VARIANT
import json
import enum
from .base import Base, TimestampMixin


class AllocationStatus(enum.Enum):
    """Allocation status enum"""
    PREVIEW = "PREVIEW"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AllocationMethod(enum.Enum):
    """Allocation method enum"""
    PRO_RATA = "PRO_RATA"
    CUSTOM_WEIGHTS = "CUSTOM_WEIGHTS"
    MIN_DISPERSION = "MIN_DISPERSION"


class Allocation(Base, TimestampMixin):
    """Main allocation record"""
    __tablename__ = "allocations"
    
    allocation_id = Column(String(100), primary_key=True)
    order_id = Column(String(100))
    portfolio_group_id = Column(String(50), nullable=False)
    security_id = Column(String(20), nullable=False)
    allocation_method = Column(String(50), nullable=False)
    total_amount = Column(Numeric(20, 2), nullable=False)
    allocated_amount = Column(Numeric(20, 2), nullable=False)
    allocation_rate = Column(Numeric(5, 4))
    created_by = Column(String(100), nullable=False)
    status = Column(String(20), default="PREVIEW")
    pre_trade_metrics = Column(VARIANT)
    post_trade_metrics = Column(VARIANT)
    parameters = Column(VARIANT)
    constraints = Column(VARIANT)
    
    # Relationships
    details = relationship("AllocationDetail", back_populates="allocation", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "allocation_id": self.allocation_id,
            "order_id": self.order_id,
            "portfolio_group_id": self.portfolio_group_id,
            "security_id": self.security_id,
            "allocation_method": self.allocation_method,
            "total_amount": float(self.total_amount) if self.total_amount else 0,
            "allocated_amount": float(self.allocated_amount) if self.allocated_amount else 0,
            "allocation_rate": float(self.allocation_rate) if self.allocation_rate else 0,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "pre_trade_metrics": self.pre_trade_metrics,
            "post_trade_metrics": self.post_trade_metrics,
            "parameters": self.parameters,
            "constraints": self.constraints
        }


class AllocationDetail(Base, TimestampMixin):
    """Allocation details per account"""
    __tablename__ = "allocation_details"
    
    allocation_detail_id = Column(String(100), primary_key=True)
    allocation_id = Column(String(100), ForeignKey("allocations.allocation_id"), nullable=False)
    account_id = Column(String(50), nullable=False)
    account_name = Column(String(200))
    allocated_quantity = Column(Numeric(20, 2), nullable=False)
    allocated_notional = Column(Numeric(20, 2), nullable=False)
    pre_trade_cash = Column(Numeric(20, 2))
    post_trade_cash = Column(Numeric(20, 2))
    pre_trade_metrics = Column(VARIANT)
    post_trade_metrics = Column(VARIANT)
    warnings = Column(VARIANT)
    
    # Relationships
    allocation = relationship("Allocation", back_populates="details")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "allocation_detail_id": self.allocation_detail_id,
            "allocation_id": self.allocation_id,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "allocated_quantity": float(self.allocated_quantity) if self.allocated_quantity else 0,
            "allocated_notional": float(self.allocated_notional) if self.allocated_notional else 0,
            "pre_trade_cash": float(self.pre_trade_cash) if self.pre_trade_cash else 0,
            "post_trade_cash": float(self.post_trade_cash) if self.post_trade_cash else 0,
            "pre_trade_metrics": self.pre_trade_metrics,
            "post_trade_metrics": self.post_trade_metrics,
            "warnings": self.warnings,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }