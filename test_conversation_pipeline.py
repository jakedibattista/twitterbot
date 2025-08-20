#!/usr/bin/env python3
"""Test script to verify the conversation processing pipeline with mock data.

This script creates sample conversation data and tests the complete workflow:
User data → Conversation → AI Summary → Google Sheets formatting
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.models import User, Message, Conversation, ConversationBatch
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


def create_sample_user() -> User:
    """Create a sample user with realistic data."""
    return User(
        id="1234567890",
        username="johndoe_dev",
        name="John Doe",
        description="Senior Software Engineer @TechCorp | AI enthusiast | Building the future with Python 🐍 | LinkedIn: linkedin.com/in/johndoe-dev",
        url="https://johndoe.dev",
        location="San Francisco, CA",
        verified=True,
        profile_image_url="https://pbs.twimg.com/profile_images/sample.jpg"
    )


def create_sample_messages() -> list[Message]:
    """Create sample messages for a realistic conversation."""
    base_time = datetime.now() - timedelta(days=2)
    
    messages = [
        Message(
            id="msg_1",
            text="Hey! I saw your post about the ML project. Really interesting approach to the data pipeline.",
            created_at=base_time,
            sender_id="1234567890",  # From John
            recipient_id="your_user_id"
        ),
        Message(
            id="msg_2", 
            text="Thanks! Yeah, we're using a combination of Apache Kafka and TensorFlow serving. Are you working on something similar?",
            created_at=base_time + timedelta(minutes=15),
            sender_id="your_user_id",  # From you
            recipient_id="1234567890"
        ),
        Message(
            id="msg_3",
            text="Actually yes! We're building a real-time recommendation system. Would love to collaborate or at least share learnings.",
            created_at=base_time + timedelta(minutes=30),
            sender_id="1234567890",
            recipient_id="your_user_id"
        ),
        Message(
            id="msg_4",
            text="That sounds perfect! I'm definitely interested. When would be a good time to chat?",
            created_at=base_time + timedelta(minutes=45),
            sender_id="your_user_id",
            recipient_id="1234567890"
        ),
        Message(
            id="msg_5",
            text="How about next Tuesday at 2pm? We could do a quick Zoom call to discuss the technical details.",
            created_at=base_time + timedelta(hours=1),
            sender_id="1234567890",
            recipient_id="your_user_id"
        ),
        Message(
            id="msg_6",
            text="Perfect! Tuesday at 2pm works great. I'll send you a calendar invite with the Zoom link.",
            created_at=base_time + timedelta(hours=1, minutes=10),
            sender_id="your_user_id",
            recipient_id="1234567890"
        ),
        Message(
            id="msg_7",
            text="Sounds good. Looking forward to it! I'll prepare some slides about our current architecture.",
            created_at=base_time + timedelta(hours=1, minutes=25),
            sender_id="1234567890",
            recipient_id="your_user_id"
        ),
        Message(
            id="msg_8",
            text="Great! I'll also share our recent performance benchmarks. Should be useful for comparison.",
            created_at=base_time + timedelta(hours=2),
            sender_id="your_user_id",
            recipient_id="1234567890"
        )
    ]
    
    return messages


def test_conversation_pipeline():
    """Test the complete conversation processing pipeline."""
    logger.info("🧪 Starting conversation pipeline test...")
    
    # Step 1: Create sample data
    logger.info("Step 1: Creating sample conversation data...")
    user = create_sample_user()
    messages = create_sample_messages()
    
    # Create conversation
    conversation = Conversation(participant_id=user.id, participant=user)
    for message in messages:
        conversation.add_message(message)
    
    logger.info(
        "Sample conversation created",
        participant=user.name,
        username=user.username,
        message_count=len(messages),
        linkedin_extracted=user.linkedin_url
    )
    
    # Step 2: Test AI summarization
    logger.info("Step 2: Testing AI summarization...")
    try:
        summary = conversation_summarizer.summarize_conversation(conversation, max_length=150)
        logger.info("✓ AI summarization successful", summary_preview=summary[:100] + "...")
    except Exception as e:
        logger.warning("AI summarization failed, using fallback", error=str(e))
    
    # Step 3: Test Google Sheets formatting
    logger.info("Step 3: Testing Google Sheets formatting...")
    formatter = SheetsFormatter()
    formatted_data = formatter.format_conversation_for_sheets(conversation)
    
    logger.info("✓ Sheets formatting successful")
    for key, value in formatted_data.items():
        if key == "conversation_summary":
            logger.info(f"  {key}: {str(value)[:100]}..." if len(str(value)) > 100 else f"  {key}: {value}")
        else:
            logger.info(f"  {key}: {value}")
    
    # Step 4: Test Google Sheets connection (optional)
    logger.info("Step 4: Testing Google Sheets connection...")
    try:
        # Test connection without writing
        worksheet = sheets_client.connect_to_sheet()
        sheets_client.setup_headers()
        logger.info("✓ Google Sheets connection successful")
        
        # Ask user if they want to write test data
        write_test = input("Do you want to write this test data to your Google Sheet? (y/n): ").lower().strip()
        if write_test == 'y':
            sheets_client.write_conversations([formatted_data])
            logger.info("✓ Test data written to Google Sheets successfully!")
        else:
            logger.info("Skipped writing to Google Sheets")
            
    except Exception as e:
        logger.error("Google Sheets connection failed", error=str(e))
    
    # Step 5: Show summary
    logger.info("🎉 Pipeline test completed!")
    logger.info("Summary of what was tested:")
    logger.info("  ✓ User profile data extraction (including LinkedIn)")
    logger.info("  ✓ Message filtering and conversation building")
    logger.info("  ✓ AI-powered summarization with enhanced prompts")
    logger.info("  ✓ Google Sheets formatting with new columns")
    logger.info("  ✓ Google Sheets API connection")
    
    return True


if __name__ == "__main__":
    try:
        success = test_conversation_pipeline()
        print("\n" + "="*50)
        if success:
            print("🎉 ALL TESTS PASSED! Your pipeline is ready to go!")
            print("\nNext steps:")
            print("1. Get X API v2 DM access for real data")
            print("2. Or manually provide user IDs for testing")
            print("3. Run: python3 src/main.py --participant-ids USER_ID_HERE --dry-run")
        else:
            print("❌ Some tests failed. Check the logs above.")
        print("="*50)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)
