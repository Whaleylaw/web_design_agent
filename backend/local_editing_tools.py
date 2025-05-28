"""
Local editing tools for WordPress clone
"""
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
from bs4 import BeautifulSoup
import json

CLONE_DIR = Path("wordpress_clone")

@tool
def read_local_page_html(page_id: int) -> str:
    """Read the actual HTML content of a locally cloned page.
    
    This allows the agent to see the full HTML structure and styling.
    
    Args:
        page_id: The WordPress page ID
        
    Returns:
        The full HTML content or error message
    """
    page_dir = CLONE_DIR / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    
    if not html_file.exists():
        return f"Error: Page {page_id} not found in local clone. Run clone first."
    
    try:
        content = html_file.read_text()
        return f"HTML content for page {page_id}:\n\n{content}"
    except Exception as e:
        return f"Error reading HTML: {str(e)}"


@tool
def edit_local_page_content(page_id: int, new_content: str) -> str:
    """Edit the content section of a local page HTML file.
    
    Args:
        page_id: The WordPress page ID
        new_content: The new HTML content for the page body
        
    Returns:
        Success or error message
    """
    page_dir = CLONE_DIR / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    
    if not html_file.exists():
        return f"Error: Page {page_id} not found in local clone."
    
    try:
        # Read current HTML
        html = html_file.read_text()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find content div
        content_div = soup.find('div', class_='page-content')
        if not content_div:
            return "Error: Could not find page-content div in HTML"
        
        # Replace content
        content_div.clear()
        content_div.append(BeautifulSoup(new_content, 'html.parser'))
        
        # Save updated HTML
        html_file.write_text(str(soup.prettify()))
        
        return f"Successfully updated local content for page {page_id}. View changes in the canvas."
        
    except Exception as e:
        return f"Error editing HTML: {str(e)}"


@tool
def add_local_page_css(page_id: int, css_rules: str) -> str:
    """Add or update CSS for a local page.
    
    Args:
        page_id: The WordPress page ID
        css_rules: CSS rules to add (e.g., "body { background: blue; }")
        
    Returns:
        Success or error message
    """
    page_dir = CLONE_DIR / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    css_file = page_dir / "custom.css"
    
    if not html_file.exists():
        return f"Error: Page {page_id} not found in local clone."
    
    try:
        # Update or create CSS file
        existing_css = ""
        if css_file.exists():
            existing_css = css_file.read_text()
        
        # Append new CSS
        updated_css = existing_css + "\n\n" + css_rules
        css_file.write_text(updated_css.strip())
        
        # Also update the HTML file's inline CSS
        html = html_file.read_text()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find or create style tag in head
        head = soup.find('head')
        style_tag = soup.find('style')
        
        if not style_tag:
            style_tag = soup.new_tag('style')
            head.append(style_tag)
        
        # Update style content
        current_style = style_tag.string or ""
        style_tag.string = current_style + "\n" + css_rules
        
        # Save updated HTML
        html_file.write_text(str(soup.prettify()))
        
        return f"Successfully added CSS to page {page_id}. The changes are visible in the canvas."
        
    except Exception as e:
        return f"Error adding CSS: {str(e)}"


