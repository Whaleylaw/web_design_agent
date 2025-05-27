#!/usr/bin/env python3
"""
WordPress Clone System - Pull WordPress site locally for editing
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from wordpress_tools import WordPressAPI
from bs4 import BeautifulSoup
import re

class WordPressClone:
    """Clone WordPress content locally for offline editing"""
    
    def __init__(self, clone_dir: str = "wordpress_clone"):
        self.wp_api = WordPressAPI()
        self.clone_dir = Path(clone_dir)
        self.clone_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        (self.clone_dir / "pages").mkdir(exist_ok=True)
        (self.clone_dir / "posts").mkdir(exist_ok=True)
        (self.clone_dir / "assets").mkdir(exist_ok=True)
        (self.clone_dir / "css").mkdir(exist_ok=True)
        
        self.manifest = {
            "site_url": self.wp_api.base_url,
            "cloned_at": datetime.now().isoformat(),
            "pages": {},
            "posts": {},
            "theme_css": "",
            "custom_css": ""
        }
    
    def fetch_theme_assets(self):
        """Fetch theme CSS and assets"""
        print("Fetching theme assets...")
        
        try:
            # Get site homepage to extract theme CSS
            response = requests.get(self.wp_api.base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all CSS links
            css_links = soup.find_all('link', rel='stylesheet')
            combined_css = ""
            
            for link in css_links:
                href = link.get('href')
                if href:
                    try:
                        # Download CSS file
                        css_response = requests.get(href)
                        if css_response.status_code == 200:
                            combined_css += f"\n/* CSS from: {href} */\n"
                            combined_css += css_response.text + "\n"
                    except:
                        print(f"Could not fetch CSS: {href}")
            
            # Save combined CSS
            css_file = self.clone_dir / "css" / "theme.css"
            css_file.write_text(combined_css)
            self.manifest["theme_css"] = "css/theme.css"
            
            # Extract inline styles
            inline_styles = soup.find_all('style')
            if inline_styles:
                inline_css = "\n".join([style.string for style in inline_styles if style.string])
                (self.clone_dir / "css" / "inline.css").write_text(inline_css)
            
            print(f"✓ Saved theme CSS ({len(combined_css)} bytes)")
            
        except Exception as e:
            print(f"Error fetching theme assets: {e}")
    
    def pull_all_pages(self):
        """Pull all pages from WordPress"""
        print("\nPulling all pages...")
        
        try:
            # Get all pages
            response = self.wp_api.request("/wp/v2/pages", params={"per_page": 100})
            if response.startswith("Error"):
                print(f"Error fetching pages: {response}")
                return
            
            pages = json.loads(response)
            
            for page in pages:
                page_id = page['id']
                title = page.get('title', {}).get('rendered', 'Untitled')
                print(f"  Pulling page: {title} (ID: {page_id})")
                
                # Create page directory
                page_dir = self.clone_dir / "pages" / f"page_{page_id}"
                page_dir.mkdir(exist_ok=True)
                
                # Extract content
                content = page.get('content', {}).get('rendered', '')
                
                # Extract custom CSS from content
                custom_css = ""
                style_matches = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
                if style_matches:
                    custom_css = '\n'.join(style_matches)
                    css_file = page_dir / "custom.css"
                    css_file.write_text(custom_css)
                
                # Build complete HTML file
                html_content = self.build_html_file(title, content, custom_css)
                
                # Save HTML file
                html_file = page_dir / "index.html"
                html_file.write_text(html_content)
                
                # Save metadata
                metadata = {
                    "id": page_id,
                    "title": title,
                    "slug": page.get('slug', ''),
                    "status": page.get('status', ''),
                    "link": page.get('link', ''),
                    "modified": page.get('modified', ''),
                    "has_custom_css": bool(custom_css)
                }
                
                meta_file = page_dir / "metadata.json"
                meta_file.write_text(json.dumps(metadata, indent=2))
                
                # Update manifest
                self.manifest["pages"][str(page_id)] = {
                    "title": title,
                    "path": f"pages/page_{page_id}/index.html",
                    "metadata": f"pages/page_{page_id}/metadata.json"
                }
                
            print(f"\n✓ Pulled {len(pages)} pages successfully")
            
        except Exception as e:
            print(f"Error pulling pages: {e}")
    
    def build_html_file(self, title: str, content: str, custom_css: str = "") -> str:
        """Build a complete HTML file with all styling"""
        
        # Read theme CSS if available
        theme_css_content = ""
        theme_css_file = self.clone_dir / "css" / "theme.css"
        if theme_css_file.exists():
            theme_css_content = f'<link rel="stylesheet" href="../../css/theme.css">'
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {theme_css_content}
    <style>
        /* WordPress defaults */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, sans-serif;
            font-size: 16px;
            line-height: 1.7;
            color: #333;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        h1 {{ font-size: 2.5em; margin: 0.67em 0; }}
        h2 {{ font-size: 2em; margin: 0.83em 0; }}
        h3 {{ font-size: 1.5em; margin: 1em 0; }}
        
        a {{ color: #0073aa; text-decoration: underline; }}
        a:hover {{ color: #005177; }}
        
        /* WordPress blocks */
        .wp-block-button__link {{
            background: #0073aa;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 4px;
            display: inline-block;
        }}
        
        {custom_css}
    </style>
</head>
<body>
    <article class="wp-site-content">
        <h1 class="page-title">{title}</h1>
        <div class="page-content">
            {content}
        </div>
    </article>
</body>
</html>"""
        
        return html
    
    def save_manifest(self):
        """Save the clone manifest"""
        manifest_file = self.clone_dir / "manifest.json"
        manifest_file.write_text(json.dumps(self.manifest, indent=2))
        print(f"\n✓ Saved manifest to {manifest_file}")
    
    def clone_site(self):
        """Clone the entire WordPress site"""
        print(f"Starting WordPress clone to: {self.clone_dir}")
        print(f"Site: {self.wp_api.base_url}")
        print("-" * 50)
        
        # Fetch theme assets
        self.fetch_theme_assets()
        
        # Pull all pages
        self.pull_all_pages()
        
        # Save manifest
        self.save_manifest()
        
        print("\n✅ Clone complete!")
        print(f"📁 Files saved to: {self.clone_dir.absolute()}")
        
        return self.clone_dir


def main():
    """Run the clone process"""
    cloner = WordPressClone()
    clone_dir = cloner.clone_site()
    
    # Show summary
    print("\nClone Summary:")
    print(f"- Pages cloned: {len(cloner.manifest['pages'])}")
    print(f"- Location: {clone_dir}")
    print("\nYou can now:")
    print("1. Edit HTML files locally")
    print("2. Preview in browser")
    print("3. Push changes back to WordPress")


if __name__ == "__main__":
    main()