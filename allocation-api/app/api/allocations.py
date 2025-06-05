"""Allocations API endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import uuid
from typing import Dict, List

from app.services.allocation_engines.factory import AllocationEngineFactory
from app.services.aladdin_client import get_aladdin_client
from app.services.database_service import AllocationService
from app.services.audit_service import AuditService
from app.services.mock_data.portfolio_groups import get_portfolio_group_accounts
from app.services.mock_data.accounts import get_account_cash_balance
from app.services.mock_data.positions import get_account_positions
from app.services.mock_data.securities import get_mock_security
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.utils.async_helpers import run_async

logger = get_logger(__name__)

ns = Namespace("allocations", description="Order allocation operations")

# Request/Response Models
order_details_model = ns.model("OrderDetails", {
    "security_id": fields.String(required=True, description="Security identifier (CUSIP)"),
    "side": fields.String(required=True, enum=["BUY", "SELL"], description="Order side"),
    "quantity": fields.Float(required=True, description="Order quantity"),
    "settlement_date": fields.Date(description="Settlement date"),
    "price": fields.Float(description="Optional override price")
})

pro_rata_params = ns.model("ProRataParameters", {
    "base_metric": fields.String(enum=["NAV", "MARKET_VALUE", "CUSTOM"], default="NAV")
})

custom_weights_params = ns.model("CustomWeightsParameters", {
    "weights": fields.Raw(required=True, description="Account weights as {account_id: weight}")
})

min_dispersion_params = ns.model("MinDispersionParameters", {
    "target_metric": fields.String(
        enum=["ACTIVE_SPREAD_DURATION", "DURATION", "OAS"], 
        default="ACTIVE_SPREAD_DURATION"
    ),
    "tolerance": fields.Float(default=0.05, min=0, max=1),
    "max_iterations": fields.Integer(default=1000)
})

allocation_constraints = ns.model("AllocationConstraints", {
    "respect_cash": fields.Boolean(default=True),
    "min_allocation": fields.Float(default=1000),
    "compliance_check": fields.Boolean(default=True),
    "round_to_denomination": fields.Boolean(default=True)
})

allocation_request = ns.model("AllocationRequest", {
    "order": fields.Nested(order_details_model, required=True),
    "allocation_method": fields.String(
        required=True,
        enum=["PRO_RATA", "CUSTOM_WEIGHTS", "MIN_DISPERSION"]
    ),
    "portfolio_groups": fields.List(fields.String, required=True),
    "parameters": fields.Raw(description="Method-specific parameters"),
    "constraints": fields.Nested(allocation_constraints)
})

trade_metrics_model = ns.model("TradeMetrics", {
    "active_spread_duration": fields.Float(),
    "contribution_to_duration": fields.Float(),
    "duration": fields.Float(),
    "oas": fields.Float()
})

account_allocation_model = ns.model("AccountAllocation", {
    "account_id": fields.String(),
    "account_name": fields.String(),
    "allocated_quantity": fields.Float(),
    "allocated_notional": fields.Float(),
    "available_cash": fields.Float(),
    "post_trade_cash": fields.Float(),
    "pre_trade_metrics": fields.Nested(trade_metrics_model),
    "post_trade_metrics": fields.Nested(trade_metrics_model)
})

allocation_warning_model = ns.model("AllocationWarning", {
    "type": fields.String(enum=["INSUFFICIENT_CASH", "MIN_LOT_SIZE", "COMPLIANCE", "ROUNDING"]),
    "account_id": fields.String(),
    "message": fields.String()
})

allocation_error_model = ns.model("AllocationError", {
    "code": fields.String(),
    "message": fields.String(),
    "details": fields.Raw()
})

dispersion_metrics_model = ns.model("DispersionMetrics", {
    "pre_trade_std_dev": fields.Float(),
    "post_trade_std_dev": fields.Float(),
    "improvement": fields.Float(),
    "max_deviation": fields.Float(),
    "min_deviation": fields.Float()
})

allocation_summary_model = ns.model("AllocationSummary", {
    "total_allocated": fields.Float(),
    "unallocated": fields.Float(),
    "allocation_rate": fields.Float(),
    "accounts_allocated": fields.Integer(),
    "accounts_skipped": fields.Integer(),
    "dispersion_metrics": fields.Nested(dispersion_metrics_model)
})

order_summary_model = ns.model("OrderSummary", {
    "security_id": fields.String(),
    "side": fields.String(),
    "total_quantity": fields.Float(),
    "settlement_date": fields.Date()
})

allocation_preview_response = ns.model("AllocationPreviewResponse", {
    "allocation_id": fields.String(),
    "timestamp": fields.DateTime(),
    "order": fields.Nested(order_summary_model),
    "allocations": fields.List(fields.Nested(account_allocation_model)),
    "summary": fields.Nested(allocation_summary_model),
    "warnings": fields.List(fields.Nested(allocation_warning_model)),
    "errors": fields.List(fields.Nested(allocation_error_model))
})


@ns.route("/preview")
class AllocationPreview(Resource):
    @ns.doc("preview_allocation")
    @ns.expect(allocation_request)
    @ns.marshal_with(allocation_preview_response)
    @ns.response(200, "Allocation preview calculated")
    @ns.response(400, "Bad request")
    @ns.response(401, "Unauthorized")
    @ns.response(500, "Internal server error")
    @jwt_required()
    def post(self):
        """Calculate allocation preview"""
        try:
            data = request.get_json()
            user_id = get_jwt_identity()
            
            logger.info(f"Allocation preview requested by {user_id}")
            logger.info(f"Order: {data['order']}")
            logger.info(f"Method: {data['allocation_method']}")
            logger.info(f"Portfolio Groups: {data['portfolio_groups']}")
            
            # Validate request
            if not data.get("order"):
                ns.abort(400, "Order details are required")
            if not data.get("allocation_method"):
                ns.abort(400, "Allocation method is required")
            if not data.get("portfolio_groups"):
                ns.abort(400, "Portfolio groups are required")
            
            # Extract order details
            order = data["order"]
            security_id = order["security_id"]
            side = order["side"]
            quantity = order["quantity"]
            
            # Get allocation parameters
            method = data["allocation_method"]
            portfolio_groups = data["portfolio_groups"]
            parameters = data.get("parameters", {})
            constraints = data.get("constraints", {})
            
            # Get security information
            security = get_mock_security(security_id)
            if not security:
                ns.abort(404, f"Security {security_id} not found")
            
            security_price = security.get("price", 1.0)
            logger.info(f"Security {security_id} price: {security_price}")
            
            # Create allocation engine
            engine = AllocationEngineFactory.create(
                method=method,
                parameters=parameters
            )
            
            # Gather account data for all portfolio groups
            all_accounts = []
            for group_id in portfolio_groups:
                accounts = get_portfolio_group_accounts(group_id)
                all_accounts.extend(accounts)
            
            if not all_accounts:
                ns.abort(404, f"No accounts found for portfolio groups: {portfolio_groups}")
            
            logger.info(f"Found {len(all_accounts)} accounts across {len(portfolio_groups)} groups")
            
            # Get current positions and cash for accounts
            account_data = []
            for account in all_accounts:
                account_id = account["account_id"]
                
                # Get cash balance
                cash_balance = get_account_cash_balance(account_id)
                
                # Get positions
                positions = get_account_positions(account_id)
                
                # Find current position in this security (if any)
                current_position = 0
                for pos in positions:
                    if pos.get("cusip") == security_id:
                        current_position = pos.get("quantity", 0)
                        break
                
                account_data.append({
                    "account_id": account_id,
                    "account_name": account["account_name"],
                    "nav": account.get("nav", 0),
                    "available_cash": cash_balance,
                    "current_position": current_position,
                    "positions": positions
                })
            
            # Calculate allocations
            allocation_results = engine.allocate(
                order_quantity=quantity,
                accounts=account_data,
                constraints=constraints,
                security_price=security_price
            )
            
            # Generate allocation ID
            allocation_id = str(uuid.uuid4())
            
            # Calculate summary statistics
            total_allocated = sum(a["allocated_quantity"] for a in allocation_results)
            unallocated = quantity - total_allocated
            allocation_rate = total_allocated / quantity if quantity > 0 else 0
            accounts_allocated = sum(1 for a in allocation_results if a["allocated_quantity"] > 0)
            accounts_skipped = len(all_accounts) - accounts_allocated
            
            # Build response
            response = {
                "allocation_id": allocation_id,
                "timestamp": datetime.utcnow(),
                "order": {
                    "security_id": security_id,
                    "side": side,
                    "total_quantity": quantity,
                    "settlement_date": order.get("settlement_date")
                },
                "allocations": allocation_results,
                "summary": {
                    "total_allocated": total_allocated,
                    "unallocated": unallocated,
                    "allocation_rate": allocation_rate,
                    "accounts_allocated": accounts_allocated,
                    "accounts_skipped": accounts_skipped,
                    "dispersion_metrics": engine.get_dispersion_metrics() if hasattr(engine, 'get_dispersion_metrics') else None
                },
                "warnings": [],
                "errors": []
            }
            
            # Add warnings for accounts that were skipped
            for account in account_data:
                allocation = next((a for a in allocation_results if a["account_id"] == account["account_id"]), None)
                if not allocation or allocation["allocated_quantity"] == 0:
                    if account["available_cash"] < constraints.get("min_allocation", 1000):
                        response["warnings"].append({
                            "type": "INSUFFICIENT_CASH",
                            "account_id": account["account_id"],
                            "message": f"Account has insufficient cash: ${account['available_cash']:,.2f}"
                        })
            
            # Store allocation preview in database with Snowflake
            db = SessionLocal()
            try:
                db_allocation = AllocationService.create_allocation(
                    db=db,
                    order_data={
                        "order_id": None,  # No order ID for preview
                        "security_id": security_id,
                        "quantity": quantity
                    },
                    allocation_method=method,
                    portfolio_group_id=",".join(portfolio_groups),
                    parameters=parameters,
                    constraints=constraints,
                    created_by=user_id
                )
                
                # Add allocation details
                AllocationService.add_allocation_details(
                    db=db,
                    allocation_id=db_allocation.allocation_id,
                    allocation_results=allocation_results
                )
                
                # Update with summary metrics
                AllocationService.update_allocation_summary(
                    db=db,
                    allocation_id=db_allocation.allocation_id,
                    allocated_amount=total_allocated,
                    allocation_rate=allocation_rate,
                    pre_trade_metrics={},
                    post_trade_metrics={}
                )
                
                # Log action
                AuditService.log_action(
                    db=db,
                    user_id=user_id,
                    username=user_id,
                    action="PREVIEW_ALLOCATION",
                    entity_type="allocation",
                    entity_id=allocation_id,
                    changes={
                        "method": method,
                        "quantity": quantity,
                        "security_id": security_id,
                        "portfolio_groups": portfolio_groups
                    }
                )
            finally:
                db.close()
            
            logger.info(f"Allocation preview {allocation_id} completed successfully")
            return response
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            ns.abort(400, str(e))
        except Exception as e:
            logger.error(f"Allocation preview failed: {e}", exc_info=True)
            ns.abort(500, f"Failed to calculate allocation: {str(e)}")


@ns.route("/<string:allocation_id>/commit")
class AllocationCommit(Resource):
    @ns.doc("commit_allocation")
    @ns.expect(ns.model("CommitAllocationRequest", {
        "comment": fields.String(description="Optional comment"),
        "override_warnings": fields.Boolean(default=False)
    }))
    @ns.response(200, "Allocation committed")
    @ns.response(400, "Bad request")
    @ns.response(401, "Unauthorized")
    @ns.response(404, "Allocation not found")
    @ns.response(500, "Internal server error")
    @jwt_required()
    def post(self, allocation_id):
        """Commit allocation to Aladdin"""
        try:
            data = request.get_json() or {}
            user_id = get_jwt_identity()
            
            logger.info(f"Committing allocation {allocation_id} by {user_id}")
            
            # Get allocation from Snowflake database
            db = SessionLocal()
            try:
                allocation_data = AllocationService.get_allocation_with_details(db, allocation_id)
                if not allocation_data:
                    ns.abort(404, f"Allocation {allocation_id} not found")
                
                # Check if already committed
                if allocation_data["status"] == "COMMITTED":
                    ns.abort(400, "Allocation has already been committed")
                
                # Since we don't have real Aladdin, generate simulated order IDs
                # In production, this would call Aladdin's order submission API
                logger.info("Simulating Aladdin order submission (no real Aladdin connection)")
                aladdin_order_ids = []
                allocation_results = []
                
                for detail in allocation_data["details"]:
                    mock_order_id = f"ALAD-{uuid.uuid4().hex[:8].upper()}"
                    aladdin_order_ids.append({
                        "account_id": detail["account_id"],
                        "order_id": mock_order_id
                    })
                    
                    allocation_results.append({
                        "account_id": detail["account_id"],
                        "aladdin_order_id": mock_order_id,
                        "status": "SUBMITTED",
                        "message": "Order submitted successfully (simulated)"
                    })
                
                # Update allocation status in Snowflake
                AllocationService.commit_allocation(
                    db=db,
                    allocation_id=allocation_id,
                    aladdin_order_ids=aladdin_order_ids
                )
                
                # Log action in Snowflake
                audit_log = AuditService.log_action(
                    db=db,
                    user_id=user_id,
                    username=user_id,
                    action="COMMIT_ALLOCATION",
                    entity_type="allocation",
                    entity_id=allocation_id,
                    changes={
                        "comment": data.get("comment"),
                        "override_warnings": data.get("override_warnings", False),
                        "aladdin_order_ids": [o["order_id"] for o in aladdin_order_ids]
                    }
                )
                
                response = {
                    "status": "SUCCESS",
                    "aladdin_order_ids": [o["order_id"] for o in aladdin_order_ids],
                    "allocations": allocation_results,
                    "audit_id": audit_log.audit_id
                }
                
                logger.info(f"Allocation {allocation_id} committed successfully")
                return response
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to commit allocation {allocation_id}: {e}", exc_info=True)
            ns.abort(500, f"Failed to commit allocation: {str(e)}")