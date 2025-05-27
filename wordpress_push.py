#!/usr/bin/env python3
"""
WordPress Push System - Push local changes back to WordPress
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import difflib
from wordpress_tools import WordPressAPI

class WordPressPush:
    """Push local changes back to WordPress"""
    
    def __init__(self, clone_dir: str = "wordpress_clone"):
        self.wp_api = WordPressAPI()
        self.clone_dir = Path(clone_dir)
        self.manifest_file = self.clone_dir / "manifest.json"
        
        if not self.manifest_file.exists():
            raise FileNotFoundError(f"No clone found at {self.clone_dir}")
        
        with open(self.manifest_file) as f:
            self.manifest = json.load(f)
    
    def detect_changes(self) -> List[Dict]:
        """Detect which files have changed"""
        changes = []
        
        print("Detecting changes...")
        
        # Check each page
        for page_id, page_info in self.manifest["pages"].items():
            page_dir = self.clone_dir / f"pages/page_{page_id}"
            html_file = page_dir / "index.html"
            
            if html_file.exists():
                # Get current content from WordPress
                try:
                    response = self.wp_api.request(f"/wp/v2/pages/{page_id}")
                    if not response.startswith("Error"):
                        wp_data = json.loads(response)
                        wp_content = wp_data.get('content', {}).get('rendered', '')
                        
                        # Read local content
                        local_html = html_file.read_text()
                        soup = BeautifulSoup(local_html, 'html.parser')
                        
                        # Extract just the content div
                        content_div = soup.find('div', class_='page-content')
                        local_content = str(content_div) if content_div else ""
                        
                        # Compare content
                        if self.normalize_html(wp_content) != self.normalize_html(local_content):
                            changes.append({
                                "page_id": page_id,
                                "title": page_info["title"],
                                "type": "content",
                                "local_file": str(html_file)
                            })
                        
                        # Check for CSS changes
                        custom_css_file = page_dir / "custom.css"
                        if custom_css_file.exists():
                            local_css = custom_css_file.read_text()
                            # Extract CSS from WordPress content
                            import re
                            wp_css_matches = re.findall(r'<style[^>]*>(.*?)</style>', wp_content, re.DOTALL)
                            wp_css = '\n'.join(wp_css_matches)
                            
                            if local_css.strip() != wp_css.strip():
                                changes.append({
                                    "page_id": page_id,
                                    "title": page_info["title"],
                                    "type": "css",
                                    "local_file": str(custom_css_file)
                                })
                
                except Exception as e:
                    print(f"  Error checking page {page_id}: {e}")
        
        return changes
    
    def normalize_html(self, html: str) -> str:
        """Normalize HTML for comparison"""
        # Remove extra whitespace
        html = ' '.join(html.split())
        # Remove WordPress auto-p tags
        html = html.replace('<p>&nbsp;</p>', '')
        return html.strip()
    
    def show_diff(self, page_id: str):
        """Show diff for a specific page"""
        page_dir = self.clone_dir / f"pages/page_{page_id}"
        html_file = page_dir / "index.html"
        
        # Get WordPress content
        response = self.wp_api.request(f"/wp/v2/pages/{page_id}")
        if response.startswith("Error"):
            print(f"Error fetching page: {response}")
            return
        
        wp_data = json.loads(response)
        wp_content = wp_data.get('content', {}).get('rendered', '')
        
        # Get local content
        local_html = html_file.read_text()
        soup = BeautifulSoup(local_html, 'html.parser')
        content_div = soup.find('div', class_='page-content')
        local_content = content_div.decode_contents() if content_div else ""
        
        # Show diff
        diff = difflib.unified_diff(
            wp_content.splitlines(keepends=True),
            local_content.splitlines(keepends=True),
            fromfile='WordPress',
            tofile='Local',
            n=3
        )
        
        print("\nContent differences:")
        print(''.join(diff))
    
    def push_page(self, page_id: str, dry_run: bool = False):
        """Push a single page to WordPress"""
        page_dir = self.clone_dir / f"pages/page_{page_id}"
        html_file = page_dir / "index.html"
        
        if not html_file.exists():
            print(f"Error: HTML file not found for page {page_id}")
            return False
        
        # Read local HTML
        local_html = html_file.read_text()
        soup = BeautifulSoup(local_html, 'html.parser')
        
        # Extract content
        content_div = soup.find('div', class_='page-content')
        if not content_div:
            print(f"Error: No content div found in {html_file}")
            return False
        
        # Get inner HTML
        new_content = content_div.decode_contents()
        
        # Check for custom CSS
        custom_css = ""
        custom_css_file = page_dir / "custom.css"
        if custom_css_file.exists():
            custom_css = custom_css_file.read_text()
            if custom_css.strip():
                # Wrap CSS in style tags
                new_content = f"""<!-- Custom CSS Added by AI Assistant -->
<style>
{custom_css}
</style>
<!-- End Custom CSS -->
{new_content}"""
        
        if dry_run:
            print(f"\n[DRY RUN] Would update page {page_id} with content:")
            print("-" * 50)
            print(new_content[:500] + "..." if len(new_content) > 500 else new_content)
            print("-" * 50)
            return True
        
        # Update WordPress
        print(f"Pushing page {page_id}...")
        try:
            update_data = {"content": new_content}
            response = self.wp_api.request(f"/wp/v2/pages/{page_id}", "PATCH", update_data)
            
            if response.startswith("Error"):
                print(f"  ❌ Error: {response}")
                return False
            else:
                print(f"  ✓ Successfully updated page {page_id}")
                return True
                
        except Exception as e:
            print(f"  ❌ Error pushing page: {e}")
            return False
    
    def push_all_changes(self, dry_run: bool = False):
        """Push all detected changes"""
        changes = self.detect_changes()
        
        if not changes:
            print("✓ No changes detected")
            return
        
        print(f"\nFound {len(changes)} changed files:")
        for change in changes:
            print(f"  - {change['title']} ({change['type']})")
        
        if dry_run:
            print("\n[DRY RUN MODE - No changes will be made]")
        else:
            confirm = input("\nPush these changes to WordPress? (y/N): ")
            if confirm.lower() != 'y':
                print("Push cancelled")
                return
        
        # Push each change
        success_count = 0
        for change in changes:
            if change['type'] in ['content', 'css']:
                if self.push_page(change['page_id'], dry_run):
                    success_count += 1
        
        print(f"\n✅ Push complete: {success_count}/{len(changes)} pages updated")
    
    def status(self):
        """Show status of local changes"""
        changes = self.detect_changes()
        
        print(f"WordPress Clone Status")
        print(f"Site: {self.manifest['site_url']}")
        print(f"Cloned: {self.manifest['cloned_at']}")
        print("-" * 50)
        
        if not changes:
            print("✓ No changes (in sync with WordPress)")
        else:
            print(f"📝 {len(changes)} files with changes:")
            for change in changes:
                print(f"   M  {change['title']} ({change['type']})")
        
        print(f"\nTotal pages: {len(self.manifest['pages'])}")


def main():
    """Run push commands"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Push WordPress changes')
    parser.add_argument('command', choices=['status', 'push', 'diff'], 
                       help='Command to run')
    parser.add_argument('--page-id', help='Specific page ID for diff')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be pushed without pushing')
    
    args = parser.parse_args()
    
    pusher = WordPressPush()
    
    if args.command == 'status':
        pusher.status()
    elif args.command == 'push':
        pusher.push_all_changes(dry_run=args.dry_run)
    elif args.command == 'diff':
        if args.page_id:
            pusher.show_diff(args.page_id)
        else:
            print("Please specify --page-id for diff")


if __name__ == "__main__":
    main()