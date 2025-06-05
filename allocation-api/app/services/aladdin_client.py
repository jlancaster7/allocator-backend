"""Aladdin API client with OAuth2 authentication and retry logic"""

import httpx
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import uuid
import json
from functools import lru_cache
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Import mock data functions when in mock mode
if settings.MOCK_ALADDIN_DATA.lower() == "true":
    from app.services.mock_data import (
        get_mock_portfolio_groups,
        get_mock_portfolio_group,
        get_mock_portfolio_group_accounts,
        search_mock_securities,
        get_mock_security,
        get_mock_security_analytics,
        get_mock_positions,
        get_mock_cash_positions
    )


class AladdinAPIError(Exception):
    """Custom exception for Aladdin API errors"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self.lock:
            now = datetime.now(timezone.utc)
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < timedelta(minutes=1)]
            
            if len(self.calls) >= self.calls_per_minute:
                # Wait until the oldest call is more than 1 minute old
                sleep_time = (self.calls[0] + timedelta(minutes=1) - now).total_seconds()
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    # Recursive call to re-check
                    await self.acquire()
            else:
                self.calls.append(now)


class AladdinClient:
    """Client for interacting with BlackRock Aladdin APIs"""
    
    def __init__(self):
        self.base_url = settings.ALADDIN_BASE_URL
        self.client_id = settings.ALADDIN_CLIENT_ID
        self.client_secret = settings.ALADDIN_CLIENT_SECRET
        self.token_url = settings.ALADDIN_OAUTH_TOKEN_URL
        self.use_mock_data = settings.MOCK_ALADDIN_DATA.lower() == "true"
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(settings.ALADDIN_RATE_LIMIT_PER_MINUTE)
        
        # Cache for frequently accessed data
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        if self.use_mock_data:
            logger.info("Using mock Aladdin data for development")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.ALADDIN_REQUEST_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
    
    def _generate_request_headers(self) -> Dict[str, str]:
        """Generate required Aladdin request headers"""
        return {
            "VND.com.blackrock.Request-ID": str(uuid.uuid4()),
            "VND.com.blackrock.Origin-Timestamp": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        if self._access_token and self._token_expires_at and datetime.now(timezone.utc) < self._token_expires_at:
            return self._access_token
        
        logger.info("Refreshing Aladdin OAuth2 token")
        
        await self._ensure_client()
        
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "read write"
        }
        
        try:
            response = await self._client.post(
                self.token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            self._access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
            
            logger.info("OAuth2 token refreshed successfully", expires_at=self._token_expires_at.isoformat())
            return self._access_token
            
        except httpx.HTTPError as e:
            logger.error("Failed to get OAuth2 token", error=str(e))
            raise AladdinAPIError(f"Failed to authenticate with Aladdin: {str(e)}")
    
    def _log_before_retry(self, retry_state):
        """Log before retry attempt"""
        logger.warning(
            "Retrying Aladdin API call",
            attempt=retry_state.attempt_number,
            wait_time=retry_state.next_action.sleep if retry_state.next_action else 0
        )
    
    def _log_after_retry(self, retry_state):
        """Log after retry attempt"""
        logger.info(
            "Retry completed",
            attempt=retry_state.attempt_number,
            outcome="success" if not retry_state.outcome.failed else "failed"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, AladdinAPIError))
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: int = None
    ) -> Union[Dict, List]:
        """Make an authenticated request to Aladdin API with retry logic"""
        
        # Check cache first
        cache_key = f"{method}:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if use_cache and method == "GET" and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.now(timezone.utc) < cached_data["expires_at"]:
                logger.debug("Cache hit", endpoint=endpoint)
                return cached_data["data"]
        
        # Rate limiting
        await self._rate_limiter.acquire()
        
        # Ensure client and token
        await self._ensure_client()
        token = await self._get_access_token()
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        headers = self._generate_request_headers()
        headers["Authorization"] = f"Bearer {token}"
        
        logger.info(
            "Making Aladdin API request",
            method=method,
            endpoint=endpoint,
            request_id=headers["VND.com.blackrock.Request-ID"]
        )
        
        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers
            )
            
            # Check for rate limit headers
            if "X-RateLimit-Remaining" in response.headers:
                remaining = int(response.headers["X-RateLimit-Remaining"])
                if remaining < 10:
                    logger.warning("Approaching rate limit", remaining=remaining)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Cache successful GET requests
            if use_cache and method == "GET":
                ttl = cache_ttl or settings.CACHE_TTL_SECONDS
                self._cache[cache_key] = {
                    "data": data,
                    "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl)
                }
            
            return data
            
        except httpx.HTTPStatusError as e:
            error_detail = {}
            try:
                error_detail = e.response.json()
            except:
                error_detail = {"message": e.response.text}
            
            logger.error(
                "Aladdin API error",
                status_code=e.response.status_code,
                endpoint=endpoint,
                error=error_detail
            )
            
            raise AladdinAPIError(
                f"Aladdin API error: {error_detail.get('message', 'Unknown error')}",
                status_code=e.response.status_code,
                response_data=error_detail
            )
    
    # Portfolio Group APIs
    async def get_portfolio_groups(self, group_ticker: Optional[str] = None) -> List[Dict]:
        """Get portfolio groups"""
        if self.use_mock_data:
            groups = get_mock_portfolio_groups()
            if group_ticker:
                return [g for g in groups if g["ticker"] == group_ticker]
            return groups
        
        params = {}
        if group_ticker:
            params["ticker"] = group_ticker
        
        return await self._make_request("GET", "/portfolio/groups/v1/groups", params=params)
    
    async def get_portfolio_group_members(self, group_ticker: str) -> List[Dict]:
        """Get members of a portfolio group"""
        if self.use_mock_data:
            return get_mock_portfolio_group_accounts(group_ticker)
        
        return await self._make_request(
            "GET", 
            f"/portfolio/groups/v1/groups/{group_ticker}/members"
        )
    
    # Position APIs
    async def get_positions(
        self,
        portfolio_ticker: str,
        pos_type: str = "SOD",
        as_of_date: Optional[str] = None
    ) -> List[Dict]:
        """Get positions for a portfolio"""
        if self.use_mock_data:
            return get_mock_positions(portfolio_ticker, pos_type)
        
        params = {
            "portfolioTicker": portfolio_ticker,
            "posType": pos_type
        }
        if as_of_date:
            params["asOfDate"] = as_of_date
        
        return await self._make_request(
            "GET",
            "/portfolio/positions/v1/positions",
            params=params
        )
    
    # Security Master APIs
    async def search_securities(
        self,
        query: str,
        search_type: str = "ALL",
        limit: int = 50
    ) -> List[Dict]:
        """Search for securities by CUSIP, ticker, or description"""
        if self.use_mock_data:
            return search_mock_securities(query, limit)
        
        params = {
            "query": query,
            "searchType": search_type,
            "limit": limit
        }
        
        return await self._make_request(
            "GET",
            "/security/master/v1/securities/search",
            params=params
        )
    
    async def get_security_details(self, security_id: str, id_type: str = "CUSIP") -> Dict:
        """Get detailed security information"""
        if self.use_mock_data:
            result = get_mock_security(security_id)
            if not result:
                raise AladdinAPIError(f"Security {security_id} not found", status_code=404)
            return result
        
        params = {
            "idType": id_type
        }
        
        return await self._make_request(
            "GET",
            f"/security/master/v1/securities/{security_id}",
            params=params
        )
    
    # Account APIs
    async def get_account_cash(self, account_id: str) -> Dict:
        """Get cash positions for an account"""
        if self.use_mock_data:
            cash_positions = get_mock_cash_positions(account_id)
            return {"cashPositions": cash_positions}
        
        return await self._make_request(
            "GET",
            f"/account/cash/v1/accounts/{account_id}/cash"
        )
    
    async def get_account_nav(self, account_id: str, as_of_date: Optional[str] = None) -> Dict:
        """Get NAV for an account"""
        params = {}
        if as_of_date:
            params["asOfDate"] = as_of_date
        
        return await self._make_request(
            "GET",
            f"/account/nav/v1/accounts/{account_id}/nav",
            params=params
        )
    
    # Order Management APIs
    async def submit_order(self, order_data: Dict) -> Dict:
        """Submit an order to Aladdin"""
        return await self._make_request(
            "POST",
            "/trading/orders/v1/orders",
            json_data=order_data,
            use_cache=False
        )
    
    async def modify_order(self, order_id: str, modifications: Dict) -> Dict:
        """Modify an existing order"""
        return await self._make_request(
            "PATCH",
            f"/trading/orders/v1/orders/{order_id}",
            json_data=modifications,
            use_cache=False
        )
    
    async def cancel_order(self, order_id: str, reason: str) -> Dict:
        """Cancel an order"""
        return await self._make_request(
            "DELETE",
            f"/trading/orders/v1/orders/{order_id}",
            json_data={"reason": reason},
            use_cache=False
        )
    
    # Analytics APIs
    async def get_security_analytics(self, security_id: str, analytics_type: str = "RISK") -> Dict:
        """Get analytics for a security"""
        if self.use_mock_data:
            result = get_mock_security_analytics(security_id)
            if not result:
                raise AladdinAPIError(f"Analytics for security {security_id} not found", status_code=404)
            return result
        
        params = {
            "analyticsType": analytics_type
        }
        
        return await self._make_request(
            "GET",
            f"/analytics/security/v1/securities/{security_id}/analytics",
            params=params
        )
    
    def clear_cache(self):
        """Clear the cache"""
        self._cache.clear()
        logger.info("Aladdin client cache cleared")


# Singleton instance
_aladdin_client: Optional[AladdinClient] = None


def get_aladdin_client() -> AladdinClient:
    """Get singleton Aladdin client instance"""
    global _aladdin_client
    if _aladdin_client is None:
        _aladdin_client = AladdinClient()
    return _aladdin_client