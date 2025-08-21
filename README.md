# Twitter DM Organizer

A simple tool that takes your Twitter/X direct messages and organizes them in a Google Spreadsheet. It automatically finds LinkedIn profiles for people you chat with and creates summaries of your conversations.

## What This Does

- 📱 **Gets your Twitter DMs**: Fetches your private message conversations
- 🤖 **Creates summaries**: Uses AI to summarize what you talked about
- 🔍 **Finds LinkedIn profiles**: Automatically searches for people's LinkedIn pages
- 📊 **Saves to Google Sheets**: Puts everything in a neat spreadsheet

## Before You Start

You'll need:
- Python 3.9 or higher installed on your computer
- A Twitter Developer account (free, but requires approval)
- A Google account for the spreadsheet
- Some API keys (we'll help you get these)

## Setup Guide

### Step 1: Get the Code

```bash
# Download this project
git clone <your-repo-url>
cd twitterbot

# Install everything you need
uv sync
# OR if you don't have uv:
pip install -e .
```

### Step 2: Get Your API Keys

#### Twitter/X API Keys
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new app
3. Apply for "Direct Message" permissions (this might take a few days)
4. Copy your 4 keys: API Key, API Secret, Access Token, Access Token Secret

#### Google Sheets Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Google Sheets API"
4. Create a "Service Account" 
5. Download the JSON file (save it as `config/service_account.json`)
6. Create a new Google Spreadsheet
7. Share it with the email from your JSON file (give it "Editor" permission)
8. Copy the spreadsheet ID from the URL

#### Optional: AI Features
- **OpenAI**: Get an API key from [OpenAI](https://openai.com/) for better summaries
- **Google AI**: Get an API key from [Google AI Studio](https://makersuite.google.com/) for LinkedIn search
- **Google Custom Search** (Recommended for reliable LinkedIn discovery):
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Enable "Custom Search JSON API"
  3. Create API credentials and copy the API key
  4. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
  5. Create a new search engine (search the entire web)
  6. Copy the Search Engine ID (cx parameter)

### Step 3: Configure Your Settings

1. Copy the example settings:
   ```bash
   cp example.env .env
   ```

2. Edit the `.env` file with your information:
   ```env
   # Your Twitter keys
   X_API_KEY=paste_your_api_key_here
   X_API_SECRET=paste_your_api_secret_here
   X_ACCESS_TOKEN=paste_your_access_token_here
   X_ACCESS_TOKEN_SECRET=paste_your_access_token_secret_here

   # Your Google Sheets info
   GOOGLE_SHEETS_ID=paste_your_spreadsheet_id_here
   GOOGLE_SHEETS_CREDENTIALS_PATH=config/service_account.json

   # Optional AI features
   OPENAI_API_KEY=paste_your_openai_key_here
   GOOGLE_AI_API_KEY=paste_your_google_ai_key_here
   
   # Optional: More reliable LinkedIn search (recommended)
   GOOGLE_CSE_API_KEY=paste_your_custom_search_api_key_here
   GOOGLE_CSE_CX=paste_your_search_engine_id_here
   ```

### Step 4: Test Everything

```bash
# Check if everything is working
python setup_verification.py

# Test LinkedIn search specifically
python setup_linkedin_discovery.py
```

## How to Use It

### Test Without Twitter API (Good for Testing)
```bash
# Use uv run to ensure dependencies are available
uv run python test_manual_conversation.py

# OR if you installed with pip install -e .
python test_manual_conversation.py
```
This lets you type in fake conversations to test the LinkedIn search and spreadsheet features.

### Get Real Twitter DMs
```bash
# Get conversations with specific people (you need their user IDs)
uv run python -m src.main --participant-ids 123456789 987654321

# Or find recent conversations automatically
uv run python -m src.main --discover-recent 10
```

### Find User IDs
To get someone's Twitter user ID:
1. Use online tools like "Twitter ID Lookup"
2. Or search for their username in Twitter API docs

## What You'll Get

Your Google Spreadsheet will have columns for:
- **Username**: Their Twitter handle
- **Real Name**: Their actual name
- **LinkedIn**: Their LinkedIn profile (found automatically!)
- **Location**: Where they're from
- **Bio**: Their Twitter description
- **Website**: Their personal website
- **Conversation Summary**: What you talked about
- **Message Count**: How many messages you exchanged
- **Last Message Date**: When you last chatted

## Troubleshooting

### "Authentication Failed"
- Double-check your API keys in the `.env` file
- Make sure you copied them exactly (no extra spaces)

### "Can't Access Google Sheets"
- Make sure you shared your spreadsheet with the email from your JSON file
- Check that the JSON file is in the right place: `config/service_account.json`

### "Rate Limit Errors"
- Twitter limits how many requests you can make
- Try smaller numbers (like `--discover-recent 5` instead of 20)
- Wait a bit and try again

### "LinkedIn Search Not Working"
- Make sure you have `GOOGLE_AI_API_KEY` in your `.env` file
- The tool will still work, just won't find LinkedIn profiles automatically

## How LinkedIn Search Works

The tool automatically finds LinkedIn profiles by:
1. **Smart Search**: Uses AI to search Google for the person's LinkedIn
2. **Multiple Methods**: Tries different search approaches if one fails
3. **No Manual Work**: Gets the first good result automatically
4. **Safe Fallback**: Gives you a search link if it can't find anything

Example:
```
🔍 Searching for LinkedIn profile...
✅ Found LinkedIn profile automatically: https://www.linkedin.com/in/john-smith-123
```

## Privacy & Security

- Everything runs on your computer (nothing sent to random servers)
- Your conversations are only saved to YOUR Google Spreadsheet
- AI summaries are designed to protect sensitive information
- All your API keys stay in your `.env` file (never shared)

## Getting Help

If something isn't working:
1. Check the troubleshooting section above
2. Look at the error messages (they usually tell you what's wrong)
3. Make sure all your API keys are correct
4. Try the test scripts first before using real Twitter data

## What's in This Project

```
twitterbot/
├── src/                     # Main code
├── config/                  # Your settings and keys
├── tests/                   # Test files
├── test_manual_conversation.py  # Test without Twitter
├── setup_verification.py    # Check if everything works
├── .env                     # Your API keys (you create this)
└── README.md               # This file
```

## Legal Stuff

- MIT License (means you can use it however you want)
- Respects Twitter's rate limits
- Only accesses your own DMs (with your permission)