#!/usr/bin/env python3
"""Test script for real X API v2 DM access.

This script will test your actual DM access and process real conversations.
"""

import sys
from pathlib import Path
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.client import x_client
from src.twitter.dm_fetcher import DMFetcher
from src.summarizer.conversation_summarizer import conversation_summarizer
from src.google_sheets.formatter import SheetsFormatter
from src.google_sheets.client import sheets_client

# Configure logging
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


def test_dm_access():
    """Test basic DM API access."""
    logger.info("🔍 Testing X API v2 DM access...")
    
    try:
        dm_fetcher = DMFetcher(x_client)
        
        # Test 1: Discover recent conversation participants
        logger.info("Step 1: Discovering recent DM participants...")
        participants = dm_fetcher.get_recent_dm_participants(max_results=5)
        
        if not participants:
            logger.warning("No recent DM participants found. This could mean:")
            logger.warning("  1. You don't have recent DMs")
            logger.warning("  2. API permissions need adjustment")
            logger.warning("  3. Rate limits or other API issues")
            return False
        
        logger.info(f"✓ Found {len(participants)} recent participants: {participants}")
        
        # Test 2: Fetch profile info for first participant
        test_participant = participants[0]
        logger.info(f"Step 2: Testing profile fetch for participant: {test_participant}")
        
        user_profile = dm_fetcher._get_user_info(test_participant)
        logger.info("✓ Profile fetch successful")
        logger.info(f"  Username: @{user_profile.username}")
        logger.info(f"  Real Name: {user_profile.name}")
        logger.info(f"  LinkedIn: {user_profile.linkedin_url or 'None found'}")
        
        # Test 3: Try to fetch actual conversation
        logger.info(f"Step 3: Testing conversation fetch...")
        conversation = dm_fetcher.fetch_conversation_with_user(
            test_participant, 
            max_results=10
        )
        
        logger.info(f"✓ Conversation fetch completed")
        logger.info(f"  Messages found: {len(conversation.messages)}")
        logger.info(f"  Participant: {conversation.participant.name if conversation.participant else 'Unknown'}")
        
        if len(conversation.messages) > 0:
            logger.info("Step 4: Testing summarization...")
            summary = conversation_summarizer.summarize_conversation(conversation, max_length=100)
            logger.info(f"✓ Summary generated: {summary[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error("DM access test failed", error=str(e))
        return False


def run_mini_workflow():
    """Run a mini version of the full workflow with your most recent conversation."""
    logger.info("🚀 Running mini workflow with real data...")
    
    try:
        dm_fetcher = DMFetcher(x_client)
        
        # Get recent participants
        participants = dm_fetcher.get_recent_dm_participants(max_results=3)
        if not participants:
            logger.error("No participants found to test with")
            return False
        
        logger.info(f"Processing {len(participants)} recent conversations...")
        
        # Process conversations
        conversations_data = []
        for i, participant_id in enumerate(participants):
            logger.info(f"Processing conversation {i+1}/{len(participants)}...")
            
            try:
                # Fetch conversation
                conversation = dm_fetcher.fetch_conversation_with_user(
                    participant_id, 
                    max_results=20
                )
                
                if len(conversation.messages) == 0:
                    logger.warning(f"No messages found for participant {participant_id}")
                    continue
                
                # Generate summary
                summary = conversation_summarizer.summarize_conversation(
                    conversation, 
                    max_length=150
                )
                
                # Format for sheets
                formatter = SheetsFormatter()
                formatted_data = formatter.format_conversation_for_sheets(conversation)
                conversations_data.append(formatted_data)
                
                logger.info(f"✓ Processed conversation with @{conversation.participant.username}")
                
            except Exception as e:
                logger.error(f"Failed to process participant {participant_id}", error=str(e))
                continue
        
        if not conversations_data:
            logger.warning("No conversations were successfully processed")
            return False
        
        # Show results
        logger.info("📊 Processed Conversations Summary:")
        for data in conversations_data:
            logger.info(f"  @{data['username']} ({data['real_name']}) - {data['message_count']} messages")
            if data['linkedin_url']:
                logger.info(f"    LinkedIn: {data['linkedin_url']}")
            logger.info(f"    Summary: {data['conversation_summary'][:100]}...")
        
        # Ask about writing to Google Sheets
        write_to_sheets = input(f"\nWrite {len(conversations_data)} conversations to Google Sheets? (y/n): ").lower().strip()
        
        if write_to_sheets == 'y':
            logger.info("Writing to Google Sheets...")
            sheets_client.connect_to_sheet()
            sheets_client.setup_headers()
            sheets_client.write_conversations(conversations_data)
            logger.info("✅ Successfully written to Google Sheets!")
        else:
            logger.info("Skipped writing to Google Sheets")
        
        return True
        
    except Exception as e:
        logger.error("Mini workflow failed", error=str(e))
        return False


def main():
    """Main function for testing real DM access."""
    print("🐦 Real X API v2 DM Testing")
    print("=" * 50)
    print("This will test your actual DM access and process real conversations.")
    print("Make sure you have:")
    print("✓ X API v2 access with DM permissions")
    print("✓ Valid API credentials in .env")
    print("✓ Google Sheets configured")
    print("=" * 50)
    
    # Verify credentials first
    try:
        user_info = x_client.verify_credentials()
        logger.info(f"✓ Authenticated as @{user_info['username']} ({user_info['name']})")
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        return
    
    # Choose test type
    print("\nWhat would you like to test?")
    print("1. Basic DM access test (safe)")
    print("2. Mini workflow with real conversations")
    print("3. Both")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        logger.info("Running basic DM access test...")
        basic_success = test_dm_access()
        if basic_success:
            logger.info("✅ Basic DM access test passed!")
        else:
            logger.error("❌ Basic DM access test failed")
            if choice == '1':
                return
    
    if choice in ['2', '3']:
        logger.info("Running mini workflow...")
        workflow_success = run_mini_workflow()
        if workflow_success:
            logger.info("✅ Mini workflow completed successfully!")
        else:
            logger.error("❌ Mini workflow failed")
    
    logger.info("🎉 Testing complete!")


if __name__ == "__main__":
    main()
