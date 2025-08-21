# Twitter DM to Google Sheets Organizer

## Project Overview
A personal tool to organize Twitter/X direct messages by extracting 1-on-1 conversations and summarizing them in a Google Sheet for easy review and organization.

## Goals & Objectives
- **Primary Goal**: Extract and organize personal Twitter DM conversations 
- **Output Format**: Google Sheets with username and conversation summaries
- **Scope**: 1-on-1 conversations only (not group chats)
- **Use Case**: Personal productivity and conversation management

## Core Features

### Phase 1 (Completed ✅)
- [x] Project setup and structure
- [x] X API authentication setup (OAuth 1.0a with DM permissions)
- [x] Enhanced user profile extraction with LinkedIn discovery
- [x] AI-powered conversation summarization with enhanced prompts
- [x] Google Sheets integration with comprehensive data columns
- [x] Comprehensive error handling, logging, and rate limiting
- [x] CLI interface with multiple operational modes

### Phase 2 (In Progress 🚧)
- [x] Fetch 1-on-1 DM conversations using X API v2 (framework ready)
- [x] Extract conversation participants and enhanced message content
- [ ] Real-world DM access testing and optimization (requires non-Free tier)
- [ ] Bulk conversation processing workflows

## Technical Architecture

### X API Integration
- **Authentication**: OAuth 1.0a with DM permissions (requires app approval)
- **Required Permissions**: Read, Write, and Direct Message access
- **Primary Endpoints**: 
  - `GET /2/dm_events` (conversation discovery)
  - `GET /2/dm_conversations/with/:participant_id/dm_events` (message retrieval)
  - `GET /2/users/:id` (enhanced profile data)
- **Rate Limits**: 300 requests per 15 minutes with intelligent rate limiting
- **Data Format**: JSON with comprehensive user and message metadata

### Google Sheets Integration
- **Authentication**: Google Service Account or OAuth 2.0
- **API**: Google Sheets API v4
- **Enhanced Output Schema**:
  - Column A: Username/Handle
  - Column B: Real Name
  - Column C: LinkedIn URL (AI-discovered)
  - Column D: Location
  - Column E: Bio/Description
  - Column F: Website
  - Column G: Verification Status
  - Column H: Conversation Summary (AI-enhanced)
  - Column I: Message Count
  - Column J: Last Message Date
 

### Enhanced Data Processing
- **Conversation Aggregation**: Group messages by participant_id with chronological ordering
- **Message Filtering**: Remove low-value content (greetings, reactions) before summarization
- **AI Summary Generation**: Enhanced prompts focusing on decisions, action items, and key insights
- **LinkedIn Discovery**: Pattern matching and Gemini 2.5 Flash with iterative self-evaluation (PASS/FAIL)
- **Profile Enhancement**: Extract companies, locations, and verification data
- **Data Validation**: Comprehensive validation and formatting for Google Sheets
- **Quality Scoring**: Confidence levels and reasoning for AI-generated content

### AI Integration
- **OpenAI GPT**: Enhanced conversation summarization with structured prompts (configurable model; default gpt-4o-mini)
- **Google Gemini (2.5 Flash)**: URL-only prompt and iterative PASS/FAIL validation to return a single `linkedin.com/in/...` URL (or NOT_FOUND)
- **Fallback Systems**: Graceful degradation when AI services unavailable
- **Privacy Protection**: AI prompts designed to exclude sensitive information

## Project Structure
```
twitterbot/
├── src/
│   ├── twitter/
│   │   ├── __init__.py
│   │   ├── client.py          # X API client with OAuth 1.0a and rate limiting
│   │   ├── dm_fetcher.py      # DM conversation retrieval with pagination
│   │   └── models.py          # Enhanced data models with LinkedIn extraction
│   ├── google_sheets/
│   │   ├── __init__.py
│   │   ├── client.py          # Google Sheets API client with enhanced columns
│   │   └── formatter.py      # Data formatting, validation, and statistics
│   ├── summarizer/
│   │   ├── __init__.py
│   │   └── conversation_summarizer.py  # Enhanced AI summarization with filtering
│   ├── linkedin_discovery.py      # Manual pattern matching for LinkedIn URLs
│   ├── gemini_linkedin_discovery.py  # AI-powered LinkedIn discovery with web search
│   └── main.py               # CLI orchestration with multiple operational modes
├── config/
│   ├── settings.py           # Configuration management
│   └── .env.example          # Environment variables template
├── tests/
│   ├── test_twitter/
│   ├── test_google_sheets/
│   └── test_summarizer/
├── pyproject.toml           # Project configuration and dependencies
├── uv.lock                  # Dependency lock file
├── .env                      # Environment variables (gitignored)
├── .gitignore
├── PROJECT.md               # This file
└── README.md                # Setup and usage instructions
```

## Environment Variables Required
```
# X API Credentials (with DM permissions)
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret

# Google Sheets Integration
GOOGLE_SHEETS_CREDENTIALS_PATH=config/service_account.json
GOOGLE_SHEETS_ID=your_sheet_id

# AI Services (Optional)
OPENAI_API_KEY=your_openai_key          # Enhanced conversation summarization
GOOGLE_AI_API_KEY=your_google_ai_key    # Automated LinkedIn discovery
GOOGLE_CSE_API_KEY=your_cse_key         # Google Custom Search API (enhanced reliability)
GOOGLE_CSE_CX=your_search_engine_id     # Custom Search Engine ID

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
MAX_REQUESTS_PER_WINDOW=280
```

## Success Metrics
- ✅ Successfully authenticate with X API (OAuth 1.0a with DM permissions)
- ✅ Enhanced user profile extraction with comprehensive data
- ✅ AI-powered LinkedIn discovery (Gemini 2.5 iterative URL selection)
- ✅ Intelligent conversation summarization focusing on key insights
- ✅ Comprehensive Google Sheets integration with 10 data columns
- ✅ Robust error handling, rate limiting, and fallback systems
- 🚧 Real-world DM conversation retrieval and processing
- 🚧 Bulk conversation processing workflows

## Notes & Considerations
- **Privacy**: All data processing happens locally; no external storage of DMs
- **Rate Limiting**: Respect X API limits (300 requests/15 minutes)
- **Data Freshness**: Consider caching to avoid re-processing old conversations
- **Error Recovery**: Implement robust error handling for API failures
- **Incremental Updates**: Design for adding new conversations without full refresh

## Development Status
**Current Phase**: Advanced Features Complete ✅
**Status**: Ready for real-world DM processing with X API v2 permissions
**Next Steps**: 
- Obtain X API v2 DM permissions for production use
- Test bulk conversation processing workflows
- Optimize AI discovery for scale

## Key Achievements
- ✅ **Complete authentication system** with X API OAuth 1.0a
- ✅ **Enhanced profile extraction** with 7 data points per user
- ✅ **Multi-layer automated LinkedIn discovery** (5 fallback methods, zero manual intervention)
- ✅ **Advanced conversation summarization** with structured AI prompts
- ✅ **Comprehensive Google Sheets integration** with 10 organized columns
- ✅ **Production-ready architecture** with error handling and rate limiting
- ✅ **CLI interface** with multiple operational modes and dry-run capabilities
- ✅ **Extensive testing framework** with mock data and verification scripts
