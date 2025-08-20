"""LinkedIn profile discovery using Gemini with Google Search grounding only.

This implementation requires the new Google AI SDK (`google.genai`) and uses
the `google_search` tool per docs: https://ai.google.dev/gemini-api/docs/google-search
No non-grounded or legacy fallbacks are used.
"""

from typing import Optional, Dict, Any, List
import structlog
import json
import re
import requests
from config.settings import settings

# Try to use the new Google AI SDK (grounded search) if available
NEW_GEMINI_SDK_AVAILABLE = False
try:
    from google import genai as genai_new
    from google.genai import types as genai_types
    NEW_GEMINI_SDK_AVAILABLE = True
except Exception:
    genai_new = None
    genai_types = None

logger = structlog.get_logger()


class GeminiLinkedInDiscovery:
    """Real LinkedIn profile discovery using Google Gemini with web search."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini LinkedIn discovery service.
        
        Args:
            api_key: Google AI API key. If None, uses GOOGLE_AI_API_KEY from settings.
        """
        self.api_key = api_key or getattr(settings, 'google_ai_api_key', None)
        self._new_client = None  # new SDK client
        self._model_name = 'gemini-2.5-flash'
        
        if self.api_key:
            self._setup_client()
        else:
            logger.warning("No Google AI API key provided. Add GOOGLE_AI_API_KEY to your .env file")
    
    def _setup_client(self) -> None:
        """Set up Gemini client with API key."""
        try:
            if NEW_GEMINI_SDK_AVAILABLE:
                # New SDK client supports google_search grounding tool
                self._new_client = genai_new.Client(api_key=self.api_key) if self.api_key else genai_new.Client()
                logger.info("Gemini new SDK client initialized (grounded search enabled)")
            else:
                raise RuntimeError("Google AI new SDK not available; grounded search required")
        except Exception as e:
            logger.error("Failed to initialize Gemini client", error=str(e))
            self._new_client = None
    
    def find_linkedin_profile_with_search(
        self,
        name: str,
        username: str,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None,
        company: Optional[str] = None,
        max_attempts: int = 5
    ) -> Dict[str, Any]:
        """Use Gemini to find LinkedIn profile with real web search.
        
        Args:
            name: Real name of the person.
            username: Twitter username.
            bio: Conversation summary or Twitter bio/description (context to disambiguate).
            location: User's location.
            website: User's website.
            company: Extracted company name.
            
        Returns:
            Dictionary with LinkedIn discovery results.
        """
        if not self._new_client:
            return {
                "linkedin_url": None,
                "search_performed": False,
                "raw_response": "",
                "method": "Gemini grounded (unavailable)"
            }
        
        try:
            # Iteratively generate and self-evaluate until PASS or attempts exhausted
            last_response_text = ""
            candidate_url: Optional[str] = None
            for attempt in range(1, max_attempts + 1):
                prompt = self._build_search_prompt(name, username, bio, location, website, company)
                if last_response_text:
                    prompt += f"\n\nPrevious attempt output: {last_response_text.strip()}\nIf that was NOT_FOUND or a mismatch, try an alternative likely LinkedIn slug variation."

                # Generate content (grounded search via new SDK only)
                temperature = 0.0
                try:
                    tool = genai_types.Tool(google_search=genai_types.GoogleSearch())
                    config = genai_types.GenerateContentConfig(tools=[tool], temperature=temperature)
                    resp = self._new_client.models.generate_content(
                        model=self._model_name,
                        contents=prompt,
                        config=config,
                    )
                    last_response_text = getattr(resp, 'text', '') or ''
                except Exception as ge:
                    logger.error("Grounded search call failed", error=str(ge))
                    last_response_text = ""
                parsed = self._parse_gemini_response(last_response_text, name, username)
                candidate_url = parsed.get("linkedin_url")

                if not candidate_url:
                    continue

                # Self-evaluate PASS/FAIL for candidate
                eval_prompt = self._build_evaluator_prompt(name, username, bio, location, company, candidate_url)
                eval_resp = self._new_client.models.generate_content(
                    model=self._model_name,
                    contents=eval_prompt,
                    config=genai_types.GenerateContentConfig(temperature=0.0),
                )
                decision = (getattr(eval_resp, 'text', '') or '').strip().upper()
                if decision.startswith("PASS") or decision in {"YES", "PASS", "TRUE"}:
                    logger.info("Gemini iterative discovery PASS", candidate=candidate_url)
                    return {
                        "linkedin_url": candidate_url,
                        "search_performed": True,
                        "raw_response": last_response_text,
                        "method": "Gemini (iterative)"
                    }
                # Otherwise, try another variation

            # Attempts exhausted; return last candidate (may be None)
            return {
                "linkedin_url": candidate_url,
                "search_performed": True,
                "raw_response": last_response_text,
                "method": "Gemini (iterative, no PASS)"
            }
            
        except Exception as e:
            logger.error("Gemini LinkedIn discovery failed", error=str(e), name=name, username=username)
            return self._fallback_search_urls(name, username, bio, location, website)
    
    def _build_search_prompt(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        website: Optional[str],
        company: Optional[str]
    ) -> str:
        """Build the search prompt for Gemini.
        
        Args:
            name: Person's real name.
            username: Twitter username.
            bio: Twitter bio.
            location: User's location.
            website: User's website.
            company: Extracted company.
            
        Returns:
            Formatted prompt for Gemini.
        """
        # Use only name and company per user instruction
        target_company = (company or "").strip()
        name_clean = name.strip()

        # If company missing, just search by name
        if not target_company:
            query_line = f"Do a Google search on {name_clean} and return only their LinkedIn profile URL."
        else:
            query_line = f"Do a Google search on {name_clean} at {target_company} and return only their LinkedIn profile URL."

        prompt = (
            f"{query_line}\n\n"
            "Rules:\n"
            "- Output ONLY the LinkedIn profile URL on a single line (format: https://www.linkedin.com/in/...).\n"
            "- No extra text, no explanation, no code fences.\n"
            "- If you only infer a partial path (e.g., in/jane-doe-1234), output the full URL as https://www.linkedin.com/{that_path}.\n"
            "- If you cannot find a confident match, output exactly: NOT_FOUND.\n"
        )

        return prompt

    def _build_evaluator_prompt(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        company: Optional[str],
        candidate_url: str
    ) -> str:
        """Build a PASS/FAIL evaluator prompt for a candidate URL."""
        loc = location or "Unknown"
        ctx = bio or ""
        comp = company or ""
        return (
            "Evaluate whether this LinkedIn URL most likely matches the person described.\n"
            f"Name: {name}\n"
            f"Twitter: @{username}\n"
            f"Location: {loc}\n"
            f"Context: {ctx}\n"
            f"Company: {comp}\n"
            f"Candidate: {candidate_url}\n\n"
            "Rules:\n"
            "- Output ONLY PASS or FAIL on a single line.\n"
            "- PASS if the slug or profile pattern strongly matches the name (e.g., jake-dibattista) and context corroborates; else FAIL."
        )
    
    def _parse_gemini_response(self, response_text: str, name: str, username: str) -> Dict[str, Any]:
        """Parse Gemini response to extract LinkedIn information.
        
        Args:
            response_text: Raw response from Gemini.
            name: Person's name for logging.
            username: Twitter username for logging.
            
        Returns:
            Parsed LinkedIn discovery results.
        """
        try:
            # Expect a single line with the URL or NOT_FOUND. Still robustly extract URL if extra text appears.
            linkedin_url = None
            # First, try to find a linkedin.com/in URL anywhere in the text
            url_search = re.search(r'https?://(?:www\.)?linkedin\.com/in/[\w\-_/]+', response_text, re.IGNORECASE)
            if url_search:
                linkedin_url = url_search.group(0).strip()
            else:
                # Accept bare domain paths too
                bare_match = re.search(r'linkedin\.com/in/[\w\-_/]+', response_text, re.IGNORECASE)
                if bare_match:
                    linkedin_url = f"https://www.{bare_match.group(0).strip()}"
                else:
                    # Accept partial paths like "in/slug" or "/in/slug"
                    partial_match = re.search(r'\b/?in/[\w\-_/]+', response_text, re.IGNORECASE)
                    if partial_match:
                        path = partial_match.group(0).lstrip('/')
                        linkedin_url = f"https://www.linkedin.com/{path}"

            # NOT_FOUND handling
            if not linkedin_url and response_text.strip().upper().startswith("NOT_FOUND"):
                linkedin_url = None

            result = {
                "linkedin_url": linkedin_url,
                "search_performed": True,
                "raw_response": response_text,
                "method": "Gemini (URL-only)"
            }
            
            return result
            
        except Exception as e:
            logger.error("Failed to parse Gemini response", error=str(e))
            return {
                "linkedin_url": None,
                "raw_response": response_text,
                "search_performed": False,
                "method": "Gemini (parsing failed)"
            }
    
    def _fallback_search_urls(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        website: Optional[str]
    ) -> Dict[str, Any]:
        """Generate search URLs when Gemini is unavailable."""
        
        search_urls = []
        
        # Google search URLs that user can manually check
        base_searches = [
            f'"{name}" linkedin',
            f'"{name}" linkedin {location}' if location else f'"{name}" linkedin',
            f'"{username}" twitter linkedin',
            f'site:linkedin.com/in "{name}"',
        ]
        
        for search in base_searches:
            google_url = f"https://www.google.com/search?q={search.replace(' ', '+').replace('\"', '%22')}"
            search_urls.append(google_url)
        
        return {
            "linkedin_url": None,
            "confidence": "Manual Search Required",
            "reasoning": "Gemini API unavailable. Use the provided search URLs to manually find the LinkedIn profile.",
            "search_urls": search_urls,
            "search_performed": False,
            "method": "Manual search URLs (Gemini unavailable)"
        }


