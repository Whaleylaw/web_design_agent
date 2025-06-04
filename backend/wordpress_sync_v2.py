#!/usr/bin/env python3
"""
WordPress Sync System V2 - Two-File Approach
Uses clone.html (WordPress snapshot) and index.html (working copy) for reliable sync detection
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import difflib

try:
    from .wordpress_tools import WordPressAPI
except ImportError:
    # Handle direct import
    from wordpress_tools import WordPressAPI

class WordPressSyncV2:
    """Two-file approach WordPress sync system"""
    
    def __init__(self, clone_dir: str = "wordpress_clone"):
        self.wp_api = WordPressAPI()
        self.clone_dir = Path(clone_dir)
        self.manifest_file = self.clone_dir / "manifest.json"
        self.old_dir = self.clone_dir / "old"
        self.clones_dir = self.clone_dir / "clones"  # NEW: Timestamped clones directory
        
        # Create directories
        self.clone_dir.mkdir(exist_ok=True)
        self.old_dir.mkdir(exist_ok=True)
        self.clones_dir.mkdir(exist_ok=True)  # NEW: For timestamped clones
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in YYYYMMDD_HHMMSS format"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _normalize_html(self, html_content: str) -> str:
        """Normalize HTML content for reliable comparison by removing insignificant whitespace differences"""
        try:
            # Parse and re-serialize to normalize formatting
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove extra whitespace but preserve essential structure
            normalized = str(soup)
            # Remove multiple consecutive whitespace/newlines
            import re
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized = re.sub(r'>\s+<', '><', normalized)
            return normalized.strip()
        except Exception:
            # If parsing fails, just return original with basic whitespace cleanup
            import re
            return re.sub(r'\s+', ' ', html_content.strip())
    
    def _update_clone_with_timestamp(self, page_id: str, wp_content: str, title: str, operation: str = "clone") -> str:
        """Update clone file with timestamp and archive old version
        
        Args:
            page_id: WordPress page ID
            wp_content: WordPress content to save
            title: Page title
            operation: Operation type (clone, push, etc.)
            
        Returns:
            Timestamp of the new clone file
        """
        page_dir = self.clone_dir / f"pages/page_{page_id}"
        page_dir.mkdir(exist_ok=True)
        
        # Create timestamped clone directory for this page
        page_clones_dir = self.clones_dir / f"page_{page_id}"
        page_clones_dir.mkdir(exist_ok=True)
        
        timestamp = self._get_timestamp()
        
        # Create new clone content with timestamp
        new_clone_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Clone timestamp: {timestamp} ({operation}) -->
</head>
<body>
    <div class="page-content">
        {wp_content}
    </div>
</body>
</html>"""
        
        # 1. Archive current clone.html if it exists
        current_clone = page_dir / "clone.html"
        if current_clone.exists():
            old_content = current_clone.read_text()
            # Extract old timestamp from comment if it exists
            old_timestamp = "unknown"
            if "<!-- Clone timestamp:" in old_content:
                import re
                match = re.search(r'<!-- Clone timestamp: (\d{8}_\d{6})', old_content)
                if match:
                    old_timestamp = match.group(1)
            
            # Archive with old timestamp
            archived_clone = page_clones_dir / f"clone_{old_timestamp}.html"
            shutil.copy2(current_clone, archived_clone)
            print(f"📁 Archived old clone: {archived_clone.name}")
        
        # 2. Save timestamped version
        timestamped_clone = page_clones_dir / f"clone_{timestamp}.html"
        timestamped_clone.write_text(new_clone_html, encoding='utf-8')
        
        # 3. Update current clone.html (for compatibility)
        current_clone.write_text(new_clone_html, encoding='utf-8')
        
        print(f"📅 Created timestamped clone: {timestamped_clone.name}")
        
        return timestamp
    
    def get_clone_history(self, page_id: str) -> List[Dict]:
        """Get history of all clone versions for a page"""
        page_clones_dir = self.clones_dir / f"page_{page_id}"
        
        if not page_clones_dir.exists():
            return []
        
        history = []
        for clone_file in page_clones_dir.glob("clone_*.html"):
            try:
                # Extract timestamp from filename
                timestamp_str = clone_file.stem.replace("clone_", "")
                
                # Parse timestamp
                if len(timestamp_str) == 15:  # YYYYMMDD_HHMMSS
                    date_part = timestamp_str[:8]
                    time_part = timestamp_str[9:]
                    formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                    formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                    
                    # Get operation type from file content
                    content = clone_file.read_text()
                    operation = "clone"
                    if "<!-- Clone timestamp:" in content:
                        import re
                        match = re.search(r'<!-- Clone timestamp: \d{8}_\d{6} \(([^)]+)\)', content)
                        if match:
                            operation = match.group(1)
                    
                    history.append({
                        "timestamp": timestamp_str,
                        "file": str(clone_file),
                        "date": formatted_date,
                        "time": formatted_time,
                        "operation": operation,
                        "size": clone_file.stat().st_size
                    })
            except Exception as e:
                print(f"Warning: Could not parse clone file {clone_file}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history
    
    def restore_from_clone(self, page_id: str, timestamp: str) -> str:
        """Restore index.html from a specific timestamped clone
        
        Args:
            page_id: WordPress page ID
            timestamp: Timestamp of clone to restore from (YYYYMMDD_HHMMSS)
            
        Returns:
            Result message
        """
        page_clones_dir = self.clones_dir / f"page_{page_id}"
        source_clone = page_clones_dir / f"clone_{timestamp}.html"
        
        if not source_clone.exists():
            return f"❌ Clone with timestamp {timestamp} not found for page {page_id}"
        
        try:
            page_dir = self.clone_dir / f"pages/page_{page_id}"
            index_file = page_dir / "index.html"
            
            # Create backup of current index.html
            if index_file.exists():
                backup_timestamp = self._get_timestamp()
                backup_file = page_dir / f"index_backup_{backup_timestamp}.html"
                shutil.copy2(index_file, backup_file)
                print(f"📋 Backed up current index.html to {backup_file.name}")
            
            # Restore from archived clone
            shutil.copy2(source_clone, index_file)
            
            # Also update current clone.html
            clone_file = page_dir / "clone.html"
            shutil.copy2(source_clone, clone_file)
            
            return f"✅ Restored page {page_id} from clone timestamp {timestamp}"
            
        except Exception as e:
            return f"❌ Error restoring page {page_id}: {str(e)}"
    
    def migrate_existing_structure(self) -> str:
        """Migrate existing single-file structure to two-file structure"""
        if not self.clone_dir.exists():
            return "No existing clone to migrate"
        
        pages_dir = self.clone_dir / "pages"
        if not pages_dir.exists():
            return "No pages directory found"
        
        migrated_count = 0
        
        for page_dir in pages_dir.iterdir():
            if page_dir.is_dir() and page_dir.name.startswith("page_"):
                index_file = page_dir / "index.html"
                clone_file = page_dir / "clone.html"
                
                if index_file.exists() and not clone_file.exists():
                    # Copy index.html to clone.html (assume they were in sync when cloned)
                    shutil.copy2(index_file, clone_file)
                    migrated_count += 1
        
        return f"✅ Migrated {migrated_count} pages to two-file structure"
    
    def clone_from_wordpress(self, overwrite_local: bool = False) -> str:
        """Clone all pages from WordPress, creating both clone.html and index.html
        
        Args:
            overwrite_local: If True, overwrites existing index.html files. 
                           If False, preserves local changes and reports conflicts.
        """
        try:
            # FIRST: Detect existing local changes before downloading anything
            existing_local_changes = []
            if not overwrite_local:
                print("Checking for existing local changes...")
                changes = self.detect_changes_v2()
                if changes:
                    existing_local_changes = changes
                    print(f"Found {len(existing_local_changes)} existing local changes that will be preserved")
            
            # Get all pages from WordPress
            pages_response = self.wp_api.request("/wp/v2/pages?per_page=100")
            if pages_response.startswith("Error"):
                return f"❌ Failed to fetch pages: {pages_response}"
            
            pages_data = json.loads(pages_response)
            if not pages_data:
                return "❌ No pages found on WordPress"
            
            # Create directory structure
            pages_dir = self.clone_dir / "pages"
            pages_dir.mkdir(exist_ok=True)
            
            cloned_pages = {}
            success_count = 0
            conflicts_detected = []
            preserved_changes = []
            wordpress_updates = []
            
            for page in pages_data:
                try:
                    page_id = page['id']
                    title = page['title']['rendered']
                    content = page['content']['rendered']
                    
                    # Create page directory
                    page_dir = pages_dir / f"page_{page_id}"
                    page_dir.mkdir(exist_ok=True)
                    
                    # Create standard HTML structure
                    new_wp_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div class="page-content">
        {content}
    </div>
</body>
</html>"""
                    
                    clone_file = page_dir / "clone.html"
                    index_file = page_dir / "index.html"
                    
                    # Check if this page had local changes BEFORE we update anything
                    had_local_changes = any(change["page_id"] == str(page_id) for change in existing_local_changes)
                    
                    # Check if WordPress content changed since last clone
                    wordpress_changed = False
                    if clone_file.exists():
                        old_clone_content = clone_file.read_text(encoding='utf-8')
                        if old_clone_content != new_wp_content:
                            wordpress_changed = True
                            wordpress_updates.append(f"Page {page_id}: {title}")
                    
                    # ALWAYS update clone.html (WordPress snapshot) WITH TIMESTAMP
                    clone_timestamp = self._update_clone_with_timestamp(str(page_id), content, title, "clone")
                    print(f"📅 Page {page_id}: Created timestamped clone_{clone_timestamp}.html")
                    
                    # Handle index.html based on local changes and WordPress changes
                    if not index_file.exists():
                        # No local file exists - create it
                        index_file.write_text(new_wp_content, encoding='utf-8')
                    elif overwrite_local:
                        # User explicitly wants to overwrite local changes
                        index_file.write_text(new_wp_content, encoding='utf-8')
                    elif had_local_changes:
                        # User has local changes - preserve them regardless of WordPress changes
                        if wordpress_changed:
                            conflicts_detected.append({
                                "page_id": page_id,
                                "title": title,
                                "local_file": str(index_file),
                                "clone_file": str(clone_file),
                                "conflict_type": "both_changed"
                            })
                            preserved_changes.append(f"Page {page_id}: {title} (WordPress also updated)")
                        else:
                            conflicts_detected.append({
                                "page_id": page_id,
                                "title": title,
                                "local_file": str(index_file),
                                "clone_file": str(clone_file),
                                "conflict_type": "local_only"
                            })
                            preserved_changes.append(f"Page {page_id}: {title} (local changes only)")
                        # DO NOT overwrite index.html - preserve local changes
                    elif wordpress_changed:
                        # WordPress changed but no local changes - update working copy
                        index_file.write_text(new_wp_content, encoding='utf-8')
                        wordpress_updates.append(f"Page {page_id}: {title} (updated from WordPress)")
                    # If neither changed, do nothing to index.html
                    
                    # Create metadata
                    metadata = {
                        "id": page_id,
                        "title": title,
                        "slug": page.get('slug', ''),
                        "status": page.get('status', ''),
                        "date": page.get('date', ''),
                        "modified": page.get('modified', ''),
                        "cloned_at": datetime.now().isoformat()
                    }
                    
                    metadata_file = page_dir / "metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    cloned_pages[str(page_id)] = {
                        "title": title,
                        "path": f"pages/page_{page_id}/index.html",
                        "clone_path": f"pages/page_{page_id}/clone.html",
                        "metadata": f"pages/page_{page_id}/metadata.json"
                    }
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"Warning: Failed to clone page {page.get('id', 'unknown')}: {e}")
                    continue
            
            # Update manifest
            manifest = {
                "site_url": "https://lawyerincorporated.com",
                "cloned_at": datetime.now().isoformat(),
                "pages": cloned_pages,
                "posts": {},
                "theme_css": "css/theme.css",
                "custom_css": "",
                "version": "2.0"  # Mark as new version
            }
            
            # Write manifest atomically
            temp_manifest = self.manifest_file.with_suffix('.tmp')
            with open(temp_manifest, 'w') as f:
                json.dump(manifest, f, indent=2)
            temp_manifest.replace(self.manifest_file)
            
            # Build result message
            result = f"✅ **WordPress Clone Complete (V2 Two-File System)**\n\n"
            result += f"📊 **Summary:**\n"
            result += f"- {success_count} pages processed\n"
            result += f"- WordPress snapshots updated (clone.html)\n"
            
            if conflicts_detected:
                result += f"- ⚠️ **{len(conflicts_detected)} CONFLICTS DETECTED**\n\n"
                result += f"🔄 **Preserved Local Changes:**\n"
                for change in preserved_changes:
                    result += f"- {change}\n"
                result += f"\n💡 **What happened:**\n"
                result += f"You have local changes that were preserved in index.html.\n"
                if any(c["conflict_type"] == "both_changed" for c in conflicts_detected):
                    result += f"WordPress was also updated, creating conflicts.\n"
                result += f"Use `show_page_diff_v2` to see differences.\n"
                result += f"Use `push_changes_v2` to upload your changes to WordPress.\n"
                result += f"Use `force_overwrite_from_wordpress` to discard local changes.\n"
            elif wordpress_updates:
                result += f"- 📥 **{len(wordpress_updates)} pages updated from WordPress**\n\n"
                result += f"🔄 **WordPress Updates Applied:**\n"
                for update in wordpress_updates:
                    result += f"- {update}\n"
                result += f"\n💡 Working copies updated with latest WordPress content.\n"
            else:
                result += f"- ✅ Files are in perfect sync\n\n"
                result += f"📝 **Cloned pages:**\n"
                for page_id, info in cloned_pages.items():
                    result += f"- Page {page_id}: {info['title']}\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error cloning: {str(e)}"
    
    def detect_changes_v2(self) -> List[Dict]:
        """Detect changes by comparing index.html to clone.html (much more reliable)"""
        if not self.manifest_file.exists():
            return []
        
        with open(self.manifest_file) as f:
            manifest = json.load(f)
        
        changes = []
        
        for page_id, page_info in manifest.get("pages", {}).items():
            page_dir = self.clone_dir / f"pages/page_{page_id}"
            clone_file = page_dir / "clone.html"
            index_file = page_dir / "index.html"
            
            if clone_file.exists() and index_file.exists():
                try:
                    clone_content = clone_file.read_text(encoding='utf-8')
                    index_content = index_file.read_text(encoding='utf-8')
                    
                    # Simple file comparison - no complex parsing needed!
                    if clone_content != index_content:
                        changes.append({
                            "page_id": page_id,
                            "title": page_info["title"],
                            "type": "content",
                            "local_file": str(index_file),
                            "clone_file": str(clone_file)
                        })
                        
                except Exception as e:
                    print(f"Error comparing page {page_id}: {e}")
                    continue
        
        return changes
    
    def show_diff_v2(self, page_id: str) -> str:
        """Show differences between working copy and WordPress snapshot"""
        page_dir = self.clone_dir / f"pages/page_{page_id}"
        clone_file = page_dir / "clone.html"
        index_file = page_dir / "index.html"
        
        if not clone_file.exists():
            return f"❌ No clone file found for page {page_id}"
        
        if not index_file.exists():
            return f"❌ No index file found for page {page_id}"
        
        try:
            clone_content = clone_file.read_text()
            index_content = index_file.read_text()
            
            if clone_content == index_content:
                return f"✅ Page {page_id}: No differences (files are identical)"
            
            # Show diff
            diff = list(difflib.unified_diff(
                clone_content.splitlines(keepends=True),
                index_content.splitlines(keepends=True),
                fromfile='clone.html (WordPress)',
                tofile='index.html (Working Copy)',
                n=3
            ))
            
            result = f"📋 **Differences for Page {page_id}:**\n\n"
            result += "```diff\n"
            result += ''.join(diff[:50])  # Show first 50 lines
            if len(diff) > 50:
                result += f"... ({len(diff) - 50} more lines)\n"
            result += "```"
            
            return result
            
        except Exception as e:
            return f"❌ Error showing diff: {str(e)}"
    
    def push_page_v2(self, page_id: str, dry_run: bool = False) -> bool:
        """Push a complete page to WordPress, preserving all styling and structure"""
        page_dir = self.clone_dir / f"pages/page_{page_id}"
        index_file = page_dir / "index.html"
        clone_file = page_dir / "clone.html"
        
        if not index_file.exists():
            print(f"❌ No index file for page {page_id}")
            return False
        
        try:
            # Read the complete local HTML file
            index_html = index_file.read_text()
            soup = BeautifulSoup(index_html, 'html.parser')
            
            # APPROACH 1: Try to push the complete body content with embedded styles
            body = soup.find('body')
            head = soup.find('head')
            
            if body and head:
                # Extract CSS from head
                style_tags = head.find_all('style')
                all_css = ""
                for style_tag in style_tags:
                    all_css += style_tag.get_text() + "\n"
                
                # Get body content
                body_content = body.decode_contents()
                
                # Create WordPress-compatible content with embedded styles
                if all_css.strip():
                    # Embed the CSS in a style tag within the content
                    content_to_push = f"""<style>
{all_css}
</style>
{body_content}"""
                else:
                    # No CSS found, just use body content
                    content_to_push = body_content
                    
                print(f"📄 Preparing to push {len(content_to_push)} characters of styled content")
                
            else:
                # FALLBACK: If no proper HTML structure, try pushing the entire content
                print(f"⚠️ No standard HTML structure found, pushing entire file content")
                content_to_push = index_html
            
            if dry_run:
                print(f"[DRY RUN] Would push page {page_id}")
                print(f"Content preview: {content_to_push[:200]}...")
                return True
            
            # Push to WordPress
            print(f"🚀 Pushing styled page {page_id} to WordPress...")
            update_data = {"content": content_to_push}
            response = self.wp_api.request(f"/wp/v2/pages/{page_id}", "PATCH", update_data)
            
            if response.startswith("Error"):
                print(f"❌ Push failed: {response}")
                return False
            
            # VERIFICATION: Get what WordPress actually stored
            print(f"🔍 Verifying push for page {page_id}...")
            verification_response = self.wp_api.request(f"/wp/v2/pages/{page_id}")
            
            if verification_response.startswith("Error"):
                print(f"⚠️ Push succeeded but verification failed: {verification_response}")
                return True  # Push worked, but couldn't verify
            
            # Parse verification response
            wp_data = json.loads(verification_response)
            wp_content = wp_data.get('content', {}).get('rendered', '')
            title = wp_data.get('title', {}).get('rendered', 'Unknown')
            
            # UPDATE CLONE TO MATCH WORDPRESS EXACTLY
            push_timestamp = self._update_clone_with_timestamp(page_id, wp_content, title, "push")
            print(f"📅 Updated clone with timestamp after push: clone_{push_timestamp}.html")
            
            # CRITICAL: Also update index.html to match WordPress exactly
            # This ensures perfect sync after push
            wordpress_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Synced with WordPress: {push_timestamp} -->
</head>
<body>
    {wp_content}
</body>
</html>"""
            
            # Update local index.html to match WordPress
            index_file.write_text(wordpress_html, encoding='utf-8')
            
            print(f"✅ Page {page_id} pushed successfully!")
            print(f"   📊 WordPress content length: {len(wp_content)} characters")
            print(f"   🔄 Local files updated to match WordPress")
            return True
                
        except Exception as e:
            print(f"❌ Error pushing page {page_id}: {e}")
            return False
    
    def sync_status_v2(self):
        """Check sync status using V2 file comparison"""
        try:
            manifest_file = Path(self.clone_dir) / "manifest.json"
            if not manifest_file.exists():
                return {"status": "no_manifest", "changes": []}
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            pages = manifest.get("pages", {})
            changes = []
            local_only_pages = []
            
            for page_id, page_info in pages.items():
                page_dir = Path(self.clone_dir) / f"pages/page_{page_id}"
                index_file = page_dir / "index.html"
                clone_file = page_dir / "clone.html"
                metadata_file = page_dir / "metadata.json"
                
                # Check if this is a local-only page
                is_local_only = False
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        is_local_only = metadata.get("local_only", False) or metadata.get("status") == "local_only"
                    except:
                        pass
                
                if is_local_only:
                    # Local-only page (never pushed to WordPress)
                    local_only_pages.append({
                        "page_id": page_id,
                        "title": page_info.get("title", f"Page {page_id}"),
                        "status": "local_only",
                        "reason": "Page created locally, not yet published to WordPress"
                    })
                    continue
                
                # Skip if index.html doesn't exist
                if not index_file.exists():
                    continue
                
                # Skip if clone.html doesn't exist (orphaned page)
                if not clone_file.exists():
                    changes.append({
                        "page_id": page_id,
                        "title": page_info.get("title", f"Page {page_id}"),
                        "status": "no_clone",
                        "reason": "Local page exists but no WordPress snapshot found"
                    })
                    continue
                
                # Compare files
                index_content = self._normalize_html(index_file.read_text())
                clone_content = self._normalize_html(clone_file.read_text())
                
                if index_content != clone_content:
                    changes.append({
                        "page_id": page_id,
                        "title": page_info.get("title", f"Page {page_id}"),
                        "status": "modified",
                        "reason": "Local version differs from WordPress snapshot"
                    })
            
            # Determine overall status
            if local_only_pages and not changes:
                status = "local_only_pages"
            elif changes or local_only_pages:
                status = "needs_sync"
            else:
                status = "synced"
            
            return {
                "status": status,
                "changes": changes,
                "local_only": local_only_pages,
                "summary": {
                    "modified_pages": len(changes),
                    "local_only_pages": len(local_only_pages),
                    "total_pages": len(pages)
                }
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e), "changes": []} 