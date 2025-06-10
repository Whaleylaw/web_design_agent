#!/usr/bin/env python3
"""
Page Context Generator
Creates markdown descriptions and element mappings for each page
to help the agent understand page layout and find specific elements.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
DEPLOY_DIR = PROJECT_ROOT / "deploy" / "public"
CONTEXT_DIR = PROJECT_ROOT / "page_contexts"

def extract_page_elements(html_content: str) -> Dict[str, List[str]]:
    """Extract key elements from HTML and categorize them by location/type."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    elements = {
        "headings": [],
        "navigation": [],
        "header": [],
        "main_content": [],
        "footer": [],
        "buttons": [],
        "links": [],
        "images": [],
        "forms": []
    }
    
    # Extract headings (h1-h6)
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = heading.get_text(strip=True)
        if text:
            elements["headings"].append(f"{heading.name}: {text}")
    
    # Extract navigation elements
    nav_areas = soup.find_all(['nav', 'ul', 'ol']) + soup.find_all(attrs={'class': re.compile(r'nav|menu|header', re.I)})
    for nav in nav_areas:
        links = nav.find_all('a')
        for link in links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text:
                elements["navigation"].append(f"Link: {text} ({href})")
    
    # Extract header content
    header = soup.find('header') or soup.find(attrs={'class': re.compile(r'header', re.I)})
    if header:
        text = header.get_text(strip=True)
        if text:
            elements["header"].append(text[:200] + "..." if len(text) > 200 else text)
    
    # Extract main content
    main = soup.find('main') or soup.find(attrs={'class': re.compile(r'main|content', re.I)})
    if main:
        # Get first few paragraphs or content blocks
        for p in main.find_all(['p', 'div'])[:5]:
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                elements["main_content"].append(text[:150] + "..." if len(text) > 150 else text)
    
    # Extract buttons
    for button in soup.find_all(['button']) + soup.find_all('a', attrs={'class': re.compile(r'btn|button', re.I)}):
        text = button.get_text(strip=True)
        if text:
            elements["buttons"].append(text)
    
    # Extract images with alt text
    for img in soup.find_all('img'):
        alt = img.get('alt', '')
        src = img.get('src', '')
        if alt or src:
            elements["images"].append(f"Image: {alt} ({src})")
    
    # Extract form elements
    for form in soup.find_all('form'):
        inputs = form.find_all(['input', 'textarea', 'select'])
        for inp in inputs:
            input_type = inp.get('type', 'text')
            name = inp.get('name', '')
            placeholder = inp.get('placeholder', '')
            label_elem = form.find('label', attrs={'for': inp.get('id', '')})
            label = label_elem.get_text(strip=True) if label_elem else ''
            
            elements["forms"].append(f"{input_type}: {label or name or placeholder}")
    
    return elements

def create_layout_description(elements: Dict[str, List[str]]) -> str:
    """Create a human-readable layout description."""
    description = []
    
    if elements["header"]:
        description.append("## Header Area")
        for item in elements["header"]:
            description.append(f"- {item}")
        description.append("")
    
    if elements["headings"]:
        description.append("## Main Headings")
        for heading in elements["headings"]:
            description.append(f"- {heading}")
        description.append("")
    
    if elements["navigation"]:
        description.append("## Navigation")
        for nav_item in elements["navigation"]:
            description.append(f"- {nav_item}")
        description.append("")
    
    if elements["main_content"]:
        description.append("## Main Content")
        for content in elements["main_content"]:
            description.append(f"- {content}")
        description.append("")
    
    if elements["buttons"]:
        description.append("## Buttons & Actions")
        for button in elements["buttons"]:
            description.append(f"- Button: {button}")
        description.append("")
    
    if elements["images"]:
        description.append("## Images")
        for image in elements["images"]:
            description.append(f"- {image}")
        description.append("")
    
    if elements["forms"]:
        description.append("## Form Elements")
        for form_elem in elements["forms"]:
            description.append(f"- {form_elem}")
        description.append("")
    
    return "\n".join(description)