def test_gemini_linkedin_discovery():
    """Test the Gemini LinkedIn discovery with a real example."""
    
    print("🔍 Testing Gemini LinkedIn Discovery with Real Web Search")
    print("="*70)
    
    discovery = GeminiLinkedInDiscovery()
    
    if not discovery.model:
        print("❌ Gemini not available. To use this feature:")
        print("1. Get a Google AI API key from: https://makersuite.google.com/app/apikey")
        print("2. Add GOOGLE_AI_API_KEY=your_key_here to your .env file")
        print("3. Install: pip install google-generativeai")
        return False
    
    # Test with the corrected information
    print("Testing with Jake's actual information...")
    
    result = discovery.find_linkedin_profile_with_search(
        name="Jake Dibattista",
        username="jakediba", 
        bio="Patriots fan, UX Fiend, Screenwriter, Traveler, Gamer. Part-time Serbian, full time Italian American.",
        location="Charleston",
        website=None
    )
    
    print("\n📊 Gemini Discovery Results:")
    print("="*50)
    print(f"LinkedIn URL: {result.get('linkedin_url') or 'Not found'}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Method: {result.get('method')}")
    
    if result.get('reasoning'):
        print(f"\nReasoning: {result['reasoning']}")
    
    if result.get('search_queries'):
        print(f"\nSearch Queries Used:")
        for i, query in enumerate(result['search_queries'], 1):
            print(f"  {i}. {query}")
    
    if result.get('search_urls'):
        print(f"\nManual Search URLs:")
        for i, url in enumerate(result['search_urls'], 1):
            print(f"  {i}. {url}")
    
    return True


if __name__ == "__main__":
    test_gemini_linkedin_discovery()