@tool
def analyze_local_page_structure(page_id: int) -> str:
    """Analyze the HTML structure of a local page to help with targeted edits.
    
    Args:
        page_id: The WordPress page ID
        
    Returns:
        Analysis of the page structure
    """
    page_dir = CLONE_DIR / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    
    if not html_file.exists():
        return f"Error: Page {page_id} not found in local clone."
    
    try:
        html = html_file.read_text()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Analyze structure
        analysis = f"Page Structure Analysis for Page {page_id}:\n\n"
        
        # Title
        title = soup.find('h1', class_='page-title')
        if title:
            analysis += f"Title: {title.get_text().strip()}\n\n"
        
        # Content structure
        content_div = soup.find('div', class_='page-content')
        if content_div:
            # Count elements
            headings = content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            paragraphs = content_div.find_all('p')
            images = content_div.find_all('img')
            links = content_div.find_all('a')
            divs = content_div.find_all('div')
            
            analysis += "Content Elements:\n"
            analysis += f"- Headings: {len(headings)}\n"
            if headings:
                for h in headings[:5]:  # First 5 headings
                    analysis += f"  - {h.name}: {h.get_text().strip()[:50]}...\n"
            
            analysis += f"- Paragraphs: {len(paragraphs)}\n"
            analysis += f"- Images: {len(images)}\n"
            analysis += f"- Links: {len(links)}\n"
            analysis += f"- Divs: {len(divs)}\n"
            
            # Check for WordPress blocks
            blocks = content_div.find_all(class_=lambda x: x and 'wp-block' in x)
            if blocks:
                analysis += f"\nWordPress Blocks Found: {len(blocks)}\n"
                block_types = set()
                for block in blocks:
                    classes = block.get('class', [])
                    for cls in classes:
                        if 'wp-block-' in cls:
                            block_types.add(cls)
                
                for block_type in sorted(block_types):
                    analysis += f"  - {block_type}\n"
            
            # CSS classes used
            all_classes = set()
            for elem in content_div.find_all(class_=True):
                all_classes.update(elem.get('class', []))
            
            if all_classes:
                analysis += f"\nCSS Classes Used ({len(all_classes)}):\n"
                for cls in sorted(all_classes)[:10]:  # First 10 classes
                    analysis += f"  - .{cls}\n"
        
        # Custom CSS
        css_file = page_dir / "custom.css"
        if css_file.exists():
            css_content = css_file.read_text()
            if css_content.strip():
                analysis += f"\nCustom CSS File: Yes ({len(css_content)} chars)\n"
        
        return analysis
        
    except Exception as e:
        return f"Error analyzing page: {str(e)}"


@tool
def list_local_pages() -> str:
    """List all locally cloned pages.
    
    Returns:
        List of cloned pages with their IDs and titles
    """
    manifest_file = CLONE_DIR / "manifest.json"
    
    if not manifest_file.exists():
        return "No local clone found. Run clone first to download pages."
    
    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
        
        if not manifest.get("pages"):
            return "No pages found in local clone."
        
        result = "Locally Cloned Pages:\n\n"
        for page_id, info in manifest["pages"].items():
            result += f"• Page {page_id}: {info['title']}\n"
            result += f"  Path: {info['path']}\n"
        
        result += f"\nTotal: {len(manifest['pages'])} pages"
        result += f"\nCloned from: {manifest['site_url']}"
        result += f"\nCloned at: {manifest['cloned_at']}"
        
        return result
        
    except Exception as e:
        return f"Error reading manifest: {str(e)}"


@tool
def clone_wordpress_site() -> str:
    """Clone the WordPress site locally for editing.
    
    This downloads all pages with their content and styling.
    
    Returns:
        Success message with clone location
    """
    try:
        from wordpress_clone import WordPressClone
        
        cloner = WordPressClone()
        clone_dir = cloner.clone_site()
        
        return f"""Successfully cloned WordPress site!

Location: {clone_dir.absolute()}
Pages cloned: {len(cloner.manifest['pages'])}

You can now:
1. Read actual HTML with read_local_page_html
2. Edit content with edit_local_page_content
3. Add CSS with add_local_page_css
4. Analyze structure with analyze_local_page_structure

When ready, push changes back to WordPress."""
        
    except Exception as e:
        return f"Error cloning site: {str(e)}"


@tool
def push_local_changes(dry_run: bool = True) -> str:
    """Push local changes back to WordPress.
    
    Args:
        dry_run: If True, show what would be pushed without actually pushing
        
    Returns:
        Status of push operation
    """
    try:
        from wordpress_push import WordPressPush
        
        pusher = WordPressPush()
        
        # Get changes
        changes = pusher.detect_changes()
        
        if not changes:
            return "No changes detected. Local clone is in sync with WordPress."
        
        result = f"Detected {len(changes)} changes:\n\n"
        for change in changes:
            result += f"• {change['title']} ({change['type']})\n"
        
        if dry_run:
            result += "\n[DRY RUN - No changes will be pushed]"
            result += "\nTo actually push, use push_local_changes(dry_run=False)"
        else:
            # Actually push
            pusher.push_all_changes(dry_run=False)
            result += "\n✅ Changes pushed to WordPress!"
        
        return result
        
    except Exception as e:
        return f"Error pushing changes: {str(e)}"