"""AI-powered conversation summarization using OpenAI GPT models.

Provides intelligent summarization of Twitter DM conversations with
context awareness, privacy protection, and multiple summarization strategies.
"""

from typing import List, Optional, Dict, Any
import openai
import structlog
from datetime import datetime
from ..twitter.models import Conversation, Message, ConversationBatch
from config.settings import settings

logger = structlog.get_logger()


class ConversationSummarizer:
    """AI-powered conversation summarizer using OpenAI GPT models."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the conversation summarizer.
        
        Args:
            api_key: OpenAI API key. If None, uses value from settings.
            model: OpenAI model to use for summarization.
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or getattr(settings, "openai_model", "gpt-4o-mini")
        self.client: Optional[openai.OpenAI] = None
        
        if self.api_key:
            self._setup_client()
        else:
            logger.warning("No OpenAI API key provided. Summarization will use fallback method.")
    
    def _setup_client(self) -> None:
        """Set up OpenAI client with API key."""
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize OpenAI client", error=str(e))
            self.client = None
    
    def summarize_conversation(
        self, 
        conversation: Conversation,
        max_length: int = 200,
        include_context: bool = True
    ) -> str:
        """Generate a summary for a single conversation.
        
        Args:
            conversation: Conversation object to summarize.
            max_length: Maximum length of summary in words.
            include_context: Whether to include participant context in summary.
            
        Returns:
            Generated conversation summary.
        """
        try:
            if not conversation.messages:
                return "No messages in conversation"
            
            # Use AI summarization if available, otherwise fallback
            if self.client:
                summary = self._ai_summarize(conversation, max_length, include_context)
            else:
                summary = self._fallback_summarize(conversation, max_length)
            
            # Update conversation object with summary
            conversation.summary = summary
            
            logger.info(
                "Conversation summarized",
                participant_id=conversation.participant_id,
                message_count=len(conversation.messages),
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "Failed to summarize conversation",
                participant_id=conversation.participant_id,
                error=str(e)
            )
            fallback_summary = f"Summary generation failed: {str(e)}"
            conversation.summary = fallback_summary
            return fallback_summary
    
    def summarize_batch(
        self, 
        batch: ConversationBatch,
        max_length: int = 200
    ) -> ConversationBatch:
        """Summarize all conversations in a batch.
        
        Args:
            batch: ConversationBatch containing conversations to summarize.
            max_length: Maximum length of each summary in words.
            
        Returns:
            Updated batch with summaries added to conversations.
        """
        logger.info(
            "Starting batch summarization",
            total_conversations=len(batch.conversations)
        )
        
        summarized_count = 0
        for i, conversation in enumerate(batch.conversations):
            try:
                logger.info(
                    "Summarizing conversation",
                    current=i+1,
                    total=len(batch.conversations),
                    participant_id=conversation.participant_id
                )
                
                self.summarize_conversation(conversation, max_length)
                summarized_count += 1
                batch.mark_processed(conversation.participant_id)
                
            except Exception as e:
                logger.error(
                    "Failed to summarize conversation in batch",
                    participant_id=conversation.participant_id,
                    error=str(e)
                )
                conversation.summary = f"Batch summarization failed: {str(e)}"
        
        logger.info(
            "Batch summarization completed",
            successful=summarized_count,
            total=len(batch.conversations)
        )
        
        return batch
    
    def _ai_summarize(
        self, 
        conversation: Conversation, 
        max_length: int,
        include_context: bool
    ) -> str:
        """Generate AI-powered summary using OpenAI GPT.
        
        Args:
            conversation: Conversation to summarize.
            max_length: Maximum summary length in words.
            include_context: Whether to include participant context.
            
        Returns:
            AI-generated summary.
        """
        try:
            # Prepare conversation text
            messages_text = self._prepare_conversation_text(conversation)
            
            # Build context information
            context = ""
            if include_context and conversation.participant:
                context = f"Conversation with {conversation.participant.username} ({conversation.participant.name}). "
            
            # Create prompt for summarization
            prompt = self._build_summarization_prompt(
                messages_text, 
                max_length, 
                context,
                len(conversation.messages)
            )
            
            # Make API request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that creates concise, accurate summaries of conversations while protecting privacy."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=min(max_length * 2, 500),  # Allow some buffer
                temperature=0.3  # Lower temperature for more consistent summaries
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure summary isn't too long and add quality scoring
            summary = self._enforce_word_limit(summary, max_length)
            quality_score = self._score_summary_quality(summary)
            
            logger.debug(
                "AI summary generated",
                word_count=len(summary.split()),
                quality_score=quality_score,
                participant_id=conversation.participant_id
            )
            
            return summary
            
        except Exception as e:
            logger.error("AI summarization failed", error=str(e))
            return self._fallback_summarize(conversation, max_length)
    
    def _fallback_summarize(self, conversation: Conversation, max_length: int) -> str:
        """Generate a basic summary without AI when API is unavailable.
        
        Args:
            conversation: Conversation to summarize.
            max_length: Maximum summary length (simplified for fallback).
            
        Returns:
            Basic summary based on message analysis.
        """
        try:
            participant_name = (
                conversation.participant.username 
                if conversation.participant 
                else f"User {conversation.participant_id}"
            )
            
            message_count = len(conversation.messages)
            
            if message_count == 0:
                return f"No messages with {participant_name}"
            
            # Get date range
            messages = conversation.get_messages_chronological()
            start_date = messages[0].created_at.strftime("%Y-%m-%d")
            end_date = messages[-1].created_at.strftime("%Y-%m-%d")
            
            date_range = start_date if start_date == end_date else f"{start_date} to {end_date}"
            
            # Calculate basic stats
            total_chars = sum(len(msg.text) for msg in messages if msg.text)
            avg_message_length = total_chars // message_count if message_count > 0 else 0
            
            # Analyze message content for key topics
            message_texts = [msg.text.lower() for msg in messages if msg.text]
            all_text = " ".join(message_texts)
            
            # Look for key topic indicators
            topic_indicators = {
                'work/project': ['project', 'work', 'meeting', 'deadline', 'task', 'client'],
                'collaboration': ['collaborate', 'partner', 'team', 'together', 'joint'],
                'planning': ['plan', 'schedule', 'when', 'where', 'time', 'date'],
                'business': ['business', 'deal', 'proposal', 'contract', 'opportunity'],
                'technical': ['code', 'github', 'api', 'database', 'bug', 'feature'],
                'social': ['event', 'party', 'dinner', 'coffee', 'hang out', 'meet up']
            }
            
            identified_topics = []
            for topic, keywords in topic_indicators.items():
                if any(keyword in all_text for keyword in keywords):
                    identified_topics.append(topic)
            
            # Generate focused summary
            if identified_topics:
                topic_str = ", ".join(identified_topics[:2])  # Max 2 topics
                summary = f"Conversation with {participant_name} about {topic_str}"
            else:
                summary = f"General conversation with {participant_name}"
            
            # Add meaningful details
            summary += f" ({message_count} messages, {date_range})"
            
            # Look for actionable content indicators
            action_keywords = ['agreed', 'decided', 'planned', 'scheduled', 'will', 'going to', 'next']
            if any(keyword in all_text for keyword in action_keywords):
                summary += ". Contains agreements or planned actions"
            
            return summary
            
        except Exception as e:
            logger.error("Fallback summarization failed", error=str(e))
            return f"Unable to summarize conversation with {conversation.participant_id}"
    
    def _prepare_conversation_text(self, conversation: Conversation) -> str:
        """Prepare conversation text for AI processing.
        
        Args:
            conversation: Conversation to process.
            
        Returns:
            Formatted conversation text with low-value messages filtered out.
        """
        messages = conversation.get_messages_chronological()
        
        # Limit to recent messages if conversation is very long
        if len(messages) > 50:
            messages = messages[-50:]  # Last 50 messages
        
        # Filter out low-value messages
        substantive_messages = self._filter_substantive_messages(messages)
        
        conversation_lines = []
        for msg in substantive_messages:
            if msg.text:  # Only include messages with text content
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
                sender = "User" if msg.sender_id == conversation.participant_id else "Me"
                conversation_lines.append(f"[{timestamp}] {sender}: {msg.text}")
        
        return "\n".join(conversation_lines)
    
    def _filter_substantive_messages(self, messages: List[Message]) -> List[Message]:
        """Filter out low-value messages that don't contribute to key information.
        
        Args:
            messages: List of messages to filter.
            
        Returns:
            List of messages with substantive content only.
        """
        import re
        
        # Patterns for low-value messages to exclude
        low_value_patterns = [
            r'^(hi|hey|hello|thanks?|thank you|thx|ok|okay|sure|yes|no|yep|nope)\.?!?$',
            r'^(lol|haha|hehe|😂|😊|👍|👎|❤️|🎉|✅)+$',  # Just emojis/reactions
            r'^.{1,3}$',  # Very short messages (1-3 chars)
            r'^(good|nice|cool|awesome|great)\.?!?$',  # Simple reactions
            r'^(morning|afternoon|evening|night)\.?!?$',  # Time greetings
        ]
        
        substantive_messages = []
        
        for msg in messages:
            if not msg.text:
                continue
                
            text = msg.text.strip().lower()
            
            # Skip if it matches low-value patterns
            is_low_value = any(re.match(pattern, text, re.IGNORECASE) for pattern in low_value_patterns)
            
            # Keep messages that are longer and likely substantive
            if not is_low_value and len(text) > 5:
                substantive_messages.append(msg)
            # Also keep very short messages if they contain key indicators
            elif any(keyword in text for keyword in ['meet', 'plan', 'when', 'where', 'how', 'what', 'project', 'work', 'call']):
                substantive_messages.append(msg)
        
        # If we filtered out too much, keep the original messages
        if len(substantive_messages) < max(3, len(messages) * 0.3):
            return messages
        
        return substantive_messages
    
    def _enforce_word_limit(self, summary: str, max_length: int) -> str:
        """Enforce word limit on summary with intelligent truncation.
        
        Args:
            summary: The summary text to potentially truncate.
            max_length: Maximum allowed words.
            
        Returns:
            Summary truncated to word limit if necessary.
        """
        words = summary.split()
        
        if len(words) <= max_length:
            return summary
        
        # Try to truncate at sentence boundaries first
        truncated = " ".join(words[:max_length-3])
        
        # Find the last complete sentence
        last_period = truncated.rfind('.')
        last_bullet = truncated.rfind('•')
        last_sentence_end = max(last_period, last_bullet)
        
        if last_sentence_end > len(truncated) * 0.7:  # If we can keep 70%+ of content
            return truncated[:last_sentence_end + 1] + "..."
        else:
            return truncated + "..."
    
    def _score_summary_quality(self, summary: str) -> int:
        """Score summary quality based on presence of key information indicators.
        
        Args:
            summary: The summary text to score.
            
        Returns:
            Quality score (higher is better).
        """
        summary_lower = summary.lower()
        
        # Key information indicators (weighted by importance)
        quality_indicators = {
            # High value (3 points each)
            'decision': 3, 'agreed': 3, 'planned': 3, 'deadline': 3,
            'meeting': 3, 'action': 3, 'committed': 3, 'scheduled': 3,
            
            # Medium value (2 points each)  
            'discussed': 2, 'recommended': 2, 'shared': 2, 'proposal': 2,
            'next steps': 2, 'follow up': 2, 'collaborate': 2,
            
            # Lower value (1 point each)
            'mentioned': 1, 'talked about': 1, 'brought up': 1,
        }
        
        score = 0
        for indicator, weight in quality_indicators.items():
            if indicator in summary_lower:
                score += weight
        
        # Bonus points for specific formatting that indicates actionable content
        if '•' in summary or '-' in summary:  # Bullet points
            score += 2
        if any(char.isdigit() for char in summary):  # Contains numbers (dates, times, etc.)
            score += 1
        
        return score
    
    def _build_summarization_prompt(
        self, 
        conversation_text: str, 
        max_length: int,
        context: str,
        message_count: int
    ) -> str:
        """Build the prompt for AI summarization.
        
        Args:
            conversation_text: Formatted conversation text.
            max_length: Maximum summary length in words.
            context: Additional context about the conversation.
            message_count: Total number of messages in conversation.
            
        Returns:
            Formatted prompt for AI model.
        """
        prompt = f"""Summarize this Twitter DM conversation in {max_length} words or less, focusing on KEY INFORMATION ONLY.

