"""Database service for allocation operations"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Allocation, AllocationDetail
from app.core.logging import get_logger

logger = get_logger(__name__)


class AllocationService:
    """Service for allocation database operations"""
    
    @staticmethod
    def create_allocation(
        db: Session,
        order_data: Dict,
        allocation_method: str,
        portfolio_group_id: str,
        parameters: Dict,
        constraints: Dict,
        created_by: str
    ) -> Allocation:
        """Create a new allocation record"""
        allocation_id = str(uuid.uuid4())
        
        # Use raw SQL with PARSE_JSON for VARIANT columns
        stmt = text("""
            INSERT INTO allocations (
                allocation_id, order_id, portfolio_group_id, security_id,
                allocation_method, total_amount, allocated_amount, allocation_rate,
                created_by, status, parameters, constraints, created_at
            )
            SELECT :allocation_id, :order_id, :portfolio_group_id, :security_id,
                :allocation_method, :total_amount, :allocated_amount, :allocation_rate,
                :created_by, :status, PARSE_JSON(:parameters), PARSE_JSON(:constraints),
                CURRENT_TIMESTAMP()
        """)
        
        db.execute(stmt, {
            "allocation_id": allocation_id,
            "order_id": order_data.get("order_id"),
            "portfolio_group_id": portfolio_group_id,
            "security_id": order_data["security_id"],
            "allocation_method": allocation_method,
            "total_amount": order_data["quantity"],
            "allocated_amount": 0,
            "allocation_rate": 0,
            "created_by": created_by,
            "status": "PREVIEW",
            "parameters": json.dumps(parameters) if parameters else None,
            "constraints": json.dumps(constraints) if constraints else None
        })
        
        db.commit()
        
        # Fetch the created allocation
        allocation = db.query(Allocation).filter_by(allocation_id=allocation_id).first()
        
        logger.info(f"Created allocation {allocation_id} for {portfolio_group_id}")
        return allocation
    
    @staticmethod
    def add_allocation_details(
        db: Session,
        allocation_id: str,
        allocation_results: List[Dict]
    ) -> List[AllocationDetail]:
        """Add allocation details for each account"""
        details = []
        
        for result in allocation_results:
            detail_id = str(uuid.uuid4())
            
            # Use raw SQL with PARSE_JSON for VARIANT columns
            stmt = text("""
                INSERT INTO allocation_details (
                    allocation_detail_id, allocation_id, account_id, account_name,
                    allocated_quantity, allocated_notional, pre_trade_cash, post_trade_cash,
                    pre_trade_metrics, post_trade_metrics, warnings, created_at
                )
                SELECT :allocation_detail_id, :allocation_id, :account_id, :account_name,
                    :allocated_quantity, :allocated_notional, :pre_trade_cash, :post_trade_cash,
                    PARSE_JSON(:pre_trade_metrics), PARSE_JSON(:post_trade_metrics), 
                    PARSE_JSON(:warnings), CURRENT_TIMESTAMP()
            """)
            
            db.execute(stmt, {
                "allocation_detail_id": detail_id,
                "allocation_id": allocation_id,
                "account_id": result["account_id"],
                "account_name": result.get("account_name"),
                "allocated_quantity": result["allocated_quantity"],
                "allocated_notional": result.get("allocated_notional", 0),
                "pre_trade_cash": result.get("pre_trade_cash"),
                "post_trade_cash": result.get("post_trade_cash"),
                "pre_trade_metrics": json.dumps(result.get("pre_trade_metrics")) if result.get("pre_trade_metrics") else None,
                "post_trade_metrics": json.dumps(result.get("post_trade_metrics")) if result.get("post_trade_metrics") else None,
                "warnings": json.dumps(result.get("warnings", [])) if result.get("warnings") else None
            })
            
            # Fetch the created detail
            detail = db.query(AllocationDetail).filter_by(allocation_detail_id=detail_id).first()
            details.append(detail)
        
        db.commit()
        logger.info(f"Added {len(details)} allocation details for allocation {allocation_id}")
        return details
    
    @staticmethod
    def update_allocation_summary(
        db: Session,
        allocation_id: str,
        allocated_amount: float,
        allocation_rate: float,
        pre_trade_metrics: Dict,
        post_trade_metrics: Dict
    ) -> Allocation:
        """Update allocation with summary metrics"""
        # Use raw SQL with PARSE_JSON for VARIANT columns
        stmt = text("""
            UPDATE allocations
            SET allocated_amount = :allocated_amount,
                allocation_rate = :allocation_rate,
                pre_trade_metrics = PARSE_JSON(:pre_trade_metrics),
                post_trade_metrics = PARSE_JSON(:post_trade_metrics)
            WHERE allocation_id = :allocation_id
        """)
        
        db.execute(stmt, {
            "allocation_id": allocation_id,
            "allocated_amount": allocated_amount,
            "allocation_rate": allocation_rate,
            "pre_trade_metrics": json.dumps(pre_trade_metrics) if pre_trade_metrics else None,
            "post_trade_metrics": json.dumps(post_trade_metrics) if post_trade_metrics else None
        })
        
        db.commit()
        
        # Fetch the updated allocation
        allocation = db.query(Allocation).filter_by(allocation_id=allocation_id).first()
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
        
        logger.info(f"Updated allocation {allocation_id} with summary metrics")
        return allocation
    
    @staticmethod
    def get_allocation(db: Session, allocation_id: str) -> Optional[Allocation]:
        """Get allocation by ID"""
        return db.query(Allocation).filter_by(allocation_id=allocation_id).first()
    
    @staticmethod
    def get_allocation_with_details(db: Session, allocation_id: str) -> Optional[Dict]:
        """Get allocation with all details"""
        allocation = db.query(Allocation).filter_by(allocation_id=allocation_id).first()
        if not allocation:
            return None
        
        result = allocation.to_dict()
        result["details"] = [detail.to_dict() for detail in allocation.details]
        return result
    
    @staticmethod
    def commit_allocation(
        db: Session,
        allocation_id: str,
        aladdin_order_ids: List[Dict]
    ) -> Allocation:
        """Mark allocation as committed"""
        allocation = db.query(Allocation).filter_by(allocation_id=allocation_id).first()
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
        
        allocation.status = "COMMITTED"
        
        # Store Aladdin order IDs in each detail
        for detail in allocation.details:
            for order_info in aladdin_order_ids:
                if order_info["account_id"] == detail.account_id:
                    if not detail.post_trade_metrics:
                        detail.post_trade_metrics = {}
                    detail.post_trade_metrics["aladdin_order_id"] = order_info["order_id"]
        
        db.commit()
        db.refresh(allocation)
        
        logger.info(f"Committed allocation {allocation_id}")
        return allocation
    
    @staticmethod
    def get_recent_allocations(
        db: Session,
        portfolio_group_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent allocations"""
        query = db.query(Allocation)
        
        if portfolio_group_id:
            query = query.filter_by(portfolio_group_id=portfolio_group_id)
        
        allocations = query.order_by(Allocation.created_at.desc()).limit(limit).all()
        
        return [allocation.to_dict() for allocation in allocations]