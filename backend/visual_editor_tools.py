"""
Enhanced WordPress tools for visual editing capabilities
"""
import json
import re
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from .wordpress_tools import api

@tool
def wp_add_custom_css_to_page(page_id: int, css_rules: str) -> str:
    """Add custom CSS to a specific page by injecting a style block.
    
    Args:
        page_id: The ID of the page to update
        css_rules: CSS rules to add (e.g., "body { background-color: blue; }")
    
    Returns:
        Success or error message
    """
    try:
        # Get current page content
        response = api.request(f"/wp/v2/pages/{page_id}")
        if response.startswith("Error"):
            return response
        
        page_data = json.loads(response)
        current_content = page_data.get("content", {}).get("raw", "")
        
        # Create a unique style block
        style_block = f"\n<!-- Custom CSS Added by AI Assistant -->\n<style>\n{css_rules}\n</style>\n<!-- End Custom CSS -->\n"
        
        # Check if we already have a custom CSS block and replace it
        pattern = r'<!-- Custom CSS Added by AI Assistant -->.*?<!-- End Custom CSS -->'
        if re.search(pattern, current_content, re.DOTALL):
            # Replace existing block
            new_content = re.sub(pattern, style_block.strip(), current_content, flags=re.DOTALL)
        else:
            # Add new block at the beginning
            new_content = style_block + current_content
        
        # Update the page
        update_response = api.request(
            f"/wp/v2/pages/{page_id}", 
            "PATCH", 
            {"content": new_content}
        )
        
        if update_response.startswith("Error"):
            return update_response
        
        return f"Successfully added CSS to page {page_id}. The changes should be visible after refreshing."
        
    except Exception as e:
        return f"Error adding CSS: {str(e)}"


@tool
def wp_add_content_block_to_page(page_id: int, block_html: str, position: str = "end") -> str:
    """Add a content block (HTML) to a page.
    
    Args:
        page_id: The ID of the page to update
        block_html: HTML content to add
        position: Where to add the content - "beginning", "end", or "replace"
    
    Returns:
        Success or error message
    """
    try:
        # Get current page content
        response = api.request(f"/wp/v2/pages/{page_id}")
        if response.startswith("Error"):
            return response
        
        page_data = json.loads(response)
        current_content = page_data.get("content", {}).get("raw", "")
        
        # Add content based on position
        if position == "beginning":
            new_content = block_html + "\n\n" + current_content
        elif position == "end":
            new_content = current_content + "\n\n" + block_html
        elif position == "replace":
            new_content = block_html
        else:
            return f"Invalid position: {position}. Use 'beginning', 'end', or 'replace'"
        
        # Update the page
        update_response = api.request(
            f"/wp/v2/pages/{page_id}", 
            "PATCH", 
            {"content": new_content}
        )
        
        if update_response.startswith("Error"):
            return update_response
        
        return f"Successfully added content block to page {page_id}. The changes should be visible after refreshing."
        
    except Exception as e:
        return f"Error adding content block: {str(e)}"


@tool
def wp_get_page_structure(page_id: int) -> str:
    """Analyze the structure of a page to help with targeted edits.
    
    Args:
        page_id: The ID of the page to analyze
    
    Returns:
        A summary of the page structure including main sections, headings, etc.
    """
    try:
        # Get page content
        response = api.request(f"/wp/v2/pages/{page_id}")
        if response.startswith("Error"):
            return response
        
        page_data = json.loads(response)
        content = page_data.get("content", {}).get("rendered", "")
        title = page_data.get("title", {}).get("rendered", "")
        
        # Extract structure information
        headings = re.findall(r'<h([1-6])[^>]*>(.*?)</h\1>', content)
        paragraphs = len(re.findall(r'<p[^>]*>', content))
        images = len(re.findall(r'<img[^>]*>', content))
        links = len(re.findall(r'<a[^>]*>', content))
        
        # Check for common WordPress blocks
        has_gallery = 'wp-block-gallery' in content
        has_columns = 'wp-block-columns' in content
        has_button = 'wp-block-button' in content
        
        structure = f"""Page Structure Analysis for "{title}" (ID: {page_id}):

Content Summary:
- Headings: {len(headings)} total
"""
        if headings:
            structure += "  Structure:\n"
            for level, text in headings:
                indent = "  " * (int(level) - 1)
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                structure += f"    {indent}H{level}: {clean_text[:50]}{'...' if len(clean_text) > 50 else ''}\n"
        
        structure += f"""
- Paragraphs: {paragraphs}
- Images: {images}
- Links: {links}

WordPress Blocks Detected:
- Gallery: {'Yes' if has_gallery else 'No'}
- Columns: {'Yes' if has_columns else 'No'}
- Buttons: {'Yes' if has_button else 'No'}

This information can help you make more targeted edits to specific sections."""
        
        return structure
        
    except Exception as e:
        return f"Error analyzing page structure: {str(e)}"


@tool
def wp_update_page_section(page_id: int, old_text: str, new_text: str) -> str:
    """Update a specific section of text on a page.
    
    Args:
        page_id: The ID of the page to update
        old_text: The text to find and replace (partial match supported)
        new_text: The new text to insert
    
    Returns:
        Success or error message
    """
    try:
        # Get current page content
        response = api.request(f"/wp/v2/pages/{page_id}")
        if response.startswith("Error"):
            return response
        
        page_data = json.loads(response)
        current_content = page_data.get("content", {}).get("raw", "")
        
        # Check if the old text exists
        if old_text not in current_content:
            # Try to find it in the rendered content
            rendered_content = page_data.get("content", {}).get("rendered", "")
            if old_text in rendered_content:
                return "The text was found in the rendered content but not in the raw content. This might be generated by a theme or plugin. Try updating the entire page content instead."
            else:
                return f"Could not find the text '{old_text[:50]}...' on the page. Please check the exact wording."
        
        # Replace the text
        new_content = current_content.replace(old_text, new_text)
        
        # Update the page
        update_response = api.request(
            f"/wp/v2/pages/{page_id}", 
            "PATCH", 
            {"content": new_content}
        )
        
        if update_response.startswith("Error"):
            return update_response
        
        return f"Successfully updated the text on page {page_id}. The changes should be visible after refreshing."
        
    except Exception as e:
        return f"Error updating page section: {str(e)}"