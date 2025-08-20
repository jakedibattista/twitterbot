# Twitter DM to Google Sheets Organizer

A personal tool to organize Twitter/X direct messages by extracting 1-on-1 conversations and summarizing them in a Google Sheet for easy review and organization.

## Features

- 🔐 **Secure Authentication**: OAuth integration with X API and Google Sheets
- 📱 **DM Extraction**: Fetch 1-on-1 direct message conversations with X API v2
- 🤖 **Enhanced AI Summarization**: Intelligent conversation summaries focused on key decisions and actions
- 🔗 **Smart LinkedIn Discovery**: AI-powered LinkedIn profile discovery using Google Gemini with real web search
- 👤 **Rich Profile Data**: Extract real names, locations, bios, companies, and social media links
- 📊 **Comprehensive Google Sheets**: Organized output with enhanced profile information and conversation insights
- ⚡ **Rate Limit Handling**: Respectful API usage with automatic rate limiting and retry logic
- 🛡️ **Privacy Protection**: All processing happens locally with privacy-conscious summarization
- 🔄 **Fallback Systems**: Graceful degradation when AI services are unavailable

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- X (Twitter) Developer Account with **DM permissions** (requires app approval)
- Google Cloud Project with Sheets API enabled
- OpenAI API key (optional, for enhanced AI summaries)
- Google AI API key (optional, for LinkedIn profile discovery)

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd twitterbot

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### 3. Configuration

1. **Copy environment template:**
   ```bash
   cp example.env .env
   ```

2. **Configure X API credentials** in `.env`:
   - Get credentials from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
   ```env
   X_API_KEY=your_api_key_here
   X_API_SECRET=your_api_secret_here
   X_ACCESS_TOKEN=your_access_token_here
   X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
   ```

