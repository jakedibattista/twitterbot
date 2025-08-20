"""Data formatting utilities for Google Sheets output.

Handles conversion of conversation data into formats suitable for
Google Sheets display and processing.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from ..twitter.models import Conversation, ConversationBatch

logger = structlog.get_logger()


class SheetsFormatter:
    """Formats conversation data for Google Sheets output."""
    
    @staticmethod
    def format_conversation_for_sheets(conversation: Conversation) -> Dict[str, Any]:
        """Format a single conversation for Google Sheets row.
        
        Args:
            conversation: Conversation object to format.
            
        Returns:
            Dictionary with formatted data for sheets.
        """
        participant = conversation.participant
        
        return {
            "username": participant.username if participant else "Unknown",
            "user_id": conversation.participant_id,
            "real_name": participant.name if participant else "Unknown",
            "linkedin_url": participant.linkedin_url if participant and participant.linkedin_url else "",
            "location": participant.location if participant and participant.location else "",
            "bio": participant.description if participant and participant.description else "",
            "website": participant.url if participant and participant.url else "",
            "verified": "✓" if participant and participant.verified else "",
            "conversation_summary": conversation.summary or "No summary available",
            "message_count": conversation.total_message_count,
            "last_message_date": (
                conversation.last_message_time.strftime("%Y-%m-%d %H:%M:%S") 
                if conversation.last_message_time 
                else ""
            )
        }
    
    @staticmethod
    def format_conversations_batch(batch: ConversationBatch) -> List[Dict[str, Any]]:
        """Format a batch of conversations for Google Sheets.
        
        Args:
            batch: ConversationBatch containing multiple conversations.
            
        Returns:
            List of formatted conversation dictionaries.
        """
        formatted_conversations = []
        
        for conversation in batch.conversations:
            try:
                formatted_conv = SheetsFormatter.format_conversation_for_sheets(conversation)
                formatted_conversations.append(formatted_conv)
            except Exception as e:
                logger.warning(
                    "Failed to format conversation for sheets",
                    participant_id=conversation.participant_id,
                    error=str(e)
                )
                # Add minimal entry for failed formatting
                formatted_conversations.append({
                    "username": "Error",
                    "user_id": conversation.participant_id,
                    "conversation_summary": f"Formatting error: {str(e)}",
                    "message_count": 0,
                    "last_message_date": ""
                })
        
        logger.info(
            "Formatted conversations batch",
            total=len(batch.conversations),
            formatted=len(formatted_conversations)
        )
        
        return formatted_conversations
    
    @staticmethod
    def create_summary_statistics(batch: ConversationBatch) -> Dict[str, Any]:
        """Create summary statistics for the conversation batch.
        
        Args:
            batch: ConversationBatch to analyze.
            
        Returns:
            Dictionary with summary statistics.
        """
        total_conversations = len(batch.conversations)
        total_messages = sum(conv.total_message_count for conv in batch.conversations)
        
        # Find most recent conversation
        most_recent = None
        for conv in batch.conversations:
            if conv.last_message_time:
                if not most_recent or conv.last_message_time > most_recent:
                    most_recent = conv.last_message_time
        
        # Calculate average messages per conversation
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        # Count conversations with summaries
        summarized_count = sum(1 for conv in batch.conversations if conv.summary)
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "average_messages_per_conversation": round(avg_messages, 2),
            "conversations_with_summaries": summarized_count,
            "summary_completion_rate": (
                round((summarized_count / total_conversations) * 100, 1) 
                if total_conversations > 0 else 0
            ),
            "most_recent_message": (
                most_recent.strftime("%Y-%m-%d %H:%M:%S") 
                if most_recent else "No messages"
            ),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def format_statistics_for_sheets(stats: Dict[str, Any]) -> List[List[str]]:
        """Format statistics as rows for Google Sheets.
        
        Args:
            stats: Statistics dictionary from create_summary_statistics.
            
        Returns:
            List of rows for appending to sheets.
        """
        stats_rows = [
            [""],  # Empty row for spacing
            ["=== SUMMARY STATISTICS ==="],
            ["Total Conversations", str(stats["total_conversations"])],
            ["Total Messages", str(stats["total_messages"])],
            ["Average Messages/Conversation", str(stats["average_messages_per_conversation"])],
            ["Conversations with Summaries", str(stats["conversations_with_summaries"])],
            ["Summary Completion Rate", f"{stats['summary_completion_rate']}%"],
            ["Most Recent Message", stats["most_recent_message"]],
            ["Report Generated", stats["generated_at"]],
            [""]  # Empty row for spacing
        ]
        
        return stats_rows
    
    @staticmethod
    def validate_sheet_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean data before writing to sheets.
        
        Args:
            data: List of conversation dictionaries to validate.
            
        Returns:
            List of validated and cleaned conversation data.
        """
        validated_data = []
        
        for i, conv_data in enumerate(data):
            try:
                # Ensure required fields exist
                validated_conv = {
                    "username": str(conv_data.get("username", "Unknown")).strip(),
                    "user_id": str(conv_data.get("user_id", "")).strip(),
                    "real_name": str(conv_data.get("real_name", "Unknown")).strip(),
                    "linkedin_url": str(conv_data.get("linkedin_url", "")).strip(),
                    "location": str(conv_data.get("location", "")).strip(),
                    "bio": str(conv_data.get("bio", "")).strip(),
                    "website": str(conv_data.get("website", "")).strip(),
                    "verified": str(conv_data.get("verified", "")).strip(),
                    "conversation_summary": str(conv_data.get("conversation_summary", "")).strip(),
                    "message_count": max(0, int(conv_data.get("message_count", 0))),
                    "last_message_date": str(conv_data.get("last_message_date", "")).strip()
                }
                
                # Truncate summary if too long (Google Sheets cell limit)
                if len(validated_conv["conversation_summary"]) > 50000:
                    validated_conv["conversation_summary"] = (
                        validated_conv["conversation_summary"][:49950] + "... [truncated]"
                    )
                
                # Validate username is not empty
                if (not validated_conv["username"] or validated_conv["username"] == "Unknown") and validated_conv.get("user_id"):
                    validated_conv["username"] = f"User_{validated_conv['user_id'][:8]}"
                
                validated_data.append(validated_conv)
                
            except Exception as e:
                logger.warning(
                    "Failed to validate conversation data",
                    index=i,
                    error=str(e)
                )
                # Add error entry
                validated_data.append({
                    "username": "Validation Error",
                    "user_id": conv_data.get("user_id", "unknown"),
                    "conversation_summary": f"Data validation failed: {str(e)}",
                    "message_count": 0,
                    "last_message_date": ""
                })
        
        logger.info(
            "Data validation completed",
            original_count=len(data),
            validated_count=len(validated_data)
        )
        
        return validated_data
    
    @staticmethod
    def sort_conversations(
        data: List[Dict[str, Any]], 
        sort_by: str = "last_message_date",
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """Sort conversations by specified field.
        
        Args:
            data: List of conversation dictionaries.
            sort_by: Field to sort by ('last_message_date', 'message_count', 'username').
            reverse: If True, sort in descending order.
            
        Returns:
            Sorted list of conversation data.
        """
        try:
            if sort_by == "last_message_date":
                # Sort by date, handling empty dates
                def date_sort_key(conv):
                    date_str = conv.get("last_message_date", "")
                    if not date_str:
                        return datetime.min if reverse else datetime.max
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return datetime.min if reverse else datetime.max
                
                sorted_data = sorted(data, key=date_sort_key, reverse=reverse)
                
            elif sort_by == "message_count":
                sorted_data = sorted(
                    data, 
                    key=lambda x: x.get("message_count", 0), 
                    reverse=reverse
                )
                
            elif sort_by == "username":
                sorted_data = sorted(
                    data, 
                    key=lambda x: x.get("username", "").lower(), 
                    reverse=reverse
                )
                
            else:
                logger.warning(f"Unknown sort field: {sort_by}, using default order")
                sorted_data = data
            
            logger.info(f"Conversations sorted by {sort_by}", count=len(sorted_data))
            return sorted_data
            
        except Exception as e:
            logger.error(f"Failed to sort conversations by {sort_by}", error=str(e))
            return data
