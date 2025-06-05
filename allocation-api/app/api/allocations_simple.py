"""Simple Allocations API endpoints without database writes"""

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import uuid
from typing import Dict, List

from app.services.allocation_engines.factory import AllocationEngineFactory
from app.services.mock_data.portfolio_groups import get_portfolio_group_accounts
from app.services.mock_data.accounts import get_account_cash_balance
from app.services.mock_data.positions import get_account_positions
from app.services.mock_data.securities import get_mock_security
from app.core.logging import get_logger

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
            
            # Extract request data
            order = data.get("order", {})
            security_id = order.get("security_id")
            side = order.get("side")
            quantity = order.get("quantity")
            settlement_date = order.get("settlement_date")
            
            method = data.get("allocation_method")
            portfolio_groups = data.get("portfolio_groups", [])
            parameters = data.get("parameters", {})
            constraints = data.get("constraints", {})
            
            # Validate inputs
            if not all([security_id, side, quantity, method, portfolio_groups]):
                raise ValueError("Missing required fields")
            
            if side not in ["BUY", "SELL"]:
                raise ValueError("Side must be BUY or SELL")
            
            if method not in ["PRO_RATA", "CUSTOM_WEIGHTS", "MIN_DISPERSION"]:
                raise ValueError("Invalid allocation method")
            
            # Generate allocation ID
            allocation_id = str(uuid.uuid4())
            
            # Get account data for selected portfolio groups
            account_data = []
            for group_id in portfolio_groups:
                accounts = get_portfolio_group_accounts(group_id)
                for account in accounts:
                    # Add cash balance
                    account["available_cash"] = get_account_cash_balance(account["account_id"])
                    # Add positions for min dispersion
                    if method == "MIN_DISPERSION":
                        account["positions"] = get_account_positions(account["account_id"])
                    account_data.append(account)
            
            if not account_data:
                raise ValueError("No accounts found in selected portfolio groups")
            
            # Get security info
            security = get_mock_security(security_id)
            if not security:
                raise ValueError(f"Security {security_id} not found")
            
            # Create allocation engine
            engine = AllocationEngineFactory.create_simple_engine(method)
            
            # Calculate allocations
            allocation_results = engine.allocate(
                order_quantity=quantity,
                accounts=account_data,
                constraints=constraints,
                parameters=parameters
            )
            
            # Calculate summary metrics
            total_allocated = sum(a["allocated_quantity"] for a in allocation_results)
            unallocated = quantity - total_allocated
            allocation_rate = total_allocated / quantity if quantity > 0 else 0
            accounts_allocated = sum(1 for a in allocation_results if a["allocated_quantity"] > 0)
            accounts_skipped = len(account_data) - accounts_allocated
            
            # Prepare response
            response = {
                "allocation_id": allocation_id,
                "timestamp": datetime.utcnow(),
                "order": {
                    "security_id": security_id,
                    "side": side,
                    "total_quantity": quantity,
                    "settlement_date": settlement_date
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
            
            logger.info(f"Allocation commit requested by {user_id} for {allocation_id}")
            
            # In a real implementation, we would:
            # 1. Retrieve the allocation from database
            # 2. Validate it hasn't been committed already
            # 3. Send orders to Aladdin
            # 4. Update database with results
            
            # For now, return mock success response
            return {
                "allocation_id": allocation_id,
                "status": "COMMITTED",
                "commit_timestamp": datetime.utcnow().isoformat(),
                "aladdin_order_ids": [
                    f"ALAD-{allocation_id[:8]}-001",
                    f"ALAD-{allocation_id[:8]}-002",
                    f"ALAD-{allocation_id[:8]}-003"
                ],
                "audit_id": str(uuid.uuid4()),
                "allocations": [
                    {
                        "account_id": "PUB001",
                        "status": "SUCCESS",
                        "aladdin_order_id": f"ALAD-{allocation_id[:8]}-001"
                    },
                    {
                        "account_id": "PUB002",
                        "status": "SUCCESS",
                        "aladdin_order_id": f"ALAD-{allocation_id[:8]}-002"
                    },
                    {
                        "account_id": "PUB003",
                        "status": "SUCCESS",
                        "aladdin_order_id": f"ALAD-{allocation_id[:8]}-003"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Allocation commit failed: {e}", exc_info=True)
            ns.abort(500, f"Failed to commit allocation: {str(e)}")