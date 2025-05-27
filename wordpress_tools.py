"""
Comprehensive WordPress API tools for the agent
"""
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any
from langchain_core.tools import tool

class WordPressAPI:
    """WordPress API client with authentication"""
    
    def __init__(self, config_file='wp-sites.json'):
        # Load WordPress credentials
        with open(config_file, 'r') as f:
            wp_config = json.load(f)
        
        site_config = wp_config.get('lawyerinc', {})
        self.base_url = site_config.get('URL', '').rstrip('/')
        self.username = site_config.get('USER', '')
        self.password = site_config.get('PASS', '')
        self.auth = HTTPBasicAuth(self.username, self.password)
    
    def request(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> str:
        """Make authenticated request to WordPress API"""
        try:
            # Construct full URL
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            if not endpoint.startswith('/wp-json'):
                endpoint = '/wp-json' + endpoint
            
            url = self.base_url + endpoint
            
            response = requests.request(
                method=method.upper(),
                url=url,
                auth=self.auth,
                json=data,
                params=params,
                headers={'Content-Type': 'application/json'}
            )
            
            # Handle response
            if response.status_code >= 400:
                return f"Error {response.status_code}: {response.text[:500]}"
            
            return json.dumps(response.json(), indent=2)
            
        except Exception as e:
            return f"Error: {str(e)}"


# Initialize API client
api = WordPressAPI()


# ============== CONTENT MANAGEMENT TOOLS ==============

@tool
def wp_create_post(title: str, content: str, status: str = "draft", categories: Optional[str] = None, tags: Optional[str] = None) -> str:
    """Create a new WordPress post.
    
    Args:
        title: Post title
        content: Post content (HTML supported)
        status: Post status (draft, publish, private)
        categories: Comma-separated category IDs (optional)
        tags: Comma-separated tag IDs (optional)
    """
    data = {
        "title": title,
        "content": content,
        "status": status
    }
    
    if categories:
        data["categories"] = [int(x.strip()) for x in categories.split(",") if x.strip()]
    if tags:
        data["tags"] = [int(x.strip()) for x in tags.split(",") if x.strip()]
    
    return api.request("/wp/v2/posts", "POST", data)


@tool
def wp_update_post(post_id: int, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None) -> str:
    """Update an existing WordPress post.
    
    Args:
        post_id: ID of the post to update
        title: New title (optional)
        content: New content (optional)
        status: New status (optional)
    """
    data = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if status is not None:
        data["status"] = status
    
    return api.request(f"/wp/v2/posts/{post_id}", "PATCH", data)


@tool
def wp_delete_post(post_id: int, force: bool = False) -> str:
    """Delete a WordPress post.
    
    Args:
        post_id: ID of the post to delete
        force: If True, permanently delete. If False, move to trash.
    """
    params = {"force": force}
    return api.request(f"/wp/v2/posts/{post_id}", "DELETE", params=params)


@tool
def wp_get_posts(status: str = "publish", per_page: int = 10, page: int = 1, search: Optional[str] = None) -> str:
    """Get WordPress posts with filtering options.
    
    Args:
        status: Post status filter (publish, draft, private, any)
        per_page: Number of posts per page
        page: Page number
        search: Search term
    """
    params = {"status": status, "per_page": per_page, "page": page}
    if search:
        params["search"] = search
    return api.request("/wp/v2/posts", params=params)


@tool
def wp_get_post(post_id: int) -> str:
    """Get a specific WordPress post by ID."""
    return api.request(f"/wp/v2/posts/{post_id}")


# ============== PAGE MANAGEMENT TOOLS ==============

@tool
def wp_create_page(title: str, content: str, status: str = "draft", parent: Optional[int] = None) -> str:
    """Create a new WordPress page.
    
    Args:
        title: Page title
        content: Page content (HTML supported)
        status: Page status (draft, publish, private)
        parent: Parent page ID for hierarchical pages (optional)
    """
    data = {
        "title": title,
        "content": content,
        "status": status
    }
    
    if parent is not None:
        data["parent"] = parent
    
    return api.request("/wp/v2/pages", "POST", data)


@tool
def wp_update_page(page_id: int, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None) -> str:
    """Update an existing WordPress page."""
    data = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if status is not None:
        data["status"] = status
    
    return api.request(f"/wp/v2/pages/{page_id}", "PATCH", data)


@tool
def wp_get_pages(status: str = "publish", per_page: int = 10, parent: Optional[int] = None) -> str:
    """Get WordPress pages."""
    params = {"status": status, "per_page": per_page}
    if parent is not None:
        params["parent"] = parent
    return api.request("/wp/v2/pages", params=params)


# ============== MEDIA MANAGEMENT TOOLS ==============

@tool
def wp_get_media(per_page: int = 10, media_type: Optional[str] = None, mime_type: Optional[str] = None) -> str:
    """Get media items from WordPress media library.
    
    Args:
        per_page: Number of items to retrieve
        media_type: Filter by media type (image, video, audio, application)
        mime_type: Filter by MIME type (e.g., image/jpeg, video/mp4)
    """
    params = {"per_page": per_page}
    if media_type:
        params["media_type"] = media_type
    if mime_type:
        params["mime_type"] = mime_type
    return api.request("/wp/v2/media", params=params)


@tool
def wp_update_media_metadata(media_id: int, title: Optional[str] = None, caption: Optional[str] = None, alt_text: Optional[str] = None) -> str:
    """Update media item metadata.
    
    Args:
        media_id: ID of the media item
        title: New title
        caption: New caption
        alt_text: New alt text for images
    """
    data = {}
    if title is not None:
        data["title"] = {"raw": title}
    if caption is not None:
        data["caption"] = {"raw": caption}
    if alt_text is not None:
        data["alt_text"] = alt_text
    
    return api.request(f"/wp/v2/media/{media_id}", "PATCH", data)


# ============== TAXONOMY TOOLS ==============

@tool
def wp_get_categories(per_page: int = 100, search: Optional[str] = None) -> str:
    """Get all categories."""
    params = {"per_page": per_page}
    if search:
        params["search"] = search
    return api.request("/wp/v2/categories", params=params)


@tool
def wp_create_category(name: str, description: str = "", parent: Optional[int] = None) -> str:
    """Create a new category."""
    data = {
        "name": name,
        "description": description
    }
    if parent is not None:
        data["parent"] = parent
    return api.request("/wp/v2/categories", "POST", data)


@tool
def wp_get_tags(per_page: int = 100, search: Optional[str] = None) -> str:
    """Get all tags."""
    params = {"per_page": per_page}
    if search:
        params["search"] = search
    return api.request("/wp/v2/tags", params=params)


@tool
def wp_create_tag(name: str, description: str = "") -> str:
    """Create a new tag."""
    data = {
        "name": name,
        "description": description
    }
    return api.request("/wp/v2/tags", "POST", data)


# ============== COMMENT TOOLS ==============

@tool
def wp_get_comments(status: str = "approved", per_page: int = 10, post: Optional[int] = None) -> str:
    """Get comments.
    
    Args:
        status: Comment status (approved, pending, spam, trash)
        per_page: Number of comments to retrieve
        post: Filter by post ID
    """
    params = {"status": status, "per_page": per_page}
    if post is not None:
        params["post"] = post
    return api.request("/wp/v2/comments", params=params)


@tool
def wp_moderate_comment(comment_id: int, status: str) -> str:
    """Moderate a comment by changing its status.
    
    Args:
        comment_id: ID of the comment
        status: New status (approved, pending, spam, trash)
    """
    data = {"status": status}
    return api.request(f"/wp/v2/comments/{comment_id}", "PATCH", data)


# ============== USER MANAGEMENT TOOLS ==============

@tool
def wp_get_users(per_page: int = 10, roles: Optional[str] = None) -> str:
    """Get WordPress users.
    
    Args:
        per_page: Number of users to retrieve
        roles: Comma-separated list of roles to filter by
    """
    params = {"per_page": per_page}
    if roles:
        params["roles"] = roles
    return api.request("/wp/v2/users", params=params)


@tool
def wp_get_current_user() -> str:
    """Get information about the currently authenticated user."""
    return api.request("/wp/v2/users/me")


# ============== SITE MANAGEMENT TOOLS ==============

@tool
def wp_get_site_info() -> str:
    """Get comprehensive site information including settings and available endpoints."""
    settings = api.request("/wp/v2/settings")
    discovery = api.request("/")
    return f"Site Settings:\n{settings}\n\nAvailable Endpoints:\n{discovery}"


@tool
def wp_update_site_settings(title: Optional[str] = None, description: Optional[str] = None, 
                          timezone: Optional[str] = None, date_format: Optional[str] = None, 
                          time_format: Optional[str] = None) -> str:
    """Update WordPress site settings.
    
    Args:
        title: Site title
        description: Site tagline/description
        timezone: Timezone string (e.g., 'America/New_York')
        date_format: PHP date format
        time_format: PHP time format
    """
    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if timezone is not None:
        data["timezone_string"] = timezone
    if date_format is not None:
        data["date_format"] = date_format
    if time_format is not None:
        data["time_format"] = time_format
    
    return api.request("/wp/v2/settings", "PATCH", data)


@tool
def wp_get_post_types() -> str:
    """Get all available post types on the site."""
    return api.request("/wp/v2/types")


@tool
def wp_get_taxonomies() -> str:
    """Get all available taxonomies on the site."""
    return api.request("/wp/v2/taxonomies")


# ============== MENU TOOLS ==============

@tool
def wp_get_menus() -> str:
    """Get all navigation menus."""
    return api.request("/wp/v2/menus")


@tool
def wp_get_menu_items(menu_id: Optional[int] = None) -> str:
    """Get menu items, optionally filtered by menu ID."""
    params = {}
    if menu_id is not None:
        params["menus"] = menu_id
    return api.request("/wp/v2/menu-items", params=params)


# ============== THEME TOOLS ==============

@tool
def wp_get_themes() -> str:
    """Get all available themes."""
    return api.request("/wp/v2/themes")


# ============== PLUGIN TOOLS ==============

@tool
def wp_get_plugins() -> str:
    """Get all installed plugins (requires admin permissions)."""
    return api.request("/wp/v2/plugins")


# ============== REUSABLE BLOCKS ==============

@tool
def wp_get_blocks() -> str:
    """Get all reusable blocks."""
    return api.request("/wp/v2/blocks")


@tool
def wp_create_block(title: str, content: str) -> str:
    """Create a reusable block."""
    data = {
        "title": title,
        "content": content,
        "status": "publish"
    }
    return api.request("/wp/v2/blocks", "POST", data)


# ============== SEARCH TOOL ==============

@tool
def wp_search(query: str, per_page: int = 10) -> str:
    """Search across all content types.
    
    Args:
        query: Search query
        per_page: Number of results to return
    """
    params = {"search": query, "per_page": per_page}
    return api.request("/wp/v2/search", params=params)


# ============== GENERIC API TOOL ==============

@tool
def wp_api_request(endpoint: str, method: str = "GET", data: Optional[str] = None, params: Optional[str] = None) -> str:
    """Make a custom WordPress API request for endpoints not covered by specific tools.
    
    Args:
        endpoint: API endpoint path (e.g., '/wp/v2/custom-endpoint')
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        data: JSON string of data to send in request body
        params: JSON string of URL parameters
    """
    request_data = json.loads(data) if data else None
    request_params = json.loads(params) if params else None
    return api.request(endpoint, method, request_data, request_params)


def get_all_wordpress_tools():
    """Get all WordPress tools for the agent."""
    return [
        # Content Management
        wp_create_post,
        wp_update_post,
        wp_delete_post,
        wp_get_posts,
        wp_get_post,
        
        # Page Management
        wp_create_page,
        wp_update_page,
        wp_get_pages,
        
        # Media
        wp_get_media,
        wp_update_media_metadata,
        
        # Taxonomies
        wp_get_categories,
        wp_create_category,
        wp_get_tags,
        wp_create_tag,
        
        # Comments
        wp_get_comments,
        wp_moderate_comment,
        
        # Users
        wp_get_users,
        wp_get_current_user,
        
        # Site Management
        wp_get_site_info,
        wp_update_site_settings,
        wp_get_post_types,
        wp_get_taxonomies,
        
        # Menus
        wp_get_menus,
        wp_get_menu_items,
        
        # Themes & Plugins
        wp_get_themes,
        wp_get_plugins,
        
        # Blocks
        wp_get_blocks,
        wp_create_block,
        
        # Search
        wp_search,
        
        # Generic API
        wp_api_request
    ]