3. **Set up Google Sheets:**
   - Create a [Google Cloud Project](https://console.cloud.google.com/)
   - Enable Google Sheets API
   - Create a Service Account and download the JSON key file
   - Place the key file in `config/service_account.json`
   - Create a Google Sheet and add the service account email as an editor
   - Add the Sheet ID to `.env`:
   ```env
   GOOGLE_SHEETS_ID=your_sheet_id_here
   GOOGLE_SHEETS_CREDENTIALS_PATH=config/service_account.json
   ```

4. **Optional - AI Services:**
   ```env
   # Enhanced conversation summarization
   OPENAI_API_KEY=your_openai_key_here
   
   # LinkedIn profile discovery with real web search
   GOOGLE_AI_API_KEY=your_google_ai_key_here
   ```

### 4. Verify Setup

```bash
python setup_verification.py
```

This will verify all your API credentials and connections.

### 5. Run the Organizer

```bash
# Basic usage with user IDs (module)
python -m src.main --participant-ids USER_ID_1 USER_ID_2 USER_ID_3

# Or after editable install, use the CLI entrypoint
twitter-dm-organizer --participant-ids USER_ID_1 USER_ID_2 USER_ID_3

# Discover recent DM participants automatically (e.g., last 10)
python -m src.main --discover-recent 10 --max-messages 50

# Limit to messages from the last N days
python -m src.main --discover-recent 10 --since-days 30

# Enrich missing LinkedIn URLs using AI (optional)
python -m src.main --discover-recent 10 --enrich-linkedin --enrich-limit 5

# Advanced options
python -m src.main \
  --participant-ids USER_ID_1 USER_ID_2 \
  --max-messages 50 \
  --since-days 60 \
  --clear-sheet \
  --no-summaries
```

## Usage Examples

### Basic Conversation Export
```bash
python -m src.main --participant-ids 123456789 987654321
```

### Large Export with Custom Limits
```bash
python -m src.main \
  --participant-ids 123456789 987654321 456789123 \
  --max-messages 200 \
  --clear-sheet
```

### Dry Run (Verification Only)
```bash
python -m src.main --participant-ids 123456789 --dry-run
```

### Manual Conversation Mode (no X API required)
```bash
python test_manual_conversation.py
# Prompts for username/name and conversation lines; can run Gemini to find LinkedIn and write to Sheets
```

### Verify DM Access
```bash
# Confirms API credentials and DM permissions
python setup_verification.py
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--participant-ids` | User IDs to fetch conversations with | - |
| `--discover-recent` | Discover and use N recent DM participants | - |
| `--max-messages` | Maximum messages per conversation | 100 |
| `--no-summaries` | Skip AI summary generation | False |
| `--clear-sheet` | Clear existing sheet data before writing | False |
| `--dry-run` | Run verification only, don't fetch data | False |
| `--since-days` | Only fetch messages from the last N days | None |
| `--enrich-linkedin` | Use AI to fill missing LinkedIn URLs | False |
| `--enrich-limit` | Limit AI enrichment to first N users (0 = all) | 0 |

## Enhanced Output Format

The Google Sheet will contain comprehensive profile and conversation data:

| Column | Description |
|--------|-------------|
| Username | Twitter username/handle |
| User ID | Twitter user ID (for stable updates) |
| Real Name | Full name from Twitter profile |
| LinkedIn URL | Discovered LinkedIn profile (AI-powered) |
| Location | User's location |
| Bio | Twitter bio/description |
| Website | Personal/company website |
| Verified | Twitter verification status |
| Conversation Summary | AI-enhanced summary focusing on key decisions and actions |
| Message Count | Number of messages in conversation |
| Last Message Date | Date of most recent message |

## Project Structure

```
twitterbot/
├── src/
│   ├── twitter/              # X API integration
│   │   ├── client.py         # API client and OAuth auth
│   │   ├── dm_fetcher.py     # DM retrieval with rate limiting
│   │   └── models.py         # Enhanced data models with LinkedIn extraction
│   ├── google_sheets/        # Google Sheets integration
│   │   ├── client.py         # Sheets API client with enhanced columns
│   │   └── formatter.py      # Data formatting and validation
│   ├── summarizer/           # AI-powered conversation analysis
│   │   └── conversation_summarizer.py  # Enhanced prompts for key insights
│   ├── linkedin_discovery.py      # Manual LinkedIn pattern matching
│   ├── gemini_linkedin_discovery.py  # AI-powered LinkedIn discovery
│   └── main.py              # Main orchestration with CLI interface
├── config/
│   ├── settings.py          # Configuration management (packaged under src/config)
│   └── service_account.json # Google credentials (you add this)
├── tests/                   # Test suite
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml          # Project configuration
├── .env                    # Environment variables (you create this)
└── README.md               # This file
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Run tests
pytest
```

### Installing in Development Mode

```bash
pip install -e .
```

## LinkedIn Profile Discovery

This tool features **dual-layer LinkedIn discovery** for comprehensive profile information:

### 🔍 **Automatic Pattern Detection**
- Extracts LinkedIn URLs directly mentioned in Twitter bios
- Detects patterns like: "LinkedIn: linkedin.com/in/username"
- Handles website URLs that are LinkedIn profiles
- Recognizes @linkedin: username formats

### 🤖 **AI-Powered Discovery (Gemini 2.5 Flash)**
- Produces a single LinkedIn profile URL (or NOT_FOUND) from name, Twitter handle, optional location/company, and conversation summary
- Iterative self-evaluation loop: generate a candidate, then validate PASS/FAIL; repeats up to 3 attempts
- Output: one `https://www.linkedin.com/in/...` URL when confident

### 🎯 **Smart Search Strategies**
```
"[Name]" linkedin [location]
"[Name]" [company] linkedin  
"[Username]" twitter linkedin
site:linkedin.com/in "[Name]"
```

### 📊 **LinkedIn Discovery Results**
- **High Confidence**: Clear match with multiple verification points
- **Medium/Low**: Potential matches requiring manual review
- **Not Found**: No confident matches (better than false positives!)
- **Search URLs**: Manual verification links when AI is uncertain

**Example Output:**
```
LinkedIn URL: https://www.linkedin.com/in/john-doe-tech
Confidence: HIGH
Reasoning: Profile matches name, San Francisco location, and TechCorp employment from bio
```

## Troubleshooting

### Common Issues

1. **X API Authentication Errors**
   - Verify your API keys in `.env`
   - Ensure your Twitter Developer App has the correct permissions
   - Check that your access tokens are valid

2. **Google Sheets Access Denied**
   - Verify the service account JSON file path
   - Ensure the service account email is added as an editor to your sheet
   - Check that the Google Sheets API is enabled in your project

3. **Rate Limit Errors**
   - The tool automatically handles rate limits
   - Reduce `--max-messages` if you hit limits frequently
   - Consider running smaller batches of conversations

4. **OpenAI API Errors**
   - Verify your API key is valid and has credits
   - The tool will fall back to basic summaries if OpenAI fails

### Getting User IDs

To find Twitter user IDs for the `--participant-ids` parameter:

1. Use the Twitter API to look up users by username
2. Use online tools like "Twitter ID Lookup"
3. Check the user's profile URL or API responses

### Logs and Debugging

The application uses structured logging. Set log level in `.env`:
```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## Privacy and Security

- All message processing happens locally on your machine
- No conversation data is stored externally (except in your Google Sheet)
- AI summarization is designed to protect privacy and exclude personal details
- Credentials are managed through environment variables and excluded from version control

## Rate Limits

The tool respects X API rate limits:
- DM endpoints: 300 requests per 15-minute window
- User lookups: 300 requests per 15-minute window
- Automatic retry logic with exponential backoff

## Contributing

This is a personal project, but suggestions and improvements are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [Tweepy](https://github.com/tweepy/tweepy) for X API integration
- Uses [gspread](https://github.com/burnash/gspread) for Google Sheets
- AI summaries powered by [OpenAI](https://openai.com/)
- Structured logging with [structlog](https://github.com/hynek/structlog)
