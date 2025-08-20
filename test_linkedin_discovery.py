#!/usr/bin/env python3
"""Test LinkedIn profile discovery with sample user data.

This tests the LinkedIn URL extraction and discovery features
using sample profile data that mimics real Twitter profiles.
"""

import sys
from pathlib import Path
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.twitter.models import User
from src.linkedin_discovery import LinkedInDiscovery


def create_sample_profiles():
    """Create sample user profiles with different LinkedIn patterns."""
    
    profiles = [
        {
            "username": "johndoe_dev",
            "name": "John Doe",
            "description": "Senior Software Engineer @TechCorp | AI enthusiast | Building the future with Python 🐍 | LinkedIn: linkedin.com/in/johndoe-dev",
            "url": "https://johndoe.dev",
            "location": "San Francisco, CA"
        },
        {
            "username": "sarahtech",
            "name": "Sarah Johnson",
            "description": "CTO at StartupXYZ | Former @Google engineer | Passionate about ML and distributed systems",
            "url": "https://www.linkedin.com/in/sarah-johnson-tech",
            "location": "New York, NY"
        },
        {
            "username": "alexcoder",
            "name": "Alex Chen",
            "description": "Full-stack developer | React & Node.js expert | @linkedin: alexchen-dev | Open source contributor",
            "url": "https://alexchen.blog",
            "location": "Seattle, WA"
        },
        {
            "username": "mariaml",
            "name": "Maria Rodriguez",
            "description": "Lead Data Scientist at DataFlow Inc | PhD in Machine Learning | Founder of WomenInTech meetup",
            "url": None,
            "location": "Austin, TX"
        },
        {
            "username": "davidstartup",
            "name": "David Kim",
            "description": "Co-founder & CEO @InnovateLabs | Building the next generation of productivity tools | linkedin.com/in/david-kim-ceo",
            "url": "https://innovatelabs.com",
            "location": "Los Angeles, CA"
        }
    ]
    
    return profiles


def test_linkedin_extraction(profile_data):
    """Test LinkedIn extraction for a single profile."""
    
    print(f"\n{'='*60}")
    print(f"🔍 TESTING: @{profile_data['username']} ({profile_data['name']})")
    print(f"{'='*60}")
    
    # Create User object
    user = User(
        id=f"fake_id_{profile_data['username']}",
        username=profile_data['username'],
        name=profile_data['name'],
        description=profile_data['description'],
        url=profile_data['url'],
        location=profile_data['location'],
        verified=False
    )
    
    print(f"📍 Location: {user.location}")
    print(f"🌐 Website: {user.url or 'None'}")
    print(f"📝 Bio: {user.description}")
    
    # Test LinkedIn extraction
    linkedin_url = user.linkedin_url  # This calls _extract_linkedin_url()
    
    print(f"\n🔗 LINKEDIN DISCOVERY RESULTS:")
    if linkedin_url:
        print(f"✅ LinkedIn Found: {linkedin_url}")
        
        # Validate the URL
        is_valid = LinkedInDiscovery.validate_linkedin_url(linkedin_url)
        print(f"✅ URL Valid: {is_valid}")
    else:
        print("❌ No LinkedIn URL found in bio or website")
    
    # Test company extraction
    company = LinkedInDiscovery.extract_company_from_bio(user.description)
    if company:
        print(f"🏢 Company Detected: {company}")
    
    # Generate search suggestions
    suggestions = LinkedInDiscovery.generate_linkedin_suggestions(
        user.name, 
        user.username,
        user.description,
        user.location,
        user.url
    )
    
    print(f"\n🔍 SEARCH SUGGESTIONS:")
    for search_type, url in suggestions.items():
        print(f"  {search_type.replace('_', ' ').title()}: {url}")
    
    return linkedin_url is not None


def test_custom_profile(username, name, bio, website=None, location=None):
    """Test LinkedIn discovery for a custom profile."""
    
    profile_data = {
        "username": username,
        "name": name,
        "description": bio,
        "url": website,
        "location": location
    }
    
    return test_linkedin_extraction(profile_data)


def main():
    """Main testing function."""
    print("🔗 LinkedIn Profile Discovery Testing")
    print("="*60)
    print("Testing the enhanced LinkedIn discovery features")
    
    # Test with sample profiles
    print("\n🧪 TESTING WITH SAMPLE PROFILES:")
    
    sample_profiles = create_sample_profiles()
    success_count = 0
    
    for profile in sample_profiles:
        found_linkedin = test_linkedin_extraction(profile)
        if found_linkedin:
            success_count += 1
    
    print(f"\n📊 RESULTS: Found LinkedIn for {success_count}/{len(sample_profiles)} sample profiles")
    
    # Test with custom profile
    print(f"\n{'='*60}")
    print("🎯 CUSTOM PROFILE TESTING")
    print("="*60)
    print("Enter a Twitter profile to test LinkedIn discovery:")
    
    username = input("Twitter username (without @): ").strip()
    if username:
        name = input("Real name: ").strip()
        bio = input("Bio/description: ").strip()
        website = input("Website URL (optional): ").strip() or None
        location = input("Location (optional): ").strip() or None
        
        if name and bio:
            print(f"\n🔍 Testing custom profile...")
            test_custom_profile(username, name, bio, website, location)
        else:
            print("❌ Need at least username, name, and bio to test")
    
    print(f"\n{'='*60}")
    print("✅ LinkedIn Discovery Testing Complete!")
    print("="*60)
    print("The system can detect LinkedIn URLs from:")
    print("• Direct LinkedIn URLs in bio")
    print("• LinkedIn URLs as website")
    print("• @linkedin: username patterns")
    print("• linkedin: username patterns")
    print("• Company names for enhanced search")
    print("• Generate targeted search URLs")


if __name__ == "__main__":
    main()
