#!/usr/bin/env python3
"""Test WordPress connection and display capabilities"""

import json
import requests
from wordpress_tools import WordPressAPI

def test_connection():
    """Test basic WordPress connection"""
    print("Testing WordPress Connection...")
    print("-" * 50)
    
    try:
        # Initialize API
        api = WordPressAPI()
        print(f"✓ Site URL: {api.base_url}")
        print(f"✓ Username: {api.username}")
        
        # Test API connection
        response = api.request("/wp/v2/posts", params={"per_page": 1})
        if not response.startswith("Error"):
            print("✓ API Connection: Success")
            
            # Get site info
            site_response = api.request("")
            if not site_response.startswith("Error"):
                site_data = json.loads(site_response)
                print(f"✓ Site Name: {site_data.get('name', 'Unknown')}")
                print(f"✓ Site Description: {site_data.get('description', 'Unknown')}")
        else:
            print(f"✗ API Connection Failed: {response}")
            
        # Test direct URL access
        print("\nTesting Direct URL Access...")
        try:
            direct_response = requests.get(api.base_url, timeout=5)
            print(f"✓ Homepage Status: {direct_response.status_code}")
            print(f"✓ Homepage Accessible: {'Yes' if direct_response.status_code == 200 else 'No'}")
            
            # Check if it's a "coming soon" page
            if "coming soon" in direct_response.text.lower() or "maintenance" in direct_response.text.lower():
                print("⚠ Note: Site appears to be in 'Coming Soon' or maintenance mode")
        except Exception as e:
            print(f"✗ Direct URL Access Failed: {e}")
            
        # List available pages
        print("\nAvailable Pages:")
        pages_response = api.request("/wp/v2/pages", params={"per_page": 10})
        if not pages_response.startswith("Error"):
            pages = json.loads(pages_response)
            for page in pages[:5]:
                title = page.get("title", {}).get("rendered", "Untitled")
                page_id = page.get("id")
                link = page.get("link", "")
                print(f"  • {title} (ID: {page_id})")
                print(f"    URL: {link}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_connection()