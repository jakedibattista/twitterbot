"""LinkedIn profile discovery using Gemini with Google Search."""

from typing import Optional
import structlog
import re
import os
from src.config.settings import settings

# Try to use the Google AI SDK (generativeai)
GEMINI_SDK_AVAILABLE = False
try:
    import google.generativeai as genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    genai = None

logger = structlog.get_logger()


def validate_linkedin_url(url: str) -> bool:
    """Validate if a LinkedIn URL is properly formatted.
    
    Args:
        url: LinkedIn URL to validate.
        
    Returns:
        True if URL appears to be a valid LinkedIn profile URL.
    """
    if not url:
        return False
    
    # Basic LinkedIn URL pattern validation
    linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?$'
    return bool(re.match(linkedin_pattern, url, re.IGNORECASE))


def find_linkedin_profile(
    real_name: str,
    location: Optional[str] = None,
    website: Optional[str] = None,
    conversation_summary: Optional[str] = None
) -> Optional[str]:
    """Find LinkedIn profile prioritizing Google Search results over AI generation.
    
    This function now prioritizes reliable Google search results over AI-generated
    answers to reduce hallucinations and improve accuracy.
    
    Args:
        real_name: Person's real name.
        location: Location if available.
        website: Website if available.
        conversation_summary: Summary of the conversation.
    
    Returns:
        LinkedIn URL if found, else None.
    """
    # Build simple search query - complex queries often return no results
    query = f'site:linkedin.com/in "{real_name}"'
    # Note: We avoid adding website/location to keep query simple and effective
    
    logger.info("Prioritizing Google search over AI generation", query=query, name=real_name)
    
    # PRIORITY 1: Try Google search methods first (most reliable)
    google_result = _try_google_search_methods(query)
    if google_result:
        logger.info("Found LinkedIn profile via Google search", url=google_result)
        return google_result
    
    # PRIORITY 2: Only use AI as backup if Google search fails completely
    api_key = getattr(settings, 'google_ai_api_key', None)
    if not api_key or not GEMINI_SDK_AVAILABLE:
        logger.warning("Google search failed and Gemini unavailable. Set GOOGLE_AI_API_KEY in .env and install google-generativeai.")
        return _generate_manual_search_url(query)
    
    try:
        logger.info("Google search failed, trying AI as backup", name=real_name)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Use simpler query for better results - just name + site
        search_query = f'site:linkedin.com/in "{real_name}"'
        
        prompt = (
            f"I need to find the LinkedIn profile for: {real_name}\n"
            f"Additional context:\n"
            f"- Location: {location or 'Unknown'}\n"
            f"- Website: {website or 'Unknown'}\n"
            f"- Conversation context: {conversation_summary or 'Unknown'}\n\n"
            f"Please search for: {search_query}\n\n"
            f"Look through the search results and find the most likely LinkedIn profile URL. "
            f"Return ONLY the complete LinkedIn URL starting with https://www.linkedin.com/in/ "
            f"or return 'NOT_FOUND' if you cannot find a suitable match."
        )
        
        logger.info("Using AI as backup for LinkedIn profile search", name=real_name, query=search_query)
        
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        logger.info("AI backup response", response=response_text)
        
        # Extract LinkedIn URL from response
        url_match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[\w\-_/]+/?', response_text, re.IGNORECASE)
        if url_match:
            candidate_url = url_match.group(0).rstrip('/')
            
            # Verify URL format is correct
            if validate_linkedin_url(candidate_url):
                logger.info("Found LinkedIn URL via AI backup", url=candidate_url)
                return candidate_url
            else:
                logger.warning("Invalid LinkedIn URL format from AI", url=candidate_url)
        
        # If no valid URL found in response, generate manual search URL
        if "NOT_FOUND" not in response_text.upper():
            logger.warning("No LinkedIn URL found in AI response")
        
        return _generate_manual_search_url(query)
    
    except Exception as e:
        logger.error("AI backup discovery failed", error=str(e))
        return _generate_manual_search_url(query)

