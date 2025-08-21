#!/usr/bin/env python3
"""Setup script for LinkedIn discovery functionality.

This script helps verify that all required dependencies and configuration
are properly set up for the LinkedIn discovery feature.
"""

import sys
from pathlib import Path
import subprocess
import os

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

def check_dependencies():
    """Check if required packages are installed."""
    print("🔍 Checking dependencies...")
    
    # Map package names to their import names
    required_packages = {
        "google-generativeai": "google.generativeai",
        "beautifulsoup4": "bs4",
        "googlesearch-python": "googlesearch",
        "requests": "requests",
        "structlog": "structlog",
        "pydantic": "pydantic",
        "pydantic-settings": "pydantic_settings"
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - MISSING")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: uv sync  OR  pip install -e .")
        return False
    
    print("✅ All dependencies installed!")
    return True

def check_configuration():
    """Check if configuration is properly set up."""
    print("\n🔍 Checking configuration...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Copy example.env to .env and fill in your API keys")
        return False
    
    print("✅ .env file exists")
    
    # Try to load settings
    try:
        from src.config.settings import settings
        
        # Check Google AI API key
        if hasattr(settings, 'google_ai_api_key') and settings.google_ai_api_key:
            print("✅ Google AI API key configured")
        else:
            print("⚠️  Google AI API key not configured")
            print("   Add GOOGLE_AI_API_KEY to your .env file")
            
        # Check Google Sheets
        if settings.google_sheets_id:
            print("✅ Google Sheets ID configured")
        else:
            print("⚠️  Google Sheets ID not configured")
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_linkedin_discovery():
    """Test the LinkedIn discovery functionality."""
    print("\n🧪 Testing LinkedIn discovery...")
    
    try:
        from src.gemini_linkedin_discovery import find_linkedin_profile
        
        # Test with a sample search
        result = find_linkedin_profile(
            real_name="Test User",
            location="Test Location",
            conversation_summary="Test conversation"
        )
        
        if result:
            print(f"✅ LinkedIn discovery working - Result: {result[:100]}...")
        else:
            print("⚠️  LinkedIn discovery returned no result")
            
        return True
        
    except Exception as e:
        print(f"❌ LinkedIn discovery test failed: {e}")
        return False

def main():
    """Main setup verification."""
    print("🔧 LinkedIn Discovery Setup Verification")
    print("=" * 50)
    
    all_good = True
    
    # Check dependencies
    if not check_dependencies():
        all_good = False
    
    # Check configuration
    if not check_configuration():
        all_good = False
    
    # Test functionality if everything looks good
    if all_good:
        test_linkedin_discovery()
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 Setup verification complete! You're ready to use LinkedIn discovery.")
    else:
        print("⚠️  Some issues found. Please address them before using LinkedIn discovery.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
