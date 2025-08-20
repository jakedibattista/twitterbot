"""LinkedIn profile discovery utilities.

Optional enhanced LinkedIn discovery methods beyond basic URL extraction.
These methods can help find LinkedIn profiles when not directly listed in bio.
"""

from typing import Optional, Dict, Any
import re
import structlog
from urllib.parse import quote_plus

logger = structlog.get_logger()


class LinkedInDiscovery:
    """Enhanced LinkedIn profile discovery methods."""
    
    @staticmethod
    def suggest_linkedin_search_url(name: str, location: Optional[str] = None) -> str:
        """Generate a LinkedIn search URL for manual verification.
        
        Args:
            name: Real name of the person.
            location: Location if available.
            
        Returns:
            LinkedIn search URL that can be manually checked.
        """
        # Clean the name for search
        clean_name = re.sub(r'[^\w\s]', '', name).strip()
        search_query = quote_plus(clean_name)
        
        if location:
            clean_location = re.sub(r'[^\w\s]', '', location).strip()
            search_query += f"%20{quote_plus(clean_location)}"
        
        return f"https://www.linkedin.com/search/results/people/?keywords={search_query}"
    
    @staticmethod
    def extract_company_from_bio(bio: str) -> Optional[str]:
        """Extract company information from bio that could help with LinkedIn search.
        
        Args:
            bio: User's bio/description.
            
        Returns:
            Company name if found, None otherwise.
        """
        if not bio:
            return None
        
        # Common patterns for company mentions
        company_patterns = [
            r'(?:@|at)\s+([A-Z][a-zA-Z0-9\s&]+?)(?:\s|$|,|\.|!)',  # @Company or at Company
            r'(?:CEO|CTO|VP|Director|Manager|Lead|Head)\s+(?:of|at)\s+([A-Z][a-zA-Z0-9\s&]+?)(?:\s|$|,|\.|!)',
            r'(?:Founder|Co-founder|Co-Founder)\s+(?:of|at)?\s*([A-Z][a-zA-Z0-9\s&]+?)(?:\s|$|,|\.|!)',
            r'(?:Working|Works)\s+(?:at|for)\s+([A-Z][a-zA-Z0-9\s&]+?)(?:\s|$|,|\.|!)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                # Clean up common suffixes/prefixes
                company = re.sub(r'\s+(Inc|LLC|Corp|Ltd|Co)\.?$', '', company, flags=re.IGNORECASE)
                if len(company) > 2 and len(company) < 50:  # Reasonable company name length
                    return company
        
        return None
    
    @staticmethod
    def generate_linkedin_suggestions(
        name: str, 
        username: str,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate multiple LinkedIn discovery suggestions.
        
        Args:
            name: Real name of the person.
            username: Twitter username.
            bio: User's bio.
            location: User's location.
            website: User's website.
            
        Returns:
            Dictionary with different search strategies and URLs.
        """
        suggestions = {}
        
        # Basic name search
        suggestions["name_search"] = LinkedInDiscovery.suggest_linkedin_search_url(name, location)
        
        # Company-based search if we can extract company
        if bio:
            company = LinkedInDiscovery.extract_company_from_bio(bio)
            if company:
                company_search = LinkedInDiscovery.suggest_linkedin_search_url(f"{name} {company}")
                suggestions["company_search"] = company_search
        
        # Username-based search (sometimes people use same username)
        clean_username = username.replace("_", " ").replace("-", " ")
        suggestions["username_search"] = LinkedInDiscovery.suggest_linkedin_search_url(clean_username)
        
        # Google search suggestion for LinkedIn profile
        google_query = quote_plus(f'"{name}" site:linkedin.com/in')
        if location:
            google_query += f" {quote_plus(location)}"
        suggestions["google_search"] = f"https://www.google.com/search?q={google_query}"
        
        return suggestions
    
    @staticmethod
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
        linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?'
        return bool(re.match(linkedin_pattern, url, re.IGNORECASE))
    
    @staticmethod
    def create_discovery_summary(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary with LinkedIn discovery information.
        
        Args:
            user_data: Dictionary with user information.
            
        Returns:
            Enhanced user data with LinkedIn discovery suggestions.
        """
        name = user_data.get("real_name", "")
        username = user_data.get("username", "")
        bio = user_data.get("bio", "")
        location = user_data.get("location", "")
        linkedin_url = user_data.get("linkedin_url", "")
        
        discovery_data = user_data.copy()
        
        # If we already have a LinkedIn URL, validate it
        if linkedin_url:
            discovery_data["linkedin_validated"] = LinkedInDiscovery.validate_linkedin_url(linkedin_url)
        else:
            discovery_data["linkedin_validated"] = False
            
            # Generate search suggestions if no LinkedIn found
            if name and name != "Unknown":
                suggestions = LinkedInDiscovery.generate_linkedin_suggestions(
                    name, username, bio, location
                )
                discovery_data["linkedin_suggestions"] = suggestions
                
                # Add the primary suggestion as a searchable field
                discovery_data["linkedin_search_url"] = suggestions.get("name_search", "")
        
        # Extract company for additional context
        if bio:
            company = LinkedInDiscovery.extract_company_from_bio(bio)
            if company:
                discovery_data["extracted_company"] = company
        
        return discovery_data