def _try_google_search_methods(query: str) -> Optional[str]:
    """Try all Google search methods in order of reliability."""
    logger.info("Attempting Google search methods", query=query)
    
    # Try Google Custom Search API first (most reliable)
    api_result = _google_custom_search(query)
    if api_result:
        return api_result
    
    # Try googlesearch-python library (simple and works well)
    library_result = _googlesearch_library(query)
    if library_result:
        return library_result
    
    # Try automated scraping as backup
    automated_result = _automated_google_search(query)
    if automated_result:
        return automated_result
    
    logger.info("All Google search methods failed")
    return None


def _generate_manual_search_url(query: str) -> str:
    """Generate a manual Google search URL as final fallback."""
    import urllib.parse
    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://www.google.com/search?q={encoded_query}"
    
    logger.info("Generated manual search URL", query=query, url=search_url)
    return search_url


def fallback_google_search(
    real_name: str,
    location: Optional[str] = None,
    website: Optional[str] = None,
    conversation_summary: Optional[str] = None
) -> Optional[str]:
    """Legacy fallback function - now redirects to prioritized search."""
    # Build simple search query - complex queries often return no results
    query = f'site:linkedin.com/in "{real_name}"'
    # Note: We avoid adding website/location to keep query simple and effective
    
    logger.info("Using legacy fallback (redirecting to prioritized search)", query=query)
    
    # Try Google search methods
    google_result = _try_google_search_methods(query)
    if google_result:
        return google_result
    
    # Return manual search URL if all automation fails
    return _generate_manual_search_url(query)


def _googlesearch_library(query: str) -> Optional[str]:
    """Use googlesearch-python library to get first result."""
    try:
        from googlesearch import search
        
        logger.info("Using googlesearch-python library", query=query)
        
        # Search for first 3 results (simple approach)
        results = []
        try:
            # Try the simplest API first
            for result in search(query):
                results.append(result)
                if len(results) >= 3:  # Only get first 3 results
                    break
        except Exception as e:
            logger.debug("Simple search failed, trying alternative", error=str(e))
            # Alternative approach
            results = search(query, advanced=False, num_results=3)
        
        # Find first LinkedIn URL
        for url in results:
            if 'linkedin.com/in/' in url and validate_linkedin_url(url):
                logger.info("Found LinkedIn URL via googlesearch library", url=url)
                return url
        
        logger.info("No LinkedIn URLs found via googlesearch library")
        return None
        
    except ImportError:
        logger.debug("googlesearch-python library not available")
        return None
    except Exception as e:
        logger.warning("googlesearch library failed", error=str(e))
        return None


def _google_custom_search(query: str) -> Optional[str]:
    """Use Google Custom Search API for reliable results (requires API key)."""
    try:
        # Check if Custom Search API credentials are available
        cse_api_key = getattr(settings, 'google_cse_api_key', None)
        cse_cx = getattr(settings, 'google_cse_cx', None)
        
        if not cse_api_key or not cse_cx:
            logger.debug("Google Custom Search API not configured, skipping")
            return None
        
        import requests
        
        # Use the already simplified query as-is
        # The query is now already optimized: site:linkedin.com/in "Name"
        simple_query = query
        
        # Make API request
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': cse_api_key,
            'cx': cse_cx,
            'q': simple_query,
            'num': 5  # Get first 5 results for better chance of success
        }
        
        logger.info("Making Google Custom Search API request", query=query)
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Look for LinkedIn URLs in the results
        if 'items' in data:
            for item in data['items']:
                link = item.get('link', '')
                if 'linkedin.com/in/' in link and validate_linkedin_url(link):
                    logger.info("Found LinkedIn URL via Custom Search API", url=link)
                    return link
        
        logger.info("No LinkedIn URLs found in Custom Search API results")
        return None
        
    except Exception as e:
        logger.warning("Google Custom Search API failed", error=str(e))
        return None


