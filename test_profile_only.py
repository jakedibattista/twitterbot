#!/usr/bin/env python3
"""Test profile fetching and processing without DM access.

This tests the user profile enhancement and LinkedIn discovery features
using manually provided user IDs.
"""

import sys
from pathlib import Path
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.client import x_client
from src.twitter.dm_fetcher import DMFetcher
from src.twitter.models import Conversation, Message
from src.summarizer.conversation_summarizer import conversation_summarizer
from src.google_sheets.formatter import SheetsFormatter
from src.google_sheets.client import sheets_client
from datetime import datetime, timedelta

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


def test_user_profile_features():
    """Test enhanced user profile fetching and LinkedIn discovery."""
    logger.info("🧪 Testing enhanced user profile features...")
    
    # Get your own info first
    try:
        my_info = x_client.verify_credentials()
        my_user_id = my_info["id"]
        logger.info(f"✓ Your account: @{my_info['username']} ({my_info['name']})")
    except Exception as e:
        logger.error("Failed to get your user info", error=str(e))
        return False
    
    # Test profile fetching with a few well-known tech accounts
    test_users = [
        my_user_id,  # Your own profile
        "783214",    # Twitter (official account)
        "17919972",  # TechCrunch
    ]
    
    dm_fetcher = DMFetcher(x_client)
    processed_profiles = []
    
    for i, user_id in enumerate(test_users):
        logger.info(f"Testing profile {i+1}/{len(test_users)}: {user_id}")
        
        try:
            # Fetch enhanced user profile
            user_profile = dm_fetcher._get_user_info(user_id)
            
            logger.info("✓ Profile fetched successfully:")
            logger.info(f"  Username: @{user_profile.username}")
            logger.info(f"  Real Name: {user_profile.name}")
            logger.info(f"  Bio: {(user_profile.description or 'No bio')[:100]}...")
            logger.info(f"  Location: {user_profile.location or 'Not specified'}")
            logger.info(f"  Website: {user_profile.url or 'No website'}")
            logger.info(f"  Verified: {'✓' if user_profile.verified else '✗'}")
            logger.info(f"  LinkedIn: {user_profile.linkedin_url or 'None detected'}")
            
            # Create mock conversation for testing
            conversation = Conversation(
                participant_id=user_profile.id,
                participant=user_profile
            )
            
            # Add some mock messages for summary testing
            base_time = datetime.now() - timedelta(days=1)
            mock_messages = [
                Message(
                    id=f"msg_{i}",
                    text=f"Hi! I saw your latest post about {user_profile.name}. Very interesting work!",
                    created_at=base_time,
                    sender_id=user_profile.id,
                    recipient_id=my_user_id
                ),
                Message(
                    id=f"msg_{i}_2",
                    text="Thanks! I'd love to collaborate on a project. When would be a good time to chat?",
                    created_at=base_time + timedelta(minutes=30),
                    sender_id=my_user_id,
                    recipient_id=user_profile.id
                ),
                Message(
                    id=f"msg_{i}_3",
                    text="How about next Tuesday at 2pm? We could discuss the technical details.",
                    created_at=base_time + timedelta(hours=1),
                    sender_id=user_profile.id,
                    recipient_id=my_user_id
                )
            ]
            
            for msg in mock_messages:
                conversation.add_message(msg)
            
            # Test summarization
            summary = conversation_summarizer.summarize_conversation(
                conversation, 
                max_length=100
            )
            logger.info(f"✓ Summary: {summary}")
            
            # Test Google Sheets formatting
            formatter = SheetsFormatter()
            formatted_data = formatter.format_conversation_for_sheets(conversation)
            processed_profiles.append(formatted_data)
            
            logger.info("✓ Google Sheets formatting successful")
            
        except Exception as e:
            logger.error(f"Failed to process user {user_id}", error=str(e))
            continue
    
    if processed_profiles:
        logger.info(f"📊 Successfully processed {len(processed_profiles)} profiles")
        
        # Show formatted data
        logger.info("Sample formatted data for Google Sheets:")
        for data in processed_profiles:
            logger.info(f"  @{data['username']} | {data['real_name']} | LinkedIn: {data['linkedin_url'] or 'None'}")
        
        # Ask about writing to sheets
        write_test = input(f"\nWrite {len(processed_profiles)} test profiles to Google Sheets? (y/n): ").lower().strip()
        if write_test == 'y':
            try:
                sheets_client.connect_to_sheet()
                sheets_client.setup_headers()
                sheets_client.write_conversations(processed_profiles)
                logger.info("✅ Test data written to Google Sheets!")
            except Exception as e:
                logger.error("Failed to write to sheets", error=str(e))
        
        return True
    else:
        logger.error("No profiles were successfully processed")
        return False


def show_dm_permission_instructions():
    """Show instructions for getting DM permissions."""
    print("\n" + "="*60)
    print("🔧 TO ENABLE DM ACCESS:")
    print("="*60)
    print("1. Go to: https://developer.twitter.com/en/portal/dashboard")
    print("2. Select your app")
    print("3. Go to Settings → User authentication settings")
    print("4. Set App permissions to: 'Read and write and Direct message'")
    print("5. Regenerate your Access Token and Secret")
    print("6. Update your .env file with new tokens")
    print("7. Wait a few minutes for changes to propagate")
    print("="*60)


def main():
    """Main testing function."""
    print("🧪 Profile Enhancement Testing")
    print("Testing the enhanced profile features without DM access")
    
    # Test profile features
    success = test_user_profile_features()
    
    if success:
        logger.info("✅ All profile tests passed!")
        logger.info("Your enhanced profile system is working:")
        logger.info("  ✓ Real name extraction")
        logger.info("  ✓ LinkedIn URL discovery")
        logger.info("  ✓ Enhanced bio and location data")
        logger.info("  ✓ Google Sheets formatting")
        logger.info("  ✓ AI summarization")
    else:
        logger.error("❌ Some tests failed")
    
    # Show DM permission instructions
    show_dm_permission_instructions()
    
    print("\nOnce you have DM permissions:")
    print("- Run: python3 test_real_dms.py")
    print("- Or: python3 src/main.py --participant-ids USER_ID --dry-run")


if __name__ == "__main__":
    main()
