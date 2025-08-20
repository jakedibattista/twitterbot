#!/usr/bin/env python3
"""Get your own Twitter user info and test user profile fetching."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.client import x_client
from src.twitter.dm_fetcher import DMFetcher
import structlog

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


def get_my_user_info():
    """Get your own Twitter user information."""
    logger.info("Getting your Twitter user information...")
    
    try:
        # Get your own user info
        user_info = x_client.verify_credentials()
        
        print("\n" + "="*50)
        print("🐦 YOUR TWITTER PROFILE INFO")
        print("="*50)
        print(f"User ID: {user_info['id']}")
        print(f"Username: @{user_info['username']}")
        print(f"Name: {user_info['name']}")
        print(f"Followers: {user_info.get('public_metrics', {}).get('followers_count', 'N/A')}")
        print(f"Following: {user_info.get('public_metrics', {}).get('following_count', 'N/A')}")
        print("="*50)
        
        return user_info
        
    except Exception as e:
        logger.error("Failed to get user info", error=str(e))
        return None


def test_user_profile_fetching(target_user_id: str):
    """Test fetching profile information for a specific user."""
    logger.info(f"Testing profile fetch for user ID: {target_user_id}")
    
    try:
        dm_fetcher = DMFetcher(x_client)
        user_profile = dm_fetcher._get_user_info(target_user_id)
        
        print("\n" + "="*50)
        print("👤 FETCHED USER PROFILE")
        print("="*50)
        print(f"User ID: {user_profile.id}")
        print(f"Username: @{user_profile.username}")
        print(f"Real Name: {user_profile.name}")
        print(f"Bio: {user_profile.description or 'No bio'}")
        print(f"Location: {user_profile.location or 'No location'}")
        print(f"Website: {user_profile.url or 'No website'}")
        print(f"Verified: {'✓' if user_profile.verified else '✗'}")
        print(f"LinkedIn (extracted): {user_profile.linkedin_url or 'None found'}")
        print("="*50)
        
        # Test Google Sheets formatting
        from src.google_sheets.formatter import SheetsFormatter
        from src.twitter.models import Conversation
        
        # Create a mock conversation for formatting test
        conversation = Conversation(participant_id=user_profile.id, participant=user_profile)
        conversation.summary = "Test conversation summary"
        conversation.total_message_count = 5
        conversation.last_message_time = None
        
        formatted_data = SheetsFormatter.format_conversation_for_sheets(conversation)
        
        print("\n📊 GOOGLE SHEETS FORMAT PREVIEW:")
        print("-" * 30)
        for key, value in formatted_data.items():
            print(f"{key}: {value}")
        print("-" * 30)
        
        return user_profile
        
    except Exception as e:
        logger.error("Failed to fetch user profile", error=str(e))
        return None


def main():
    """Main function to test user info fetching."""
    print("🧪 Twitter User Profile Testing")
    print("This will test the enhanced profile fetching with LinkedIn discovery")
    
    # Get your own info first
    my_info = get_my_user_info()
    if not my_info:
        print("❌ Failed to get your user info. Check your API credentials.")
        return
    
    # Ask for a user ID to test profile fetching
    print(f"\nYour User ID: {my_info['id']}")
    print("\nTo test profile fetching, you can:")
    print("1. Use your own ID (enter 'me')")
    print("2. Enter another Twitter user ID")
    print("3. Leave blank to skip profile testing")
    
    user_input = input("\nEnter user ID to test (or 'me' for yourself): ").strip()
    
    if user_input.lower() == 'me':
        target_id = my_info['id']
    elif user_input:
        target_id = user_input
    else:
        print("Skipping profile test.")
        return
    
    # Test profile fetching
    profile = test_user_profile_fetching(target_id)
    
    if profile:
        print("\n✅ Profile fetching test successful!")
        print("The enhanced profile data includes:")
        print("  • Real name extraction")
        print("  • LinkedIn URL discovery") 
        print("  • Location and bio capture")
        print("  • Verification status")
        print("  • Google Sheets formatting")
    else:
        print("\n❌ Profile fetching test failed.")


if __name__ == "__main__":
    main()