def create_element_mapping(html_content: str) -> Dict[str, str]:
    """Create mapping of common descriptions to HTML selectors."""
    soup = BeautifulSoup(html_content, 'html.parser')
    mapping = {}
    
    # Map common location descriptions to selectors
    header = soup.find('header') or soup.find(attrs={'class': re.compile(r'header', re.I)})
    if header:
        mapping["header"] = str(header)[:200] + "..."
        mapping["top of page"] = str(header)[:200] + "..."
        mapping["upper area"] = str(header)[:200] + "..."
    
    # Map heading text to actual HTML
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = heading.get_text(strip=True).lower()
        if text:
            mapping[text] = str(heading)
            # Also map partial matches
            words = text.split()
            if len(words) > 1:
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        if word not in mapping:
                            mapping[word] = str(heading)
    
    # Map button text
    for button in soup.find_all(['button']) + soup.find_all('a', attrs={'class': re.compile(r'btn|button', re.I)}):
        text = button.get_text(strip=True).lower()
        if text:
            mapping[text] = str(button)
    
    # Map navigation links
    for link in soup.find_all('a'):
        text = link.get_text(strip=True).lower()
        if text and len(text) > 2:
            mapping[text] = str(link)
    
    return mapping

def generate_page_context(page_name: str) -> str:
    """Generate complete context description for a page."""
    # Determine page file path
    if "/" in page_name:
        page_file = DEPLOY_DIR / f"{page_name}.html"
    else:
        page_file = DEPLOY_DIR / f"{page_name}.html"
    
    if not page_file.exists():
        return f"Error: Page '{page_name}' not found"
    
    # Read HTML content
    try:
        with open(page_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        return f"Error reading page: {e}"
    
    # Extract elements and create descriptions
    elements = extract_page_elements(html_content)
    layout_desc = create_layout_description(elements)
    element_mapping = create_element_mapping(html_content)
    
    # Create complete context document
    context = f"""# Page Context: {page_name}

## Visual Layout Description

{layout_desc}

## Element Mapping for Agent Reference

When a user refers to page elements, use this mapping to find the correct HTML:

"""
    
    for description, html_snippet in element_mapping.items():
        context += f"**\"{description}\"** → `{html_snippet}`\n\n"
    
    context += """
## Common User Descriptions

- "upper left corner" → Look in header or first heading elements
- "top of page" → Look in header section
- "navigation" → Look in nav elements or header links
- "main heading" → Look for h1 elements
- "title" → Look for h1, title tag, or prominent heading
- "button" → Look for button elements or links with button classes

## Search Strategy for Agent

1. When user describes a location (e.g., "upper left"), check the header section first
2. When user mentions text content, search headings first, then links, then other text
3. Use the element mapping above to quickly locate commonly referenced elements
4. If searching for specific text, use case-insensitive search across all text content

"""
    
    return context

def generate_all_page_contexts():
    """Generate context files for all pages."""
    # Create context directory
    CONTEXT_DIR.mkdir(exist_ok=True)
    
    if not DEPLOY_DIR.exists():
        print("❌ Deploy directory not found")
        return
    
    pages = []
    for page_file in DEPLOY_DIR.iterdir():
        if page_file.is_file() and page_file.suffix == ".html":
            pages.append(page_file.stem)
    
    # Also check pages subdirectory
    pages_subdir = DEPLOY_DIR / "pages"
    if pages_subdir.exists():
        for page_file in pages_subdir.iterdir():
            if page_file.is_file() and page_file.suffix == ".html":
                pages.append(f"pages/{page_file.stem}")
    
    print(f"📝 Generating context for {len(pages)} pages...")
    
    for page_name in pages:
        context = generate_page_context(page_name)
        
        # Write context file
        context_file = CONTEXT_DIR / f"{page_name.replace('/', '_')}_context.md"
        try:
            with open(context_file, 'w', encoding='utf-8') as f:
                f.write(context)
            print(f"✅ Generated context for {page_name}")
        except Exception as e:
            print(f"❌ Error generating context for {page_name}: {e}")
    
    print(f"📁 Context files saved to: {CONTEXT_DIR}")

if __name__ == "__main__":
    generate_all_page_contexts() 