#!/usr/bin/env python3
"""Interactive manual conversation test.

Allows you to input a Twitter username and custom conversation text, then
summarizes and (optionally) writes the result to your Google Sheet.

No Twitter API DM access is required for this test.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.models import User, Message, Conversation  # noqa: E402
from src.summarizer.conversation_summarizer import conversation_summarizer  # noqa: E402
from src.google_sheets.formatter import SheetsFormatter  # noqa: E402
from src.google_sheets.client import sheets_client  # noqa: E402
from src.gemini_linkedin_discovery import find_linkedin_profile  # noqa: E402
from src.linkedin_discovery import LinkedInDiscovery  # noqa: E402


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def prompt_input(prompt: str) -> str:
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)


def read_conversation_lines() -> List[str]:
    print("\nEnter your conversation lines. One per line. Examples:")
    print("  me: Hey, want to sync next Tue at 2pm?")
    print("  them: Tue 2pm works. Let's chat about the API integration.")
    print("Finish with an empty line (press Enter on a blank line).\n")

    lines: List[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line is None:
            break
        line = line.strip()
        if line == "":
            break
        lines.append(line)
    return lines


def build_messages_from_lines(lines: List[str], my_user_id: str, other_user_id: str) -> List[Message]:
    messages: List[Message] = []
    base_time = datetime.now() - timedelta(minutes=len(lines))
    current_time = base_time

    for idx, raw in enumerate(lines, start=1):
        lower = raw.lower()
        sender_id = my_user_id if lower.startswith("me:") else other_user_id
        text = raw.split(":", 1)[1].strip() if ":" in raw else raw

        messages.append(
            Message(
                id=f"manual_msg_{idx}",
                text=text,
                created_at=current_time,
                sender_id=sender_id,
                recipient_id=(other_user_id if sender_id == my_user_id else my_user_id),
            )
        )
        current_time += timedelta(minutes=1)

    return messages


def main() -> int:
    print("🧪 Manual Conversation Test (no X API required)")

    username = prompt_input("Twitter username (without @): ").strip()
    if not username:
        print("Username is required.")
        return 1

    real_name = prompt_input("Real name (optional): ").strip() or "Unknown"
    location = prompt_input("Location (optional): ").strip() or None
    website = prompt_input("Website (optional): ").strip() or None

    lines = read_conversation_lines()
    if not lines:
        print("No conversation lines provided.")
        return 1

    # Build participant and conversation
    other_user = User(
        id=f"manual_{username}",
        username=username,
        name=real_name,
        verified=False,
    )
    my_user_id = "your_user_id"

    conversation = Conversation(participant_id=other_user.id, participant=other_user)
    for msg in build_messages_from_lines(lines, my_user_id, other_user.id):
        conversation.add_message(msg)

    # Summarize
    summary = conversation_summarizer.summarize_conversation(conversation, max_length=150)
    print("\nSummary:\n" + summary + "\n")

    # Format
    formatter = SheetsFormatter()
    formatted = formatter.format_conversation_for_sheets(conversation)

    # LinkedIn discovery enrichment (auto-run)
    print("\n🔍 Searching for LinkedIn profile...")
    try:
        result = find_linkedin_profile(
            real_name=real_name or username,
            location=location,
            website=website,
            conversation_summary=summary  # Use summary as conversation_summary
        )
        
        if result:
            # Check if it's a direct LinkedIn URL or a search URL
            if "linkedin.com/in/" in result and "google.com/search" not in result:
                formatted["linkedin_url"] = result
                print(f"✅ Found LinkedIn profile automatically: {result}")
                logger.info("LinkedIn profile found automatically", linkedin_url=result)
            else:
                # It's a search URL for manual verification (automation failed)
                print(f"🔍 Automated search failed, providing manual search URL:")
                print(f"   {result}")
                print(f"   Please copy this URL to your browser to find the LinkedIn profile manually.")
                
                # Ask user if they want to manually enter a LinkedIn URL
                manual_url = prompt_input("\nDid you find a LinkedIn URL? Enter it here (or press Enter to skip): ").strip()
                if manual_url and "linkedin.com/in/" in manual_url:
                    formatted["linkedin_url"] = manual_url
                    print(f"✅ Added manual LinkedIn URL: {manual_url}")
                    logger.info("Manual LinkedIn URL added", linkedin_url=manual_url)
        else:
            print("❌ Could not find LinkedIn profile")
            logger.warning("No LinkedIn profile found")
            
    except Exception as e:
        print(f"❌ LinkedIn search failed: {e}")
        logger.error("LinkedIn discovery failed", error=str(e))

    # Optionally write to Google Sheets (custom 4-column schema, start at row 2)
    try:
        write = prompt_input("Write this to your Google Sheet? (y/n): ").strip().lower()
        if write == "y":
            sheets_client.connect_to_sheet()
            ws = sheets_client.worksheet
            # Ensure headers exist once, then append the row to the next empty line
            headers = ["Username", "Name", "Conversation Summary", "LinkedIn Profile"]
            existing_headers = ws.row_values(1)
            if not existing_headers or existing_headers != headers:
                if existing_headers:
                    ws.delete_rows(1)
                ws.insert_row(headers, 1)
            # Append the new row
            row = [
                formatted.get("username", "Unknown"),
                formatted.get("real_name", "Unknown"),
                formatted.get("conversation_summary", "No summary"),
                formatted.get("linkedin_url", ""),
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
            logger.info("✅ Data appended to Google Sheets with simplified headers")
        else:
            logger.info("Skipped writing to Google Sheets")
    except Exception as e:
        logger.error("Failed to write to Google Sheets", error=str(e))

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


