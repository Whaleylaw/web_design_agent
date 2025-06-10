#!/usr/bin/env python3
"""
Simple Markdown Generator
Converts HTML pages to readable markdown so the agent can "see" pages like humans do.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).parent.parent
DEPLOY_DIR = PROJECT_ROOT / "deploy" / "public"
WORKING_DIR = PROJECT_ROOT / "working"
MARKDOWN_DIR = PROJECT_ROOT / "markdown"

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to simple, readable markdown."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    # Extract key elements
    title = soup.find('title')
    title_text = title.get_text().strip() if title else "Untitled"
    
    # Get all headings
    headings = []
    for level in range(1, 7):
        for h in soup.find_all(f'h{level}'):
            headings.append(f"{'#' * level} {h.get_text().strip()}")
    
    # Get all paragraphs
    paragraphs = []
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        if text:
            paragraphs.append(text)
    
    # Get all links
    links = []
    for a in soup.find_all('a', href=True):
        text = a.get_text().strip()
        href = a['href']
        if text and href:
            links.append(f"[{text}]({href})")
    
    # Get all list items
    lists = []
    for ul in soup.find_all(['ul', 'ol']):
        list_items = []
        for li in ul.find_all('li'):
            text = li.get_text().strip()
            if text:
                list_items.append(f"- {text}")
        if list_items:
            lists.extend(list_items)
    
    # Build markdown
    markdown = f"# {title_text}\n\n"
    
    if headings:
        markdown += "## Headings\n"
        markdown += "\n".join(headings) + "\n\n"
    
    if paragraphs:
        markdown += "## Content\n"
        markdown += "\n\n".join(paragraphs) + "\n\n"
    
    if links:
        markdown += "## Links\n"
        markdown += "\n".join(links) + "\n\n"
    
    if lists:
        markdown += "## Lists\n"
        markdown += "\n".join(lists) + "\n\n"
    
    return markdown

def generate_markdown_for_page(page_name: str, source_type: str = "deployed") -> str:
    """Generate markdown for a specific page."""
    try:
        # Determine source file
        if source_type == "deployed":
            source_file = DEPLOY_DIR / f"{page_name}.html"
        else:  # working
            # Check direct working file first, then pages subdirectory
            source_file = WORKING_DIR / f"{page_name}.html"
            if not source_file.exists():
                source_file = WORKING_DIR / "pages" / f"{page_name}.html"
        
        if not source_file.exists():
            return f"❌ Source file not found: {source_file}"
        
        # Read HTML
        with open(source_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Convert to markdown
        markdown_content = html_to_markdown(html_content)
        
        # Create markdown directory structure
        markdown_subdir = MARKDOWN_DIR / source_type
        markdown_subdir.mkdir(parents=True, exist_ok=True)
        
        # Write markdown file
        markdown_file = markdown_subdir / f"{page_name}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return f"✅ Generated markdown: {markdown_file}"
        
    except Exception as e:
        return f"❌ Error generating markdown: {str(e)}"

def generate_all_markdown() -> str:
    """Generate markdown for all pages (both deployed and working)."""
    results = []
    
    # Generate for deployed pages
    if DEPLOY_DIR.exists():
        for html_file in DEPLOY_DIR.glob("*.html"):
            page_name = html_file.stem
            result = generate_markdown_for_page(page_name, "deployed")
            results.append(result)
    
    # Generate for working pages - check both working/ and working/pages/
    working_pages = set()
    if WORKING_DIR.exists():
        # Direct working files
        for html_file in WORKING_DIR.glob("*.html"):
            page_name = html_file.stem
            working_pages.add(page_name)
        
        # Working pages subdirectory
        pages_dir = WORKING_DIR / "pages"
        if pages_dir.exists():
            for html_file in pages_dir.glob("*.html"):
                page_name = html_file.stem
                working_pages.add(page_name)
    
    # Generate markdown for all working pages found
    for page_name in working_pages:
        result = generate_markdown_for_page(page_name, "working")
        results.append(result)
    
    return "\n".join(results)

if __name__ == "__main__":
    print("Generating markdown for all pages...")
    result = generate_all_markdown()
    print(result) 