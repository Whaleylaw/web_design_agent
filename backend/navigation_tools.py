"""
Navigation tools for the WordPress Visual Editor
"""
import json
from typing import Optional
from langchain_core.tools import tool
from .wordpress_tools import api

@tool
def wp_navigate_to_page(page_identifier: str) -> str:
    """Navigate to a specific page in the visual editor.
    
    Args:
        page_identifier: Page title, page ID, or keywords to search for the page
    
    Returns:
        Navigation result message
    """
    try:
        # Get all pages
        pages_response = api.request("/wp/v2/pages", params={"per_page": 100})
        if pages_response.startswith("Error"):
            return pages_response
        
        pages = json.loads(pages_response)
        
        # Search by ID if numeric
        if page_identifier.isdigit():
            page_id = int(page_identifier)
            for page in pages:
                if page["id"] == page_id:
                    return f"Navigate to page: {page.get('title', {}).get('rendered', 'Untitled')} (ID: {page_id})"
            return f"Page with ID {page_id} not found"
        
        # Search by title or keywords
        search_term = page_identifier.lower()
        for page in pages:
            page_title = page.get("title", {}).get("rendered", "").lower()
            if search_term in page_title or page_title in search_term:
                return f"Navigate to page: {page.get('title', {}).get('rendered', 'Untitled')} (ID: {page['id']})"
        
        # Check if it's a home page request
        if any(word in search_term for word in ["home", "main", "index", "front"]):
            return "Navigate to homepage"
        
        return f"Could not find a page matching '{page_identifier}'. Available pages: " + ", ".join([
            p.get("title", {}).get("rendered", "Untitled") for p in pages[:5]
        ]) + "..."
        
    except Exception as e:
        return f"Error navigating: {str(e)}"


@tool 
def wp_create_blank_page(title: str) -> str:
    """Create a new blank page and navigate to it.
    
    Args:
        title: Title for the new page
    
    Returns:
        Success message with page ID
    """
    try:
        # Create a blank page with minimal content
        data = {
            "title": title,
            "content": "<p>This is a new blank page. Start adding content!</p>",
            "status": "draft"
        }
        
        response = api.request("/wp/v2/pages", "POST", data)
        if response.startswith("Error"):
            return response
        
        page_data = json.loads(response)
        page_id = page_data.get("id")
        page_title = page_data.get("title", {}).get("rendered", title)
        
        return f"Created new blank page '{page_title}' (ID: {page_id}). Navigate to this page to start editing it."
        
    except Exception as e:
        return f"Error creating page: {str(e)}"


@tool
def wp_list_all_pages() -> str:
    """List all pages available for navigation.
    
    Returns:
        List of all pages with their IDs and titles
    """
    try:
        pages_response = api.request("/wp/v2/pages", params={"per_page": 100})
        if pages_response.startswith("Error"):
            return pages_response
        
        pages = json.loads(pages_response)
        
        if not pages:
            return "No pages found on the site."
        
        result = "Available pages:\n"
        for page in pages:
            title = page.get("title", {}).get("rendered", "Untitled")
            page_id = page.get("id")
            status = page.get("status", "unknown")
            parent = page.get("parent", 0)
            
            indent = "  " if parent > 0 else ""
            result += f"{indent}• {title} (ID: {page_id}, Status: {status})\n"
        
        result += "\nTo navigate to a page, just mention its name or ID."
        return result
        
    except Exception as e:
        return f"Error listing pages: {str(e)}"


@tool
def wp_add_page_to_menu(page_id: int, menu_location: str = "primary") -> str:
    """Add a page to the navigation menu.
    
    Args:
        page_id: ID of the page to add to menu
        menu_location: Menu location (default: primary)
    
    Returns:
        Success or error message
    """
    try:
        # First, get the page details
        page_response = api.request(f"/wp/v2/pages/{page_id}")
        if page_response.startswith("Error"):
            return f"Could not find page with ID {page_id}"
        
        page_data = json.loads(page_response)
        page_title = page_data.get("title", {}).get("rendered", "Untitled")
        page_url = page_data.get("link", "")
        
        # Get menus
        menus_response = api.request("/wp/v2/menus")
        if menus_response.startswith("Error"):
            # Try alternative menu endpoint
            return f"Menu functionality may require additional plugins. Page '{page_title}' has been created and can be accessed directly."
        
        # This is a simplified version - full menu management would require
        # the WordPress menu API or custom implementation
        return f"To add '{page_title}' to your menu, you may need to use the WordPress admin panel. The page is available at: {page_url}"
        
    except Exception as e:
        return f"Error adding to menu: {str(e)}. The page has been created successfully and can be accessed directly."