"""DM conversation retrieval module.

Handles fetching direct message conversations from X API v2 with proper
pagination, rate limiting, and data processing.
"""

import time
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime, timedelta
import structlog
from .client import XAPIClient
from .models import Conversation, Message, User, ConversationBatch
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = structlog.get_logger()


class DMFetcher:
    """Fetches and processes direct message conversations from X API."""
    
    def __init__(self, client: XAPIClient):
        """Initialize the DM fetcher.
        
        Args:
            client: Authenticated X API client instance.
        """
        self.client = client
        self.users_cache: Dict[str, User] = {}
    
    def get_recent_dm_participants(self, max_results: int = 20) -> List[str]:
        """Get list of recent DM conversation participant IDs.
        
        This uses the DM events endpoint to discover recent conversation partners.
        
        Args:
            max_results: Maximum number of recent participants to discover.
            
        Returns:
            List of participant user IDs from recent conversations.
        """
        logger.info("Discovering recent DM conversation participants...")
        
        try:
            # Get recent DM events via centralized client
            data = self.client.get_recent_dm_events(max_results=max_results * 5)
            if not data:
                return []
            events = data.get("data", [])
            
            # Get your own user ID to filter out
            my_user_info = self.client.verify_credentials()
            my_user_id = my_user_info["id"]
            
            # Extract unique participant IDs (excluding yourself)
            participant_ids = set()
            for event in events:
                sender_id = event.get("sender_id")
                if sender_id and sender_id != my_user_id:
                    participant_ids.add(sender_id)
                    
                if len(participant_ids) >= max_results:
                    break
            
            participant_list = list(participant_ids)
            logger.info(
                "Discovered recent DM participants",
                count=len(participant_list),
                participants=participant_list[:5]  # Log first 5 for preview
            )
            
            return participant_list
            
        except Exception as e:
            logger.error("Failed to discover DM participants", error=str(e))
            return []
    
    def fetch_conversation_with_user(
        self, 
        participant_id: str, 
        max_results: int = 100,
        since_days: Optional[int] = None
    ) -> Conversation:
        """Fetch complete conversation with a specific user.
        
        Args:
            participant_id: ID of the user to fetch conversation with.
            max_results: Maximum number of messages to fetch.
            since_days: Only fetch messages from the last N days.
            
        Returns:
            Conversation object with all messages and metadata.
            
        Raises:
            Exception: If API call fails or conversation cannot be fetched.
        """
        logger.info("Fetching conversation", participant_id=participant_id)
        
        conversation = Conversation(participant_id=participant_id)
        
        try:
            # Fetch user information for the participant
            participant_user = self._get_user_info(participant_id)
            conversation.participant = participant_user
            
            # Build query parameters
            params = {
                "dm_event.fields": [
                    "id", "text", "created_at", "sender_id", 
                    "dm_conversation_id", "event_type", "attachments"
                ],
                "user.fields": ["id", "username", "name"],
                "max_results": min(max_results, 100)  # API limit
            }
            
            # Add time filter if specified
            if since_days:
                start_time = datetime.utcnow() - timedelta(days=since_days)
                params["start_time"] = start_time.isoformat() + "Z"
            
            # Fetch messages with pagination
            next_token = None
            total_fetched = 0
            
            while total_fetched < max_results:
                if next_token:
                    params["pagination_token"] = next_token
                
                # Check rate limits before making request
                if not self.client.check_rate_limit("dm_conversations"):
                    logger.warning("Rate limit reached, waiting...")
                    time.sleep(60)  # Wait 1 minute before retry
                
                # Make API request via centralized client
                response = self.client.get_dm_conversation_events(participant_id, params)
                
                if not response or "data" not in response:
                    logger.warning("No DM data in response", participant_id=participant_id)
                    break
                
                # Process messages from response
                messages = self._parse_dm_events(response["data"])
                for message in messages:
                    conversation.add_message(message)
                    total_fetched += 1
                
                # Check for pagination
                if "meta" in response and "next_token" in response["meta"]:
                    next_token = response["meta"]["next_token"]
                else:
                    break
                
                # Respect rate limits
                time.sleep(0.1)  # Small delay between requests
            
            logger.info(
                "Conversation fetched successfully",
                participant_id=participant_id,
                message_count=len(conversation.messages)
            )
            
            return conversation
            
        except Exception as e:
            logger.error(
                "Failed to fetch conversation",
                participant_id=participant_id,
                error=str(e)
            )
            raise
    
    def fetch_multiple_conversations(
        self, 
        participant_ids: List[str],
        max_results_per_conversation: int = 100,
        since_days: Optional[int] = None
    ) -> ConversationBatch:
        """Fetch conversations with multiple users.
        
        Args:
            participant_ids: List of user IDs to fetch conversations with.
            max_results_per_conversation: Max messages per conversation.
            
        Returns:
            ConversationBatch containing all fetched conversations.
        """
        logger.info(
            "Fetching multiple conversations",
            participant_count=len(participant_ids)
        )
        
        batch = ConversationBatch(
            conversations=[],
            total_count=len(participant_ids)
        )
        
        # Fetch in parallel with a small pool to balance speed and limits
        def _fetch_one(pid: str) -> Optional[Conversation]:
            try:
                return self.fetch_conversation_with_user(
                    pid, max_results_per_conversation, since_days
                )
            except Exception as exc:
                logger.error("Failed to fetch conversation, skipping", participant_id=pid, error=str(exc))
                return None

        max_workers = min(5, len(participant_ids)) or 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_one, pid): pid for pid in participant_ids}
            for i, future in enumerate(as_completed(futures), start=1):
                pid = futures[future]
                try:
                    conversation = future.result()
                    if conversation:
                        batch.add_conversation(conversation)
                finally:
                    # Gentle pacing between completions
                    time.sleep(0.2)
        
        logger.info(
            "Batch fetch completed",
            successful=len(batch.conversations),
            total=len(participant_ids)
        )
        
        return batch
    
    def _get_user_info(self, user_id: str) -> User:
        """Get user information, using cache when possible.
        
        Args:
            user_id: ID of the user to fetch information for.
            
        Returns:
            User object with profile information.
        """
        if user_id in self.users_cache:
            return self.users_cache[user_id]
        
        try:
            user_response = self.client.client.get_user(
                id=user_id,
                user_fields=["id", "username", "name", "profile_image_url", "public_metrics", 
                           "description", "url", "location", "verified"]
            )
            
            if user_response.data:
                user = User.from_api_response({
                    "id": user_response.data.id,
                    "username": user_response.data.username,
                    "name": user_response.data.name,
                    "profile_image_url": getattr(user_response.data, "profile_image_url", None),
                    "public_metrics": getattr(user_response.data, "public_metrics", None),
                    "description": getattr(user_response.data, "description", None),
                    "url": getattr(user_response.data, "url", None),
                    "location": getattr(user_response.data, "location", None),
                    "verified": getattr(user_response.data, "verified", False)
                })
                
                self.users_cache[user_id] = user
                return user
            else:
                raise Exception("User data not found in response")
                
        except Exception as e:
            logger.error("Failed to fetch user info", user_id=user_id, error=str(e))
            # Return minimal user object as fallback
            return User(id=user_id, username=f"user_{user_id}", name="Unknown User")
    
    def _make_dm_request(self, participant_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a DM API request with error handling.
        
        Args:
            participant_id: ID of conversation participant.
            params: Request parameters.
            
        Returns:
            API response data or None if request fails.
        """
        try:
            if not self.client.client:
                raise ValueError("Twitter client not initialized")
            
            # Use the X API v2 DM conversation endpoint
            # Note: This endpoint requires special permissions
            url = f"https://api.twitter.com/2/dm_conversations/with/{participant_id}/dm_events"
            
            # Make the request using requests with OAuth 1.0a
            import requests
            from requests_oauthlib import OAuth1
            
            # Set up OAuth 1.0a authentication
            auth = OAuth1(
                client_key=self.client.client.consumer_key,
                client_secret=self.client.client.consumer_secret,
                resource_owner_key=self.client.client.access_token,
                resource_owner_secret=self.client.client.access_token_secret,
                signature_method='HMAC-SHA1',
                signature_type='AUTH_HEADER'
            )
            
            response = requests.get(url, params=params, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(
                    "DM request successful",
                    participant_id=participant_id,
                    result_count=len(data.get("data", []))
                )
                return data
            else:
                logger.error(
                    "DM request failed",
                    participant_id=participant_id,
                    status_code=response.status_code,
                    error=response.text
                )
                return None
                
        except Exception as e:
            logger.error(
                "DM request exception",
                participant_id=participant_id,
                error=str(e)
            )
            return None
    
    def _parse_dm_events(self, events_data: List[Dict[str, Any]]) -> List[Message]:
        """Parse DM events from API response into Message objects.
        
        Args:
            events_data: List of DM event objects from API.
            
        Returns:
            List of parsed Message objects.
        """
        messages = []
        
        for event in events_data:
            try:
                if event.get("event_type") == "MessageCreate":
                    message = Message.from_api_response(event)
                    messages.append(message)
            except Exception as e:
                logger.warning(
                    "Failed to parse message event",
                    event_id=event.get("id"),
                    error=str(e)
                )
                continue
        
        return messages