{context}Total messages: {message_count}

PRIORITIZATION GUIDELINES (in order of importance):
1. DECISIONS MADE: Any agreements, plans, or conclusions reached
2. ACTION ITEMS: Tasks, commitments, or next steps mentioned
3. KEY TOPICS: Main subjects discussed (business, personal, project, etc.)
4. IMPORTANT DATES/EVENTS: Specific meetings, deadlines, or events
5. VALUABLE INSIGHTS: Useful information, recommendations, or resources shared

FILTERING RULES:
- EXCLUDE: Greetings, small talk, "thanks", casual banter
- EXCLUDE: Personal details, addresses, phone numbers, sensitive info
- INCLUDE ONLY: Substantive content that would be useful to remember
- If mostly casual chat, simply state: "Casual conversation about [topic]"

FORMAT: Write in concise bullet points or short sentences. Be specific and actionable.

Conversation:
{conversation_text}

KEY SUMMARY:"""

        return prompt
    
    def get_conversation_topics(self, conversation: Conversation) -> List[str]:
        """Extract main topics from a conversation (if AI is available).
        
        Args:
            conversation: Conversation to analyze.
            
        Returns:
            List of identified topics/themes.
        """
        if not self.client or not conversation.messages:
            return ["Topic extraction unavailable"]
        
        try:
            messages_text = self._prepare_conversation_text(conversation)
            
            prompt = f"""Analyze this conversation and identify the main topics or themes discussed. Return only a simple list of topics, one per line.

Conversation:
{messages_text}

Topics:"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that identifies conversation topics."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            topics_text = response.choices[0].message.content.strip()
            topics = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
            
            return topics[:5]  # Return max 5 topics
            
        except Exception as e:
            logger.error("Topic extraction failed", error=str(e))
            return ["Topic extraction failed"]


# Global summarizer instance
conversation_summarizer = ConversationSummarizer()
