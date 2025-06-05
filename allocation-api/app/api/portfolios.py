"""Portfolio groups API endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt
from app.services.aladdin_client import get_aladdin_client, AladdinAPIError
from app.core.auth import require_auth
from app.core.logging import get_logger
from app.utils.async_helpers import run_async

logger = get_logger(__name__)

ns = Namespace("portfolios", description="Portfolio group operations")

# Models
account_model = ns.model("Account", {
    "account_id": fields.String(description="Account ID"),
    "account_name": fields.String(description="Account name"),
    "nav": fields.Float(description="Net Asset Value", required=False),
    "cash_available": fields.Float(description="Available cash", required=False),
    "strategy": fields.String(description="Investment strategy", required=False),
    "restrictions": fields.List(fields.String, description="Account restrictions", required=False)
})

portfolio_group_model = ns.model("PortfolioGroup", {
    "group_id": fields.String(description="Group ID"),
    "group_name": fields.String(description="Group name"),
    "description": fields.String(description="Group description", required=False),
    "account_count": fields.Integer(description="Number of accounts"),
    "total_nav": fields.Float(description="Total NAV across all accounts", required=False),
    "strategy": fields.String(description="Portfolio strategy", required=False),
    "accounts": fields.List(fields.Nested(account_model), required=False)
})

portfolio_group_detail_model = ns.model("PortfolioGroupDetail", {
    "group_id": fields.String(description="Group ID"),
    "group_name": fields.String(description="Group name"),
    "description": fields.String(description="Group description", required=False),
    "account_count": fields.Integer(description="Number of accounts"),
    "total_nav": fields.Float(description="Total NAV across all accounts", required=False),
    "strategy": fields.String(description="Portfolio strategy", required=False),
    "created_date": fields.String(description="Creation date", required=False),
    "manager": fields.String(description="Portfolio manager", required=False)
})

account_detail_model = ns.model("AccountDetail", {
    "account_id": fields.String(description="Account ID"),
    "account_name": fields.String(description="Account name"),
    "nav": fields.Float(description="Net Asset Value"),
    "cash_available": fields.Float(description="Available cash"),
    "strategy": fields.String(description="Investment strategy", required=False),
    "restrictions": fields.List(fields.String, description="Account restrictions")
})

portfolio_group_accounts_response = ns.model("PortfolioGroupAccountsResponse", {
    "accounts": fields.List(fields.Nested(account_detail_model)),
    "total_accounts": fields.Integer(description="Total number of accounts"),
    "total_nav": fields.Float(description="Total NAV across all accounts")
})

portfolio_groups_response = ns.model("PortfolioGroupsResponse", {
    "portfolio_groups": fields.List(fields.Nested(portfolio_group_model))
})


@ns.route("")
class PortfolioGroups(Resource):
    @ns.doc("get_portfolio_groups")
    @ns.marshal_with(portfolio_groups_response)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @ns.response(500, "Internal server error")
    @jwt_required()
    def get(self):
        """Get all portfolio groups"""
        try:
            logger.info("Fetching portfolio groups")
            
            # Define async function to fetch data
            async def fetch_portfolio_groups():
                client = get_aladdin_client()
                async with client:
                    groups_data = await client.get_portfolio_groups()
                
                portfolio_groups = []
                
                for group in groups_data:
                    async with client:
                        members = await client.get_portfolio_group_members(group["ticker"])
                    
                    accounts = [
                        {
                            "account_id": member["memberTicker"],
                            "account_name": member.get("memberName", member["memberTicker"])
                        }
                        for member in members
                    ]
                    
                    portfolio_groups.append({
                        "group_id": group["ticker"],
                        "group_name": group.get("name", group["ticker"]),
                        "description": group.get("description", ""),
                        "account_count": len(accounts),
                        "total_nav": group.get("totalNav", 0.0),
                        "strategy": group.get("strategy", "")
                        # Note: accounts are excluded from list view per API spec
                    })
                
                return portfolio_groups
            
            # Run async function
            portfolio_groups = run_async(fetch_portfolio_groups)
            
            logger.info(f"Retrieved {len(portfolio_groups)} portfolio groups")
            
            return {"portfolio_groups": portfolio_groups}
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            ns.abort(500, f"Failed to fetch portfolio groups: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")


@ns.route("/<string:group_id>")
@ns.param("group_id", "The portfolio group identifier")
class PortfolioGroup(Resource):
    @ns.doc("get_portfolio_group")
    @ns.marshal_with(portfolio_group_detail_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @ns.response(404, "Portfolio group not found")
    @jwt_required()
    def get(self, group_id):
        """Get a specific portfolio group"""
        try:
            logger.info(f"Fetching portfolio group: {group_id}")
            
            # Define async function
            async def fetch_group_details():
                client = get_aladdin_client()
                async with client:
                    groups = await client.get_portfolio_groups(group_ticker=group_id)
                    
                    if not groups:
                        return None
                    
                    group = groups[0]
                    members = await client.get_portfolio_group_members(group_id)
                
                accounts = [
                    {
                        "account_id": member["memberTicker"],
                        "account_name": member.get("memberName", member["memberTicker"])
                    }
                    for member in members
                ]
                
                return {
                    "group_id": group["ticker"],
                    "group_name": group.get("name", group["ticker"]),
                    "description": group.get("description", ""),
                    "account_count": len(accounts),
                    "total_nav": group.get("totalNav", 0.0),
                    "strategy": group.get("strategy", ""),
                    "created_date": group.get("createdDate", ""),
                    "manager": group.get("manager", "")
                }
            
            # Run async function
            result = run_async(fetch_group_details)
            
            if result is None:
                ns.abort(404, f"Portfolio group {group_id} not found")
            
            logger.info(f"Retrieved portfolio group {group_id} with {result['account_count']} accounts")
            
            return result
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            if e.status_code == 404:
                ns.abort(404, f"Portfolio group {group_id} not found")
            ns.abort(500, f"Failed to fetch portfolio group: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")


@ns.route("/<string:group_id>/accounts")
@ns.param("group_id", "The portfolio group identifier")
class PortfolioGroupAccounts(Resource):
    @ns.doc("get_portfolio_group_accounts")
    @ns.marshal_with(portfolio_group_accounts_response)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @ns.response(404, "Portfolio group not found")
    @jwt_required()
    def get(self, group_id):
        """Get accounts in a portfolio group"""
        try:
            logger.info(f"Fetching accounts for portfolio group: {group_id}")
            
            # Define async function
            async def fetch_members():
                client = get_aladdin_client()
                async with client:
                    return await client.get_portfolio_group_members(group_id)
            
            # Run async function
            members = run_async(fetch_members)
            
            if not members:
                ns.abort(404, f"Portfolio group {group_id} not found or has no members")
            
            # Transform to our format with additional details
            accounts = []
            total_nav = 0.0
            
            for member in members:
                account = {
                    "account_id": member["memberTicker"],
                    "account_name": member.get("memberName", member["memberTicker"]),
                    "nav": member.get("nav", 0.0),
                    "cash_available": member.get("cashAvailable", 0.0),
                    "strategy": member.get("strategy", ""),
                    "restrictions": member.get("restrictions", [])
                }
                accounts.append(account)
                total_nav += account["nav"]
            
            logger.info(f"Retrieved {len(accounts)} accounts for group {group_id}")
            
            return {
                "accounts": accounts,
                "total_accounts": len(accounts),
                "total_nav": total_nav
            }
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            if e.status_code == 404:
                ns.abort(404, f"Portfolio group {group_id} not found")
            ns.abort(500, f"Failed to fetch accounts: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")