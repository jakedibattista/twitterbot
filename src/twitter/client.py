"""X API v2 client with OAuth authentication.

Provides authenticated access to X API v2 endpoints with proper
error handling, rate limiting, and retry logic.
"""

import tweepy
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog
from config.settings import settings
import requests
from requests_oauthlib import OAuth1

logger = structlog.get_logger()


@dataclass
class RateLimitInfo:
    """Rate limit tracking information."""
    remaining: int
    reset_time: datetime
    limit: int


class XAPIClient:
    """X API v2 client with authentication and rate limiting.
    
    Handles OAuth 1.0a authentication for accessing user's direct messages
    and provides methods for fetching DM conversations with proper rate
    limit handling.
    """
    
    def __init__(self):
        """Initialize the X API client with OAuth authentication."""
        self.client: Optional[tweepy.Client] = None
        self.api_v1: Optional[tweepy.API] = None  # For some operations still requiring v1.1
        self.rate_limit_info: Dict[str, RateLimitInfo] = {}
        self._setup_authentication()
    
    def _setup_authentication(self) -> None:
        """Set up OAuth authentication for X API access."""
        try:
            # Validate credentials are present
            if not settings.validate_x_credentials():
                raise ValueError("Missing required X API credentials in environment variables")
            
            # Set up OAuth 1.0a authentication
            auth = tweepy.OAuthHandler(
                consumer_key=settings.x_api_key,
                consumer_secret=settings.x_api_secret
            )
            auth.set_access_token(
                key=settings.x_access_token,
                secret=settings.x_access_token_secret
            )
            
            # Initialize API v2 client with user context
            self.client = tweepy.Client(
                consumer_key=settings.x_api_key,
                consumer_secret=settings.x_api_secret,
                access_token=settings.x_access_token,
                access_token_secret=settings.x_access_token_secret,
                wait_on_rate_limit=True  # Automatically handle rate limiting
            )
            
            # Initialize API v1.1 for operations not yet available in v2
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            
            logger.info("X API authentication successful")
            
        except Exception as e:
            logger.error("Failed to authenticate with X API", error=str(e))
            raise

    def _build_oauth1(self) -> OAuth1:
        """Create an OAuth1 object for raw HTTP requests to X API v2 endpoints.
        
        Returns:
            Configured OAuth1 instance using credentials from settings.
        """
        return OAuth1(
            client_key=settings.x_api_key,
            client_secret=settings.x_api_secret,
            resource_owner_key=settings.x_access_token,
            resource_owner_secret=settings.x_access_token_secret,
            signature_method='HMAC-SHA1',
            signature_type='AUTH_HEADER'
        )

    def get_recent_dm_events(self, max_results: int = 50) -> Optional[Dict[str, Any]]:
        """Fetch recent DM events to discover recent participants.
        
        Args:
            max_results: Maximum number of events to request (API limits apply).
        
        Returns:
            Parsed JSON response or None on error.
        """
        try:
            url = "https://api.twitter.com/2/dm_events"
            params: Dict[str, Any] = {
                "dm_event.fields": "id,sender_id,created_at",
                "user.fields": "id,username,name",
                "max_results": min(max_results, 100),
                "expansions": "sender_id",
            }
            auth = self._build_oauth1()
            response = requests.get(url, params=params, auth=auth)

            # Update rate limit info if headers present
            self.update_rate_limit_info("dm_events", response.headers)

            if response.status_code != 200:
                logger.error(
                    "Failed to get recent DM events",
                    status_code=response.status_code,
                    error=response.text,
                )
                return None
            return response.json()
        except Exception as e:
            logger.error("Exception fetching recent DM events", error=str(e))
            return None

    def get_dm_conversation_events(self, participant_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch DM conversation events with a specific participant.
        
        Args:
            participant_id: Conversation counterparty user ID.
            params: Query parameters including pagination tokens.
        
        Returns:
            Parsed JSON response or None on error.
        """
        try:
            url = f"https://api.twitter.com/2/dm_conversations/with/{participant_id}/dm_events"
            auth = self._build_oauth1()
            response = requests.get(url, params=params, auth=auth)

            # Update rate limits for this endpoint
            self.update_rate_limit_info("dm_conversations", response.headers)

            if response.status_code == 200:
                data = response.json()
                logger.debug(
                    "DM conversation request successful",
                    participant_id=participant_id,
                    result_count=len(data.get("data", [])),
                )
                return data
            else:
                logger.error(
                    "DM conversation request failed",
                    participant_id=participant_id,
                    status_code=response.status_code,
                    error=response.text,
                )
                return None
        except Exception as e:
            logger.error(
                "DM conversation request exception",
                participant_id=participant_id,
                error=str(e),
            )
            return None
    
    def verify_credentials(self) -> Dict[str, Any]:
        """Verify API credentials and return authenticated user info.
        
        Returns:
            Dictionary containing authenticated user information.
            
        Raises:
            Exception: If credentials are invalid or API call fails.
        """
        try:
            if not self.client:
                raise ValueError("API client not initialized")
            
            # Get authenticated user's information
            user = self.client.get_me(
                user_fields=["id", "username", "name", "public_metrics"]
            )
            
            if user.data:
                user_info = {
                    "id": user.data.id,
                    "username": user.data.username,
                    "name": user.data.name,
                    "public_metrics": user.data.public_metrics
                }
                logger.info("Credentials verified", user_id=user_info["id"], username=user_info["username"])
                return user_info
            else:
                raise Exception("Failed to retrieve user information")
                
        except Exception as e:
            logger.error("Credential verification failed", error=str(e))
            raise
    
    def check_rate_limit(self, endpoint: str) -> bool:
        """Check if we're within rate limits for a specific endpoint.
        
        Args:
            endpoint: The API endpoint to check rate limits for.
            
        Returns:
            True if we can make requests, False if we need to wait.
        """
        if endpoint not in self.rate_limit_info:
            return True
        
        rate_info = self.rate_limit_info[endpoint]
        now = datetime.now()
        
        if now >= rate_info.reset_time:
            # Rate limit window has reset
            return True
        
        if rate_info.remaining <= 0:
            # No requests remaining in current window
            wait_time = (rate_info.reset_time - now).total_seconds()
            logger.warning(
                "Rate limit reached, need to wait",
                endpoint=endpoint,
                wait_seconds=wait_time
            )
            return False
        
        return True
    
    def update_rate_limit_info(self, endpoint: str, headers: Dict[str, str]) -> None:
        """Update rate limit tracking from response headers.
        
        Args:
            endpoint: The API endpoint that was called.
            headers: Response headers containing rate limit information.
        """
        try:
            remaining = int(headers.get('x-rate-limit-remaining', 0))
            reset_timestamp = int(headers.get('x-rate-limit-reset', 0))
            limit = int(headers.get('x-rate-limit-limit', 0))
            
            reset_time = datetime.fromtimestamp(reset_timestamp)
            
            self.rate_limit_info[endpoint] = RateLimitInfo(
                remaining=remaining,
                reset_time=reset_time,
                limit=limit
            )
            
            logger.debug(
                "Updated rate limit info",
                endpoint=endpoint,
                remaining=remaining,
                reset_time=reset_time.isoformat()
            )
            
        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse rate limit headers", error=str(e))


# Global client instance
x_client = XAPIClient()

