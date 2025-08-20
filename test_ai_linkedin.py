#!/usr/bin/env python3
"""Test AI-powered LinkedIn discovery with simulated web search results.

This demonstrates how AI can analyze web search results to find LinkedIn profiles
more accurately than regex pattern matching.
"""

import sys
from pathlib import Path
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.linkedin_ai_discovery import AILinkedInDiscovery

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


def simulate_web_search_results(name: str, company: str = None) -> dict:
    """Simulate web search results for testing purposes."""
    
    # Simulate realistic search results that might be found
    search_results = {
        "name_location": [
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}-tech",
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '')}-dev"
        ],
        "name_company": [
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}-{company.lower()}" if company else None
        ],
        "twitter_linkedin": [
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}"
        ],
        "linkedin_site": [
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}-engineer",
            f"https://www.linkedin.com/in/{name.lower().replace(' ', '')}"
        ]
    }
    
    # Remove None values
    return {k: [url for url in v if url] for k, v in search_results.items()}


def test_ai_linkedin_discovery():
    """Test the AI LinkedIn discovery system."""
    
    print("🤖 AI-Powered LinkedIn Discovery Testing")
    print("="*60)
    
    ai_discovery = AILinkedInDiscovery()
    
    if not ai_discovery.client:
        print("❌ OpenAI client not available.")
        print("To test this feature:")
        print("1. Add OPENAI_API_KEY to your .env file")
        print("2. The system will use AI to analyze web search results")
        print("3. Much more accurate than regex pattern matching!")
        
        # Show what the system would do
        test_cases = [
            {
                "name": "John Doe",
                "username": "johndoe_dev",
                "bio": "Senior Software Engineer @TechCorp | AI enthusiast",
                "location": "San Francisco, CA",
                "company": "TechCorp"
            },
            {
                "name": "Sarah Johnson", 
                "username": "sarahtech",
                "bio": "CTO at StartupXYZ | Former @Google engineer",
                "location": "New York, NY",
                "company": "StartupXYZ"
            }
        ]
        
        print("\n🔍 Simulated AI Analysis Process:")
        print("-"*50)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest Case {i}: {test_case['name']} (@{test_case['username']})")
            
            # Simulate search results
            search_results = simulate_web_search_results(test_case['name'], test_case['company'])
            
            print(f"📍 Location: {test_case['location']}")
            print(f"🏢 Company: {test_case['company']}")
            print(f"📝 Bio: {test_case['bio']}")
            
            print(f"\n🔍 Web Search Results Found:")
            for search_type, urls in search_results.items():
                if urls:
                    print(f"  {search_type.replace('_', ' ').title()}:")
                    for url in urls:
                        print(f"    • {url}")
            
            print(f"\n🤖 AI Would Analyze:")
            print(f"  • Compare profile names with '{test_case['name']}'")
            print(f"  • Check if company '{test_case['company']}' appears in profiles")
            print(f"  • Verify location matches '{test_case['location']}'")
            print(f"  • Cross-reference with Twitter bio information")
            print(f"  • Assign confidence level (High/Medium/Low)")
            print(f"  • Provide reasoning for the match")
        
        return False
    
    # If AI is available, run actual tests
    print("✅ OpenAI client available. Running real AI tests...")
    
    # Test with custom profile
    print("\n🎯 Custom Profile Test")
    print("-"*30)
    
    name = input("Enter person's real name: ").strip()
    if not name:
        print("❌ Name required for testing")
        return False
    
    username = input("Enter Twitter username (without @): ").strip()
    bio = input("Enter bio/description: ").strip()
    location = input("Enter location (optional): ").strip() or None
    website = input("Enter website (optional): ").strip() or None
    
    print(f"\n🔍 Running AI LinkedIn discovery for {name}...")
    
    # Run AI discovery
    result = ai_discovery.find_linkedin_profile(
        name=name,
        username=username,
        bio=bio,
        location=location,
        website=website
    )
    
    print("\n📊 AI Discovery Results:")
    print("="*40)
    print(f"LinkedIn URL: {result.get('linkedin_url') or 'None found'}")
    print(f"Confidence: {result.get('confidence', 'Unknown')}")
    print(f"Method: {result.get('method', 'Unknown')}")
    
    if result.get('verification_notes'):
        print(f"Verification: {result['verification_notes']}")
    
    if result.get('alternative_profiles'):
        print("\nAlternative Profiles:")
        for alt in result['alternative_profiles']:
            print(f"  • {alt}")
    
    if result.get('ai_response'):
        print(f"\nFull AI Analysis:")
        print("-" * 30)
        print(result['ai_response'])
    
    return True


def compare_approaches():
    """Compare AI vs regex approaches."""
    
    print("\n🔬 AI vs Regex Pattern Matching Comparison")
    print("="*60)
    
    print("""
**Traditional Regex Approach:**
❌ Only finds explicit LinkedIn URLs in bios
❌ Misses profiles not directly mentioned  
❌ Can't verify if profile actually matches the person
❌ No confidence scoring
❌ Limited to pattern matching

**AI-Powered Approach:**
✅ Performs intelligent web searches
✅ Analyzes multiple potential matches
✅ Cross-references profile details with person info
✅ Provides confidence scoring and reasoning
✅ Handles name variations and nicknames
✅ Can identify profiles even without direct mentions
✅ Learns from context clues (company, location, etc.)

**Example Scenarios Where AI Excels:**
1. Person mentions "Senior Engineer @TechCorp" → AI searches "Name TechCorp LinkedIn"
2. Bio says "Former Googler" → AI knows to search for Google in LinkedIn profiles  
3. Location helps disambiguate between multiple people with same name
4. AI can spot inconsistencies that suggest wrong profile
5. Provides reasoning: "High confidence because profile shows TechCorp employment and SF location matches Twitter bio"
""")


def main():
    """Main testing function."""
    
    success = test_ai_linkedin_discovery()
    
    if success:
        print("\n🎉 AI LinkedIn discovery test completed!")
    else:
        print("\n💡 To enable AI LinkedIn discovery:")
        print("1. Add your OpenAI API key to .env file:")
        print("   OPENAI_API_KEY=your_key_here")
        print("2. The system will then use AI + web search for accurate profile discovery")
    
    compare_approaches()
    
    print("\n🚀 Next Steps:")
    print("- Integrate this into your main conversation processing workflow")
    print("- AI will automatically find LinkedIn profiles for each Twitter user")
    print("- Much higher accuracy than pattern matching alone!")


if __name__ == "__main__":
    main()
