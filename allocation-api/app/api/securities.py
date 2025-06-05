"""Securities API endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from app.services.aladdin_client import get_aladdin_client, AladdinAPIError
from app.core.logging import get_logger
from app.utils.async_helpers import run_async

logger = get_logger(__name__)

ns = Namespace("securities", description="Security search and information")

# Models
security_model = ns.model("Security", {
    "cusip": fields.String(description="CUSIP identifier"),
    "ticker": fields.String(description="Ticker symbol"),
    "description": fields.String(description="Security description"),
    "coupon": fields.Float(description="Coupon rate"),
    "maturity": fields.Date(description="Maturity date"),
    "duration": fields.Float(description="Duration"),
    "oas": fields.Float(description="Option-adjusted spread"),
    "min_denomination": fields.Float(description="Minimum denomination")
})

security_search_response = ns.model("SecuritySearchResponse", {
    "securities": fields.List(fields.Nested(security_model))
})

security_analytics_model = ns.model("SecurityAnalytics", {
    "cusip": fields.String(description="CUSIP identifier"),
    "price": fields.Float(description="Current price"),
    "yield": fields.Float(description="Yield"),
    "duration": fields.Float(description="Modified duration"),
    "spread_duration": fields.Float(description="Spread duration"),
    "convexity": fields.Float(description="Convexity"),
    "oas": fields.Float(description="Option-adjusted spread"),
    "dv01": fields.Float(description="Dollar value of 01")
})


@ns.route("/search")
class SecuritySearch(Resource):
    @ns.doc("search_securities")
    @ns.param("query", "CUSIP or ticker to search", required=True)
    @ns.param("limit", "Maximum number of results", default=50)
    @ns.marshal_with(security_search_response)
    @ns.response(200, "Success")
    @ns.response(400, "Bad request")
    @ns.response(401, "Unauthorized")
    @jwt_required()
    def get(self):
        """Search securities"""
        query = request.args.get("query")
        limit = request.args.get("limit", 50, type=int)
        
        if not query:
            ns.abort(400, "Query parameter is required")
        
        try:
            logger.info(f"Searching securities with query: {query}")
            
            # Define async function
            async def search_securities():
                client = get_aladdin_client()
                async with client:
                    return await client.search_securities(
                        query=query,
                        limit=limit
                    )
            
            # Run async function
            search_results = run_async(search_securities)
            
            # Transform results
            securities = []
            for result in search_results:
                securities.append({
                    "cusip": result.get("cusip", ""),
                    "ticker": result.get("ticker", ""),
                    "description": result.get("description", ""),
                    "coupon": result.get("coupon", 0.0),
                    "maturity": result.get("maturityDate"),
                    "duration": result.get("duration", 0.0),
                    "oas": result.get("oas", 0.0),
                    "min_denomination": result.get("minDenomination", 1000.0)
                })
            
            logger.info(f"Found {len(securities)} securities matching '{query}'")
            
            return {"securities": securities}
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            ns.abort(500, f"Failed to search securities: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")


@ns.route("/<string:security_id>")
@ns.param("security_id", "Security identifier (CUSIP)")
class SecurityDetail(Resource):
    @ns.doc("get_security_details")
    @ns.marshal_with(security_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @ns.response(404, "Security not found")
    @jwt_required()
    def get(self, security_id):
        """Get security details"""
        try:
            logger.info(f"Fetching security details for: {security_id}")
            
            # Define async function
            async def get_security_details():
                client = get_aladdin_client()
                async with client:
                    return await client.get_security_details(
                        security_id=security_id,
                        id_type="CUSIP"
                    )
            
            # Run async function
            security = run_async(get_security_details)
            
            if not security:
                ns.abort(404, f"Security {security_id} not found")
            
            # Transform to our format
            result = {
                "cusip": security.get("cusip", security_id),
                "ticker": security.get("ticker", ""),
                "description": security.get("description", ""),
                "coupon": security.get("coupon", 0.0),
                "maturity": security.get("maturityDate"),
                "duration": security.get("duration", 0.0),
                "oas": security.get("oas", 0.0),
                "min_denomination": security.get("minDenomination", 1000.0)
            }
            
            logger.info(f"Retrieved security details for {security_id}")
            
            return result
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            if e.status_code == 404:
                ns.abort(404, f"Security {security_id} not found")
            ns.abort(500, f"Failed to fetch security details: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")


@ns.route("/<string:security_id>/analytics")
@ns.param("security_id", "Security identifier (CUSIP)")
class SecurityAnalytics(Resource):
    @ns.doc("get_security_analytics")
    @ns.marshal_with(security_analytics_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @ns.response(404, "Security not found")
    @jwt_required()
    def get(self, security_id):
        """Get security analytics"""
        try:
            logger.info(f"Fetching security analytics for: {security_id}")
            
            # Define async function
            async def get_analytics():
                client = get_aladdin_client()
                async with client:
                    return await client.get_security_analytics(
                        security_id=security_id,
                        analytics_type="RISK"
                    )
            
            # Run async function
            analytics = run_async(get_analytics)
            
            if not analytics:
                ns.abort(404, f"Analytics for security {security_id} not found")
            
            # Transform to our format
            # Handle both flat and nested response formats
            if "riskByCurrency" in analytics:
                # Mock data format
                risk_data = analytics["riskByCurrency"].get("USD", {})
                result = {
                    "cusip": security_id,
                    "price": risk_data.get("price", 100.0),
                    "yield": risk_data.get("yield", 0.0),
                    "duration": risk_data.get("duration", 0.0),
                    "spread_duration": risk_data.get("spreadDuration", 0.0),
                    "convexity": risk_data.get("convexity", 0.0),
                    "oas": risk_data.get("oas", 0.0),
                    "dv01": risk_data.get("dv01", 0.0)
                }
            else:
                # Direct format
                result = {
                    "cusip": security_id,
                    "price": analytics.get("price", 100.0),
                    "yield": analytics.get("yield", 0.0),
                    "duration": analytics.get("modifiedDuration", 0.0),
                    "spread_duration": analytics.get("spreadDuration", 0.0),
                    "convexity": analytics.get("convexity", 0.0),
                    "oas": analytics.get("oas", 0.0),
                    "dv01": analytics.get("dv01", 0.0)
                }
            
            logger.info(f"Retrieved analytics for security {security_id}")
            
            return result
            
        except AladdinAPIError as e:
            logger.error(f"Aladdin API error: {e}")
            if e.status_code == 404:
                ns.abort(404, f"Security {security_id} not found")
            ns.abort(500, f"Failed to fetch security analytics: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ns.abort(500, "An unexpected error occurred")