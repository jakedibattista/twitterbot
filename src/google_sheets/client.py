"""Google Sheets API client for writing conversation data.

Provides authenticated access to Google Sheets API v4 for creating
and updating spreadsheets with Twitter conversation summaries.
"""

import gspread
from google.auth.exceptions import GoogleAuthError
from typing import List, Dict, Any, Optional
import structlog
from pathlib import Path
from config.settings import settings

logger = structlog.get_logger()


class GoogleSheetsClient:
    """Google Sheets API client with authentication and data operations."""
    
    def __init__(self):
        """Initialize the Google Sheets client with authentication."""
        self.client: Optional[gspread.Client] = None
        self.worksheet: Optional[gspread.Worksheet] = None
        self._setup_authentication()
    
    def _setup_authentication(self) -> None:
        """Set up Google Sheets API authentication using service account.
        
        Raises:
            GoogleAuthError: If authentication fails.
            FileNotFoundError: If credentials file is not found.
        """
        try:
            credentials_path = settings.google_sheets_credentials_path
            
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Google Sheets credentials file not found: {credentials_path}"
                )
            
            # Authenticate using service account
            self.client = gspread.service_account(filename=str(credentials_path))
            
            logger.info("Google Sheets authentication successful")
            
        except Exception as e:
            logger.error("Failed to authenticate with Google Sheets", error=str(e))
            raise
    
    def connect_to_sheet(self, sheet_id: Optional[str] = None) -> gspread.Worksheet:
        """Connect to a specific Google Sheet and return the first worksheet.
        
        Args:
            sheet_id: Google Sheet ID. If None, uses ID from settings.
            
        Returns:
            The first worksheet of the specified sheet.
            
        Raises:
            Exception: If sheet cannot be accessed or doesn't exist.
        """
        try:
            if not self.client:
                raise ValueError("Google Sheets client not initialized")
            
            target_sheet_id = sheet_id or settings.google_sheets_id
            if not target_sheet_id:
                raise ValueError("No Google Sheet ID specified")
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(target_sheet_id)
            self.worksheet = spreadsheet.sheet1  # Use first worksheet
            
            logger.info(
                "Connected to Google Sheet",
                sheet_id=target_sheet_id,
                sheet_title=spreadsheet.title
            )
            
            return self.worksheet
            
        except Exception as e:
            logger.error(
                "Failed to connect to Google Sheet",
                sheet_id=target_sheet_id,
                error=str(e)
            )
            raise
    
    def setup_headers(self) -> None:
        """Set up column headers in the worksheet if they don't exist.
        
        Creates headers: Username, User ID, Real Name, LinkedIn URL, Location, Bio, Website,
        Verified, Conversation Summary, Message Count, Last Message Date
        """
        try:
            if not self.worksheet:
                raise ValueError("No worksheet connected")
            
            headers = [
                "Username",
                "User ID",
                "Real Name",
                "LinkedIn URL",
                "Location", 
                "Bio",
                "Website",
                "Verified",
                "Conversation Summary",
                "Message Count",
                "Last Message Date"
            ]
            
            # Check if headers already exist
            existing_headers = self.worksheet.row_values(1)
            
            if not existing_headers or existing_headers != headers:
                # Clear first row and set headers
                self.worksheet.delete_rows(1)
                self.worksheet.insert_row(headers, 1)
                
                # Format headers (bold)
                self.worksheet.format("A1:K1", {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                })
                
                logger.info("Headers set up successfully")
            else:
                logger.info("Headers already exist and are correct")
                
        except Exception as e:
            logger.error("Failed to set up headers", error=str(e))
            raise
    
    def write_conversations(self, conversations_data: List[Dict[str, Any]]) -> None:
        """Write conversation data to the Google Sheet.
        
        Args:
            conversations_data: List of conversation dictionaries with summary data.
            
        Raises:
            Exception: If writing to sheet fails.
        """
        try:
            if not self.worksheet:
                raise ValueError("No worksheet connected")
            
            if not conversations_data:
                logger.warning("No conversation data to write")
                return
            
            # Prepare data rows
            rows_to_add = []
            for conv_data in conversations_data:
                row = [
                    conv_data.get("username", "Unknown"),
                    conv_data.get("user_id", ""),
                    conv_data.get("real_name", "Unknown"),
                    conv_data.get("linkedin_url", ""),
                    conv_data.get("location", ""),
                    conv_data.get("bio", ""),
                    conv_data.get("website", ""),
                    conv_data.get("verified", ""),
                    conv_data.get("conversation_summary", "No summary"),
                    str(conv_data.get("message_count", 0)),
                    conv_data.get("last_message_date", "")
                ]
                rows_to_add.append(row)
            
            # Append values using Sheets API behavior to always use the next empty row
            # This avoids race conditions and header off-by-ones
            self.worksheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            
            logger.info(
                "Conversations written successfully",
                rows_added=len(rows_to_add)
            )
            
        except Exception as e:
            logger.error("Failed to write conversations to sheet", error=str(e))
            raise
    
    def update_conversation(
        self, 
        user_id: str, 
        updated_data: Dict[str, Any]
    ) -> bool:
        """Update an existing conversation row in the sheet.
        
        Args:
            user_id: User ID to find and update.
            updated_data: Dictionary with updated conversation data.
            
        Returns:
            True if update was successful, False if user not found.
        """
        try:
            if not self.worksheet:
                raise ValueError("No worksheet connected")
            
            # Find the row with the matching user ID
            user_id_column = 2  # Column B (User ID)
            user_ids = self.worksheet.col_values(user_id_column)
            
            try:
                row_index = user_ids.index(user_id) + 1  # +1 for 1-based indexing
            except ValueError:
                logger.warning("User ID not found in sheet", user_id=user_id)
                return False
            
            # Update the row with new data
            updates = []
            if "username" in updated_data:
                updates.append({"range": f"A{row_index}", "values": [[updated_data["username"]]]})
            if "conversation_summary" in updated_data:
                updates.append({"range": f"I{row_index}", "values": [[updated_data["conversation_summary"]]]})
            if "message_count" in updated_data:
                updates.append({"range": f"J{row_index}", "values": [[str(updated_data["message_count"])]]})
            if "last_message_date" in updated_data:
                updates.append({"range": f"K{row_index}", "values": [[updated_data["last_message_date"]]]})
            
            # Batch update
            if updates:
                self.worksheet.batch_update(updates)
                logger.info("Conversation updated successfully", user_id=user_id)
                return True
            else:
                logger.warning("No valid update data provided", user_id=user_id)
                return False
                
        except Exception as e:
            logger.error("Failed to update conversation", user_id=user_id, error=str(e))
            raise
    
    def clear_sheet(self) -> None:
        """Clear all data from the worksheet (except headers).
        
        Warning: This will delete all conversation data.
        """
        try:
            if not self.worksheet:
                raise ValueError("No worksheet connected")
            
            # Get total number of rows
            all_values = self.worksheet.get_all_values()
            if len(all_values) > 1:  # More than just headers
                # Delete all rows except the header
                self.worksheet.delete_rows(2, len(all_values))
                logger.info("Sheet cleared successfully")
            else:
                logger.info("Sheet is already empty")
                
        except Exception as e:
            logger.error("Failed to clear sheet", error=str(e))
            raise
    
    def get_existing_conversations(self) -> List[Dict[str, Any]]:
        """Get all existing conversation data from the sheet.
        
        Returns:
            List of dictionaries containing existing conversation data.
        """
        try:
            if not self.worksheet:
                raise ValueError("No worksheet connected")
            
            records = self.worksheet.get_all_records()
            
            # Convert to our expected format
            conversations = []
            for record in records:
                conv_data = {
                    "username": record.get("Username", ""),
                    "user_id": record.get("User ID", ""),
                    "conversation_summary": record.get("Conversation Summary", ""),
                    "message_count": record.get("Message Count", 0),
                    "last_message_date": record.get("Last Message Date", "")
                }
                conversations.append(conv_data)
            
            logger.info("Retrieved existing conversations", count=len(conversations))
            return conversations
            
        except Exception as e:
            logger.error("Failed to get existing conversations", error=str(e))
            raise


# Global client instance
sheets_client = GoogleSheetsClient()
