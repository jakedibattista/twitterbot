"""Main orchestration script for Twitter DM to Google Sheets organizer.

This script coordinates the entire workflow:
1. Authenticate with X API and Google Sheets
2. Fetch DM conversations
3. Generate AI summaries
4. Write organized data to Google Sheets
"""

import sys
import structlog
import logging
from pathlib import Path
from typing import List, Optional
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from twitter.client import x_client
from twitter.dm_fetcher import DMFetcher
from twitter.models import ConversationBatch
from google_sheets.client import sheets_client
from google_sheets.formatter import SheetsFormatter
from summarizer.conversation_summarizer import conversation_summarizer
from linkedin_ai_discovery import ai_linkedin_discovery

# Configure structured logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class TwitterDMOrganizer:
    """Main orchestrator for the Twitter DM to Google Sheets workflow."""
    
    def __init__(self):
        """Initialize the organizer with all required clients."""
        self.dm_fetcher = DMFetcher(x_client)
        self.sheets_formatter = SheetsFormatter()
        
    def run_full_workflow(
        self,
        participant_ids: List[str],
        max_messages_per_conversation: int = 100,
        generate_summaries: bool = True,
        clear_existing_data: bool = False,
        since_days: Optional[int] = None,
        enrich_linkedin: bool = False,
        enrich_limit: int = 0
    ) -> bool:
        """Run the complete workflow from DM fetching to Google Sheets.
        
        Args:
            participant_ids: List of user IDs to fetch conversations with.
            max_messages_per_conversation: Maximum messages to fetch per conversation.
            generate_summaries: Whether to generate AI summaries.
            clear_existing_data: Whether to clear existing sheet data first.
            
        Returns:
            True if workflow completed successfully, False otherwise.
        """
        logger.info(
            "Starting Twitter DM organization workflow",
            participant_count=len(participant_ids),
            max_messages=max_messages_per_conversation,
            summaries_enabled=generate_summaries
        )
        
        try:
            # Step 1: Verify all credentials and connections
            if not self._verify_setup():
                return False
            
            # Step 2: Fetch DM conversations
            logger.info("Step 2: Fetching DM conversations...")
            conversation_batch = self._fetch_conversations(
                participant_ids, 
                max_messages_per_conversation,
                since_days
            )
            
            if not conversation_batch or len(conversation_batch.conversations) == 0:
                logger.warning("No conversations fetched. Exiting.")
                return False
            
            # Step 3: Generate summaries (if enabled)
            if generate_summaries:
                logger.info("Step 3: Generating conversation summaries...")
                conversation_batch = self._generate_summaries(conversation_batch)
            else:
                logger.info("Step 3: Skipping summary generation (disabled)")
            
            # Optional: Enrich with LinkedIn discovery for missing links
            if enrich_linkedin and enrich_limit != 0:
                logger.info("Step 4: Enriching with LinkedIn discovery...")
                formatted_preview = self.sheets_formatter.format_conversations_batch(conversation_batch)
                users_to_enrich = [
                    {
                        "username": item.get("username", ""),
                        "real_name": item.get("real_name", ""),
                        "bio": item.get("bio", ""),
                        "location": item.get("location", ""),
                        "website": item.get("website", ""),
                    }
                    for item in formatted_preview
                    if not item.get("linkedin_url")
                ]
                if enrich_limit > 0:
                    users_to_enrich = users_to_enrich[:enrich_limit]
                if users_to_enrich:
                    enriched = ai_linkedin_discovery.bulk_discover_linkedin(users_to_enrich)
                    # Merge back later by username
                    enrichment_by_username = {e["username"]: e for e in enriched}
                else:
                    enrichment_by_username = {}
            else:
                enrichment_by_username = {}

            # Step 4: Prepare data for Google Sheets
            logger.info("Step 5: Formatting data for Google Sheets...")
            formatted_data = self._format_for_sheets(conversation_batch)
            # Merge enrichment
            if enrichment_by_username:
                for item in formatted_data:
                    enrich = enrichment_by_username.get(item.get("username"))
                    if enrich and enrich.get("ai_linkedin_url") and not item.get("linkedin_url"):
                        item["linkedin_url"] = enrich.get("ai_linkedin_url")
                        item["linkedin_confidence"] = enrich.get("linkedin_confidence")
            
            # Step 5: Write to Google Sheets
            logger.info("Step 6: Writing to Google Sheets...")
            if not self._write_to_sheets(formatted_data, clear_existing_data):
                return False
            
            # Step 6: Generate and log summary statistics
            stats = self.sheets_formatter.create_summary_statistics(conversation_batch)
            self._log_completion_stats(stats)
            
            logger.info("🎉 Workflow completed successfully!")
            return True
            
        except Exception as e:
            logger.error("Workflow failed with unexpected error", error=str(e))
            return False
    
    def _verify_setup(self) -> bool:
        """Verify all API credentials and connections.
        
        Returns:
            True if all verifications pass, False otherwise.
        """
        logger.info("Step 1: Verifying setup...")
        
        try:
            # Verify X API credentials
            user_info = x_client.verify_credentials()
            logger.info("✓ X API authentication successful", username=user_info["username"])
            
            # Verify Google Sheets access
            worksheet = sheets_client.connect_to_sheet()
            sheets_client.setup_headers()
            logger.info("✓ Google Sheets access verified")
            
            # Check if AI summarization is available
            if conversation_summarizer.client:
                logger.info("✓ AI summarization available (OpenAI)")
            else:
                logger.warning("⚠ AI summarization not available (using fallback method)")
            
            return True
            
        except Exception as e:
            logger.error("Setup verification failed", error=str(e))
            return False
    
    def _fetch_conversations(
        self, 
        participant_ids: List[str], 
        max_messages: int,
        since_days: Optional[int]
    ) -> Optional[ConversationBatch]:
        """Fetch conversations from X API.
        
        Args:
            participant_ids: List of user IDs to fetch conversations with.
            max_messages: Maximum messages per conversation.
            
        Returns:
            ConversationBatch with fetched conversations or None if failed.
        """
        try:
            conversation_batch = self.dm_fetcher.fetch_multiple_conversations(
                participant_ids, 
                max_messages,
                since_days
            )
            
            logger.info(
                "Conversations fetched",
                successful=len(conversation_batch.conversations),
                total_requested=len(participant_ids)
            )
            
            return conversation_batch
            
        except Exception as e:
            logger.error("Failed to fetch conversations", error=str(e))
            return None
    
    def _generate_summaries(self, batch: ConversationBatch) -> ConversationBatch:
        """Generate AI summaries for all conversations.
        
        Args:
            batch: ConversationBatch to process.
            
        Returns:
            Updated batch with summaries.
        """
        try:
            return conversation_summarizer.summarize_batch(batch)
        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            # Continue with batch even if summarization fails
            return batch
    
    def _format_for_sheets(self, batch: ConversationBatch) -> List[dict]:
        """Format conversation data for Google Sheets.
        
        Args:
            batch: ConversationBatch to format.
            
        Returns:
            List of formatted conversation dictionaries.
        """
        try:
            formatted_data = self.sheets_formatter.format_conversations_batch(batch)
            validated_data = self.sheets_formatter.validate_sheet_data(formatted_data)
            sorted_data = self.sheets_formatter.sort_conversations(
                validated_data, 
                sort_by="last_message_date", 
                reverse=True
            )
            
            logger.info("Data formatted for sheets", count=len(sorted_data))
            return sorted_data
            
        except Exception as e:
            logger.error("Data formatting failed", error=str(e))
            raise
    
    def _write_to_sheets(self, data: List[dict], clear_existing: bool) -> bool:
        """Write formatted data to Google Sheets.
        
        Args:
            data: Formatted conversation data.
            clear_existing: Whether to clear existing data first.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if clear_existing:
                logger.info("Clearing existing sheet data...")
                sheets_client.clear_sheet()
                sheets_client.setup_headers()
            
            if data:
                sheets_client.write_conversations(data)
                logger.info("Data written to Google Sheets successfully")
            else:
                logger.warning("No data to write to sheets")
            
            return True
            
        except Exception as e:
            logger.error("Failed to write to Google Sheets", error=str(e))
            return False
    
    def _log_completion_stats(self, stats: dict) -> None:
        """Log completion statistics.
        
        Args:
            stats: Statistics dictionary from sheets formatter.
        """
        logger.info(
            "Workflow Statistics",
            total_conversations=stats["total_conversations"],
            total_messages=stats["total_messages"],
            avg_messages_per_conversation=stats["average_messages_per_conversation"],
            summarized_conversations=stats["conversations_with_summaries"],
            completion_rate=f"{stats['summary_completion_rate']}%"
        )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Organize Twitter DMs into Google Sheets with AI summaries"
    )
    
    parser.add_argument(
        "--participant-ids",
        type=str,
        nargs="+",
        required=True,
        help="User IDs to fetch conversations with (space-separated)"
    )
    
    parser.add_argument(
        "--max-messages",
        type=int,
        default=100,
        help="Maximum messages per conversation (default: 100)"
    )
    
    parser.add_argument(
        "--no-summaries",
        action="store_true",
        help="Skip AI summary generation"
    )
    
    parser.add_argument(
        "--clear-sheet",
        action="store_true",
        help="Clear existing sheet data before writing"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run verification only, don't fetch or write data"
    )

    parser.add_argument(
        "--since-days",
        type=int,
        default=None,
        help="Only fetch messages from the last N days"
    )

    parser.add_argument(
        "--discover-recent",
        type=int,
        default=None,
        help="Discover and use N recent DM participants instead of providing IDs"
    )

    parser.add_argument(
        "--enrich-linkedin",
        action="store_true",
        help="Attempt AI LinkedIn discovery for users missing LinkedIn URLs"
    )

    parser.add_argument(
        "--enrich-limit",
        type=int,
        default=0,
        help="Limit number of users to enrich with AI (0 for all missing)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    try:
        args = parse_arguments()
        
        organizer = TwitterDMOrganizer()
        
        if args.dry_run:
            logger.info("Running dry-run verification only...")
            success = organizer._verify_setup()
            if success:
                logger.info("✓ Dry run completed successfully - all systems ready")
            else:
                logger.error("✗ Dry run failed - check configuration")
            return 0 if success else 1
        
        # Optionally discover recent participants
        participant_ids = args.participant_ids
        if args.discover_recent:
            ids = organizer.dm_fetcher.get_recent_dm_participants(max_results=args.discover_recent)
            if ids:
                participant_ids = ids

        # Run full workflow
        success = organizer.run_full_workflow(
            participant_ids=participant_ids,
            max_messages_per_conversation=args.max_messages,
            generate_summaries=not args.no_summaries,
            clear_existing_data=args.clear_sheet,
            since_days=args.since_days,
            enrich_linkedin=args.enrich_linkedin,
            enrich_limit=args.enrich_limit
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        return 130
    except Exception as e:
        logger.error("Unexpected error in main", error=str(e))
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
