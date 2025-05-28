"""
Tool to disable coming soon mode on WordPress site
"""
from langchain_core.tools import tool
from .wordpress_tools import api
import json

@tool
def wp_disable_coming_soon_mode() -> str:
    """Disable 'Coming Soon' or maintenance mode on the WordPress site.
    
    This will make the site publicly visible in the preview.
    
    Returns:
        Success or error message
    """
    try:
        # First, try to update site settings to disable coming soon
        # This varies by plugin, but common approaches:
        
        # Try updating general settings
        settings_data = {
            "blog_public": "1",  # Make site visible to search engines
        }
        
        settings_response = api.request("/wp/v2/settings", "POST", settings_data)
        
        # Try to find and deactivate coming soon plugins
        # Note: This requires plugin management permissions
        plugins_response = api.request("/wp/v2/plugins")
        
        if not plugins_response.startswith("Error"):
            plugins = json.loads(plugins_response)
            
            # Look for common coming soon plugins
            coming_soon_keywords = ["coming", "soon", "maintenance", "under-construction"]
            
            for plugin in plugins:
                plugin_name = plugin.get("name", "").lower()
                if any(keyword in plugin_name for keyword in coming_soon_keywords):
                    # Try to deactivate it
                    plugin_slug = plugin.get("plugin", "")
                    deactivate_response = api.request(
                        f"/wp/v2/plugins/{plugin_slug}",
                        "POST",
                        {"status": "inactive"}
                    )
        
        return """Attempted to disable Coming Soon mode. 

If the site is still showing 'Coming Soon':
1. The theme or plugin controlling this may need manual configuration
2. You can still edit pages - they will be visible once Coming Soon is disabled
3. Try creating or editing pages - the content will be ready when the site goes live

To preview pages while in Coming Soon mode, I can show you the page content directly."""
        
    except Exception as e:
        return f"""Could not automatically disable Coming Soon mode: {str(e)}

The site is currently in 'Coming Soon' mode. You can still:
1. Create and edit pages
2. Add content and styling
3. Preview changes (they'll be live when Coming Soon is disabled)

Would you like me to show you the page content directly instead?"""