def _automated_google_search(query: str) -> Optional[str]:
    """Attempt to automatically get the first LinkedIn result from Google."""
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        import time
        
        # Add random delay to avoid being flagged as bot
        import random
        delay = random.uniform(3, 8)  # Random delay between 3-8 seconds
        time.sleep(delay)
        
        # Use realistic headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Construct search URL
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded_query}&num=5"
        
        logger.info("Making automated Google search request", url=search_url)
        
        # Make the request
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for LinkedIn URLs in search results using multiple strategies
        linkedin_urls = []
        
        # Strategy 1: Look in all href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Google wraps URLs in /url?q= format
            if '/url?q=' in href and 'linkedin.com/in/' in href:
                try:
                    # Extract the actual URL
                    actual_url = href.split('/url?q=')[1].split('&')[0]
                    actual_url = urllib.parse.unquote(actual_url)
                    
                    # Validate it's a proper LinkedIn profile URL
                    if 'linkedin.com/in/' in actual_url and len(actual_url) > 20:
                        linkedin_urls.append(actual_url)
                except (IndexError, ValueError):
                    continue
            
            # Also check direct LinkedIn URLs (sometimes Google shows them directly)
            elif 'linkedin.com/in/' in href and href.startswith('http'):
                if len(href) > 20:
                    linkedin_urls.append(href)
        
        # Strategy 2: Look in text content for LinkedIn URLs
        page_text = soup.get_text()
        import re
        text_urls = re.findall(r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?', page_text)
        linkedin_urls.extend(text_urls)
        
        # Strategy 3: Look in cite tags (Google sometimes puts URLs there)
        for cite in soup.find_all('cite'):
            cite_text = cite.get_text()
            if 'linkedin.com/in/' in cite_text:
                # Reconstruct full URL if needed
                if cite_text.startswith('linkedin.com'):
                    cite_text = 'https://www.' + cite_text
                elif cite_text.startswith('www.linkedin.com'):
                    cite_text = 'https://' + cite_text
                linkedin_urls.append(cite_text)
        
        # Return the first valid LinkedIn URL found
        for url in linkedin_urls:
            # Clean and validate the URL
            clean_url = url.strip().rstrip('/')
            if validate_linkedin_url(clean_url):
                logger.info("Found LinkedIn URL via automated search", url=clean_url)
                return clean_url
        
        # Debug: log what we found for troubleshooting
        logger.info("Debug: Found potential URLs", urls=linkedin_urls[:3])
        
        logger.warning("No LinkedIn URLs found in search results")
        return None
        
    except requests.RequestException as e:
        logger.warning("HTTP request failed during automated search", error=str(e))
        return None
    except Exception as e:
        logger.warning("Automated Google search failed", error=str(e))
        return None

def test_prioritized_linkedin_discovery():
    """Test the prioritized LinkedIn discovery with Google search first."""
    
    print("🔍 Testing Prioritized LinkedIn Discovery")
    print("="*50)
    print("Note: Now prioritizing Google search over AI generation")
    
    # Test with sample information
    print("Testing with sample information...")
    
    result = find_linkedin_profile(
        real_name="Jake Dibattista",
        location="Charleston",
        conversation_summary="Patriots fan, UX Fiend, Screenwriter, Traveler, Gamer. Part-time Serbian, full time Italian American."
    )
    
    print("\n📊 Discovery Results:")
    print("="*30)
    print(f"Result: {result or 'Not found'}")
    print("\nThis result comes from:")
    print("1. Google Custom Search API (if configured)")
    print("2. googlesearch-python library")
    print("3. Automated Google scraping")
    print("4. AI generation (only as backup)")
    
    return result is not None


if __name__ == "__main__":
    test_prioritized_linkedin_discovery()


