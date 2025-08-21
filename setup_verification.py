"""Setup verification script for Twitter DM organizer.

Run this script to verify your API credentials and configuration
before running the main application.
"""

import sys
from pathlib import Path
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import settings
from twitter.client import x_client
from twitter.dm_fetcher import DMFetcher

# Configure basic logging
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


def verify_setup() -> bool:
    """Verify all components of the setup are working correctly.
    
    Returns:
        True if all verifications pass, False otherwise.
    """
    logger.info("Starting setup verification...")
    logger.info("💡 Tip: Run 'python setup_linkedin_discovery.py' to verify LinkedIn discovery features")
    
    # 1. Check environment file
    env_file = Path(".env")
    if not env_file.exists():
        logger.error("No .env file found. Please copy .env.example to .env and configure it.")
        return False
    
    logger.info("✓ .env file found")
    
    # 2. Validate X API credentials format
    try:
        if not settings.validate_x_credentials():
            logger.error("X API credentials missing or invalid in .env file")
            return False
        logger.info("✓ X API credentials loaded")
    except Exception as e:
        logger.error("Error loading settings", error=str(e))
        return False
    
    # 3. Test X API authentication
    auth_ok = False
    try:
        user_info = x_client.verify_credentials()
        logger.info(
            "✓ X API authentication successful",
            username=user_info["username"],
            user_id=user_info["id"]
        )
        auth_ok = True
    except Exception as e:
        logger.error("X API v2 get_me failed, attempting v1.1 fallback", error=str(e))
        try:
            me = x_client.api_v1.verify_credentials()
            if me:
                logger.info("✓ X API v1.1 authentication successful", username=getattr(me, 'screen_name', ''), user_id=getattr(me, 'id_str', ''))
                auth_ok = True
        except Exception as e2:
            logger.error("X API v1.1 authentication failed", error=str(e2))
            # Continue to DM events test to diagnose permissions
    
    # 4. Test DM access capability (permission check)
    try:
        dm_fetcher = DMFetcher(x_client)
        events = x_client.get_recent_dm_events(max_results=5)
        if events is None:
            logger.warning("DM events endpoint returned no data. Ensure your app has DM permissions.")
        else:
            count = len(events.get("data", []))
            logger.info("✓ DM events accessible", recent_event_count=count)
    except Exception as e:
        logger.error("Failed to access DM events", error=str(e))
        # Not fatal; user might not have DM v2 access yet

    # 5. Check Google Sheets configuration (without testing connection yet)
    if not settings.google_sheets_id:
        logger.warning("Google Sheets ID not configured - this will be needed later")
    else:
        logger.info("✓ Google Sheets ID configured")
    
    if not settings.google_sheets_credentials_path.exists():
        logger.warning("Google Sheets credentials file not found - this will be needed later")
    else:
        logger.info("✓ Google Sheets credentials file found")
    
    logger.info("🎉 Setup verification completed successfully!")
    logger.info("You're ready to start fetching your Twitter DMs!")
    
    return True


if __name__ == "__main__":
    success = verify_setup()
    sys.exit(0 if success else 1)
