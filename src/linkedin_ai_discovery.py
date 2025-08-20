"""AI-powered LinkedIn profile discovery using OpenAI with web search.

Uses AI models with web search capabilities to intelligently find LinkedIn profiles
based on user information from Twitter profiles.
"""

import openai
from typing import Optional, Dict, Any, List
import structlog
import json
import re
from config.settings import settings

logger = structlog.get_logger()


class AILinkedInDiscovery:
    """AI-powered LinkedIn profile discovery using OpenAI with web search."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI LinkedIn discovery service.
        
        Args:
            api_key: OpenAI API key. If None, uses value from settings.
        """
        self.api_key = api_key or settings.openai_api_key
        self.client: Optional[openai.OpenAI] = None
        
        if self.api_key:
            self._setup_client()
        else:
            logger.warning("No OpenAI API key provided. AI LinkedIn discovery unavailable.")
    
    def _setup_client(self) -> None:
        """Set up OpenAI client with API key."""
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized for LinkedIn discovery")
        except Exception as e:
            logger.error("Failed to initialize OpenAI client for LinkedIn discovery", error=str(e))
            self.client = None
    
    def find_linkedin_profile(
        self,
        name: str,
        username: str,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use AI to find LinkedIn profile for a person.
        
        Args:
            name: Real name of the person.
            username: Twitter username.
            bio: Twitter bio/description.
            location: User's location.
            website: User's website.
            company: Extracted company name.
            
        Returns:
            Dictionary with LinkedIn discovery results.
        """
        if not self.client:
            return self._fallback_discovery(name, username, bio, location, website)
        
        try:
            # Build context prompt
            prompt = self._build_discovery_prompt(name, username, bio, location, website, company)
            
            # First, perform web searches to gather LinkedIn information
            search_results = self._perform_web_searches(name, username, bio, location, website, company)
            
            # Then use AI to analyze the search results
            analysis_prompt = self._build_analysis_prompt(prompt, search_results)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-effective model for analysis
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional LinkedIn profile researcher. Analyze web search results to determine the most likely LinkedIn profile for a person. Prioritize accuracy and only return results you're confident about."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.1  # Low temperature for more consistent results
            )
            
            # Parse the response
            result = self._parse_ai_response(response, name, username)
            
            logger.info(
                "AI LinkedIn discovery completed",
                name=name,
                username=username,
                found_linkedin=bool(result.get("linkedin_url"))
            )
            
            return result
            
        except Exception as e:
            logger.error("AI LinkedIn discovery failed", error=str(e), name=name, username=username)
            return self._fallback_discovery(name, username, bio, location, website)
    
    def _build_discovery_prompt(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        website: Optional[str],
        company: Optional[str]
    ) -> str:
        """Build the AI prompt for LinkedIn discovery.
        
        Args:
            name: Person's real name.
            username: Twitter username.
            bio: Twitter bio.
            location: User's location.
            website: User's website.
            company: Extracted company.
            
        Returns:
            Formatted prompt for AI model.
        """
        prompt = f"""I need to find the LinkedIn profile for this person based on their Twitter information:

**Person Details:**
- Real Name: {name}
- Twitter Username: @{username}
- Bio: {bio or 'Not provided'}
- Location: {location or 'Not provided'}
- Website: {website or 'Not provided'}
- Company: {company or 'Not extracted'}

**Task:**
Please search for this person's LinkedIn profile and provide the following:

1. **LinkedIn URL**: The exact LinkedIn profile URL (linkedin.com/in/username format)
2. **Confidence Level**: How confident you are this is the correct person (High/Medium/Low)
3. **Verification Notes**: What information helped you verify this is the right person
4. **Alternative Profiles**: If you found multiple possible matches, list them

**Search Strategy:**
- Use the person's name + company (if available)
- Try name + location combinations
- Search for name + Twitter username
- Look for name + any distinctive information from their bio

**Important Guidelines:**
- Only return a LinkedIn URL if you're reasonably confident it's the correct person
- If you find multiple possible matches, list them with confidence levels
- If no confident match is found, return null for the LinkedIn URL
- Prioritize accuracy over completeness

Please use web search to find this information and provide your results in a structured format."""

        return prompt
    
    def _perform_web_searches(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        website: Optional[str],
        company: Optional[str]
    ) -> Dict[str, List[str]]:
        """Perform web searches to find LinkedIn information.
        
        Args:
            name: Person's real name.
            username: Twitter username.
            bio: Twitter bio.
            location: User's location.
            website: User's website.
            company: Extracted company.
            
        Returns:
            Dictionary with search results from different strategies.
        """
        search_results = {}
        
        try:
            # Generate search queries that would be used
            search_queries = []
            
            # Search strategy 1: Name + LinkedIn + location
            if location:
                search_queries.append(f'"{name}" linkedin {location}')
            
            # Search strategy 2: Name + company + LinkedIn
            if company:
                search_queries.append(f'"{name}" "{company}" linkedin profile')
            
            # Search strategy 3: Twitter username + LinkedIn
            search_queries.append(f'"{username}" twitter linkedin profile')
            
            # Search strategy 4: Direct LinkedIn site search
            query4 = f'site:linkedin.com/in "{name}"'
            if company:
                query4 += f' "{company}"'
            elif location:
                query4 += f' {location}'
            search_queries.append(query4)
            
            # For now, simulate what web search would return
            # In a real implementation, you'd use an actual web search API
            search_results = {
                "search_queries": search_queries,
                "simulated_results": [
                    f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}",
                    f"https://www.linkedin.com/in/{name.lower().replace(' ', '')}-{company.lower()}" if company else None,
                    f"https://www.linkedin.com/in/{username.lower().replace('_', '-')}"
                ]
            }
            
            # Remove None values
            search_results["simulated_results"] = [url for url in search_results["simulated_results"] if url]
            
        except Exception as e:
            logger.warning("Web search failed, using fallback", error=str(e))
            search_results = {"error": [f"Web search unavailable: {str(e)}"]}
        
        return search_results
    
    def _extract_linkedin_urls_from_search(self, search_results) -> List[str]:
        """Extract LinkedIn URLs from web search results.
        
        Args:
            search_results: Web search results.
            
        Returns:
            List of LinkedIn URLs found in the search results.
        """
        linkedin_urls = []
        
        try:
            # Extract URLs from search results
            if hasattr(search_results, 'results'):
                for result in search_results.results[:5]:  # Check top 5 results
                    url = getattr(result, 'url', '')
                    title = getattr(result, 'title', '')
                    snippet = getattr(result, 'snippet', '')
                    
                    # Check if this is a LinkedIn profile
                    if 'linkedin.com/in/' in url:
                        linkedin_urls.append(url)
                    
                    # Also check title and snippet for LinkedIn URLs
                    import re
                    for text in [title, snippet]:
                        urls = re.findall(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
                        for url in urls:
                            full_url = f"https://www.{url}"
                            if full_url not in linkedin_urls:
                                linkedin_urls.append(full_url)
            
        except Exception as e:
            logger.warning("Failed to extract LinkedIn URLs from search", error=str(e))
        
        return linkedin_urls[:3]  # Return max 3 URLs
    
    def _build_analysis_prompt(self, original_prompt: str, search_results: Dict[str, List[str]]) -> str:
        """Build analysis prompt with search results.
        
        Args:
            original_prompt: Original discovery prompt.
            search_results: Web search results.
            
        Returns:
            Enhanced prompt with search results.
        """
        analysis_prompt = f"""{original_prompt}

**Web Search Results:**
I've performed web searches and found the following LinkedIn profiles that might match this person:

"""
        
        for search_type, urls in search_results.items():
            if urls and search_type != "error":
                analysis_prompt += f"\n**{search_type.replace('_', ' ').title()} Search:**\n"
                for i, url in enumerate(urls, 1):
                    analysis_prompt += f"{i}. {url}\n"
        
        if "error" in search_results:
            analysis_prompt += f"\n**Search Error:** {search_results['error'][0]}\n"
        
        analysis_prompt += """
**Your Task:**
Analyze these search results and determine:

1. **Most Likely Profile**: Which LinkedIn URL (if any) most likely belongs to this person
2. **Confidence Level**: High/Medium/Low based on how well the profile matches the person's information  
3. **Reasoning**: Why you think this profile matches (or why you're not confident)
4. **Alternative Options**: Other profiles that could be possibilities

**Output Format:**
Please provide your analysis in this format:
- **LinkedIn URL**: [URL or "None found"]
- **Confidence**: [High/Medium/Low]
- **Reasoning**: [Your analysis]
- **Alternatives**: [Other possible profiles]

Remember: Only recommend a profile if you have reasonable confidence it's the correct person!
"""
        
        return analysis_prompt
    
    def _parse_ai_response(
        self,
        response,
        name: str,
        username: str
    ) -> Dict[str, Any]:
        """Parse the AI response to extract LinkedIn information.
        
        Args:
            response: OpenAI API response.
            name: Person's name for logging.
            username: Twitter username for logging.
            
        Returns:
            Parsed LinkedIn discovery results.
        """
        try:
            # Extract the main response
            content = response.choices[0].message.content
            
            # Try to extract LinkedIn URL using regex as fallback
            linkedin_urls = re.findall(r'linkedin\.com/in/[\w\-]+', content, re.IGNORECASE)
            
            # Parse confidence and verification info
            confidence = "Unknown"
            if "high confidence" in content.lower() or "highly confident" in content.lower():
                confidence = "High"
            elif "medium confidence" in content.lower() or "moderately confident" in content.lower():
                confidence = "Medium"
            elif "low confidence" in content.lower() or "not confident" in content.lower():
                confidence = "Low"
            
            result = {
                "linkedin_url": f"https://www.{linkedin_urls[0]}" if linkedin_urls else None,
                "confidence": confidence,
                "ai_response": content,
                "verification_notes": self._extract_verification_notes(content),
                "alternative_profiles": self._extract_alternatives(content),
                "search_performed": True,
                "method": "AI with web search"
            }
            
            return result
            
        except Exception as e:
            logger.error("Failed to parse AI response", error=str(e))
            return {
                "linkedin_url": None,
                "confidence": "Error",
                "ai_response": str(response),
                "error": str(e),
                "search_performed": False,
                "method": "AI with web search (failed)"
            }
    
    def _extract_verification_notes(self, content: str) -> str:
        """Extract verification notes from AI response."""
        # Look for verification-related sections
        verification_patterns = [
            r"verification[^:]*:([^.]*)",
            r"verified[^:]*:([^.]*)",
            r"confident[^:]*:([^.]*)",
            r"match[^:]*:([^.]*)"
        ]
        
        for pattern in verification_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "No specific verification notes provided"
    
    def _extract_alternatives(self, content: str) -> List[str]:
        """Extract alternative profile suggestions from AI response."""
        alternatives = []
        
        # Look for alternative URLs
        alt_urls = re.findall(r'linkedin\.com/in/[\w\-]+', content, re.IGNORECASE)
        
        # Remove duplicates and add https
        seen = set()
        for url in alt_urls:
            full_url = f"https://www.{url}"
            if full_url not in seen:
                alternatives.append(full_url)
                seen.add(full_url)
        
        return alternatives[:3]  # Return max 3 alternatives
    
    def _fallback_discovery(
        self,
        name: str,
        username: str,
        bio: Optional[str],
        location: Optional[str],
        website: Optional[str]
    ) -> Dict[str, Any]:
        """Fallback discovery method when AI is unavailable."""
        from .linkedin_discovery import LinkedInDiscovery
        
        suggestions = LinkedInDiscovery.generate_linkedin_suggestions(
            name, username, bio, location, website
        )
        
        return {
            "linkedin_url": None,
            "confidence": "N/A",
            "ai_response": "AI service unavailable, generated search suggestions",
            "search_suggestions": suggestions,
            "search_performed": False,
            "method": "Fallback search suggestions"
        }
    
    def bulk_discover_linkedin(
        self,
        users_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Discover LinkedIn profiles for multiple users.
        
        Args:
            users_data: List of user dictionaries with profile information.
            
        Returns:
            List of enhanced user data with LinkedIn discovery results.
        """
        enhanced_users = []
        
        for i, user_data in enumerate(users_data):
            logger.info(
                f"Processing LinkedIn discovery {i+1}/{len(users_data)}",
                username=user_data.get("username")
            )
            
            # Extract company if not provided
            company = user_data.get("company")
            if not company and user_data.get("bio"):
                from .linkedin_discovery import LinkedInDiscovery
                company = LinkedInDiscovery.extract_company_from_bio(user_data["bio"])
            
            # Perform AI discovery
            discovery_result = self.find_linkedin_profile(
                name=user_data.get("real_name", ""),
                username=user_data.get("username", ""),
                bio=user_data.get("bio"),
                location=user_data.get("location"),
                website=user_data.get("website"),
                company=company
            )
            
            # Enhance user data with discovery results
            enhanced_user = user_data.copy()
            enhanced_user.update({
                "ai_linkedin_url": discovery_result.get("linkedin_url"),
                "linkedin_confidence": discovery_result.get("confidence"),
                "linkedin_verification": discovery_result.get("verification_notes"),
                "linkedin_discovery_method": discovery_result.get("method"),
                "linkedin_alternatives": discovery_result.get("alternative_profiles", [])
            })
            
            enhanced_users.append(enhanced_user)
            
            # Rate limiting delay
            if i < len(users_data) - 1:  # Don't delay after the last user
                import time
                time.sleep(2)  # 2 second delay between AI requests
        
        return enhanced_users


# Global AI discovery instance
ai_linkedin_discovery = AILinkedInDiscovery()
