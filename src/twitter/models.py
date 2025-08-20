"""Data models for Twitter conversations and messages.

Provides structured data classes for handling Twitter DM conversations,
messages, and user information with proper type safety and validation.
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Types of messages in a conversation."""
    MESSAGE_CREATE = "MessageCreate"
    MEDIA_SHARE = "MediaShare"
    WELCOME_MESSAGE = "WelcomeMessage"


@dataclass
class User:
    """Represents a Twitter user."""
    id: str
    username: str
    name: str
    profile_image_url: Optional[str] = None
    public_metrics: Optional[Dict[str, int]] = None
    description: Optional[str] = None  # Bio
    url: Optional[str] = None  # Website URL
    location: Optional[str] = None
    verified: Optional[bool] = None
    linkedin_url: Optional[str] = None  # Extracted/discovered LinkedIn
    
    def __post_init__(self):
        """Initialize LinkedIn URL after dataclass creation."""
        if self.linkedin_url is None:
            # First try regex extraction for direct mentions
            self.linkedin_url = self._extract_linkedin_url()
            
            # If no direct LinkedIn found, we can optionally use AI discovery
            # This would be called separately to avoid API costs for every user
    
    @classmethod
    def from_api_response(cls, user_data: Dict[str, Any]) -> "User":
        """Create User instance from X API response.
        
        Args:
            user_data: User data from X API response.
            
        Returns:
            User instance populated with API data.
        """
        user = cls(
            id=user_data["id"],
            username=user_data["username"],
            name=user_data["name"],
            profile_image_url=user_data.get("profile_image_url"),
            public_metrics=user_data.get("public_metrics"),
            description=user_data.get("description"),
            url=user_data.get("url"),
            location=user_data.get("location"),
            verified=user_data.get("verified", False)
        )
        
        # Try to extract LinkedIn URL from bio or website
        user.linkedin_url = user._extract_linkedin_url()
        return user
    
    def _extract_linkedin_url(self) -> Optional[str]:
        """Extract LinkedIn URL from bio or website URL.
        
        Returns:
            LinkedIn URL if found, None otherwise.
        """
        import re
        
        # Check website URL first
        if self.url and "linkedin.com/in/" in self.url.lower():
            return self.url
        
        # Check bio/description for LinkedIn mentions
        if self.description:
            # Look for LinkedIn URLs in bio
            linkedin_patterns = [
                r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?',
                r'linkedin\.com/in/[\w\-]+',
                r'LinkedIn:\s*linkedin\.com/in/[\w\-]+',  # "LinkedIn: linkedin.com/in/username"
                r'@linkedin:?\s*([\w\-]+)',  # @linkedin: username format
            ]
            
            for pattern in linkedin_patterns:
                match = re.search(pattern, self.description, re.IGNORECASE)
                if match:
                    url = match.group(0).strip()
                    
                    # Handle @linkedin: username format
                    if '@linkedin:' in url.lower() or url.startswith('@linkedin'):
                        username = re.sub(r'@?linkedin:?\s*', '', url, flags=re.IGNORECASE).strip()
                        return f'https://www.linkedin.com/in/{username}'
                    
                    # Normalize regular LinkedIn URLs
                    if not url.startswith('http'):
                        if url.startswith('linkedin.com'):
                            url = 'https://www.' + url
                        else:
                            # Add missing parts
                            url = f'https://www.{url}' if not url.startswith('www.') else f'https://{url}'
                    
                    return url
        
        return None


@dataclass
class Message:
    """Represents a single direct message."""
    id: str
    text: str
    created_at: datetime
    sender_id: str
    conversation_id: Optional[str] = None
    recipient_id: Optional[str] = None
    message_type: MessageType = MessageType.MESSAGE_CREATE
    attachments: Optional[List[Dict[str, Any]]] = None
    referenced_tweet: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, message_data: Dict[str, Any]) -> "Message":
        """Create Message instance from X API response.
        
        Args:
            message_data: Message data from X API dm_events response.
            
        Returns:
            Message instance populated with API data.
        """
        # Parse datetime from ISO format
        created_at = datetime.fromisoformat(
            message_data["created_at"].replace("Z", "+00:00")
        )
        
        return cls(
            id=message_data["id"],
            text=message_data.get("text", ""),
            created_at=created_at,
            sender_id=message_data["sender_id"],
            conversation_id=message_data.get("dm_conversation_id", ""),
            message_type=MessageType(message_data.get("event_type", "MessageCreate")),
            attachments=message_data.get("attachments"),
            referenced_tweet=message_data.get("referenced_tweet")
        )


@dataclass
class Conversation:
    """Represents a complete DM conversation between two users."""
    participant_id: str
    participant: Optional[User] = None
    messages: List[Message] = None
    total_message_count: int = 0
    last_message_time: Optional[datetime] = None
    summary: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.messages is None:
            self.messages = []
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation.
        
        Args:
            message: Message to add to the conversation.
        """
        self.messages.append(message)
        self.total_message_count = len(self.messages)
        
        # Update last message time
        if not self.last_message_time or message.created_at > self.last_message_time:
            self.last_message_time = message.created_at
    
    def get_messages_chronological(self) -> List[Message]:
        """Get messages sorted chronologically (oldest first).
        
        Returns:
            List of messages sorted by creation time.
        """
        return sorted(self.messages, key=lambda m: m.created_at)
    
    def get_message_text_only(self) -> List[str]:
        """Extract only the text content from all messages.
        
        Returns:
            List of message text strings.
        """
        return [msg.text for msg in self.messages if msg.text]
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary format for Google Sheets.
        
        Returns:
            Dictionary with username, user_id, and summary.
        """
        return {
            "username": self.participant.username if self.participant else "Unknown",
            "user_id": self.participant_id,
            "conversation_summary": self.summary or "No summary generated",
            "message_count": self.total_message_count,
            "last_message_date": self.last_message_time.isoformat() if self.last_message_time else None
        }


@dataclass
class ConversationBatch:
    """Represents a batch of conversations for processing."""
    conversations: List[Conversation]
    total_count: int
    processed_count: int = 0
    
    def add_conversation(self, conversation: Conversation) -> None:
        """Add a conversation to the batch.
        
        Args:
            conversation: Conversation to add.
        """
        self.conversations.append(conversation)
        self.total_count = len(self.conversations)
    
    def mark_processed(self, conversation_id: str) -> None:
        """Mark a conversation as processed.
        
        Args:
            conversation_id: ID of the conversation that was processed.
        """
        self.processed_count += 1
    
    def get_unprocessed(self) -> List[Conversation]:
        """Get conversations that haven't been summarized yet.
        
        Returns:
            List of conversations without summaries.
        """
        return [conv for conv in self.conversations if not conv.summary]
