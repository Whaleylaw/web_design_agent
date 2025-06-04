#!/usr/bin/env python3
"""
Netlify Deployment Tools
Handles copying files from wordpress_clone to deploy directory and triggering deploys
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Optional

class NetlifyDeploy:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.wordpress_dir = self.project_root / "wordpress_clone"
        self.deploy_dir = self.project_root / "deploy"
        self.public_dir = self.deploy_dir / "public"
        
    def get_page_mapping(self) -> Dict[str, str]:
        """Get mapping of page IDs to friendly URLs"""
        return {
            "1": "about.html",
            "6": "lawyer-incorporated.html", 
            "13": "test.html",
            "16": "color-test.html",
            "21": "lawyer-now.html",
            "53": "happy.html"
        }
    
    def copy_page_to_deploy(self, page_id: str) -> bool:
        """Copy a specific page from wordpress_clone to deploy directory"""
        try:
            page_dir = self.wordpress_dir / "pages" / f"page_{page_id}"
            index_file = page_dir / "index.html"
            
            if not index_file.exists():
                print(f"❌ No index.html found for page {page_id}")
                return False
            
            # Get the friendly filename
            mapping = self.get_page_mapping()
            if page_id in mapping:
                filename = mapping[page_id]
            else:
                filename = f"page_{page_id}.html"
            
            # Copy to deploy directory
            dest_file = self.public_dir / filename
            shutil.copy2(index_file, dest_file)
            
            # Also update index.html if this is page 1
            if page_id == "1":
                index_dest = self.public_dir / "index.html"
                shutil.copy2(index_file, index_dest)
            
            print(f"✅ Copied page {page_id} to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error copying page {page_id}: {e}")
            return False
    
    def copy_all_pages_to_deploy(self) -> Dict[str, bool]:
        """Copy all pages from wordpress_clone to deploy directory"""
        results = {}
        mapping = self.get_page_mapping()
        
        for page_id in mapping.keys():
            results[page_id] = self.copy_page_to_deploy(page_id)
        
        return results
    
    def git_commit_and_push(self, message: str = None) -> bool:
        """Commit changes and push to trigger Netlify deploy"""
        try:
            if not message:
                message = f"Deploy update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Change to project root for git commands
            os.chdir(self.project_root)
            
            # Add deploy directory changes
            subprocess.run(["git", "add", "deploy/"], check=True, capture_output=True)
            
            # Check if there are changes to commit
            result = subprocess.run(["git", "diff", "--staged", "--quiet"], capture_output=True)
            if result.returncode == 0:
                print("🔍 No changes to deploy")
                return True
            
            # Commit changes
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            print(f"✅ Committed changes: {message}")
            
            # Push to remote
            subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
            print("🚀 Pushed to GitHub - Netlify deploy triggered!")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git error: {e}")
            return False
        except Exception as e:
            print(f"❌ Deploy error: {e}")
            return False
    
    def deploy_page(self, page_id: str) -> str:
        """Deploy a specific page to Netlify"""
        try:
            print(f"🚀 Deploying page {page_id} to Netlify...")
            
            # Copy page to deploy directory
            if not self.copy_page_to_deploy(page_id):
                return f"❌ Failed to copy page {page_id}"
            
            # Get page title from metadata if available
            metadata_file = self.wordpress_dir / "pages" / f"page_{page_id}" / "metadata.json"
            page_title = f"Page {page_id}"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        page_title = metadata.get('title', f"Page {page_id}")
                except:
                    pass
            
            # Commit and push
            commit_message = f"Deploy {page_title} (page {page_id})"
            if self.git_commit_and_push(commit_message):
                mapping = self.get_page_mapping()
                filename = mapping.get(page_id, f"page_{page_id}.html")
                return f"✅ Page {page_id} ({page_title}) deployed successfully!\n🌐 Will be available at: yoursite.netlify.app/{filename}"
            else:
                return f"❌ Failed to deploy page {page_id}"
                
        except Exception as e:
            return f"❌ Deployment error: {e}"
    
    def deploy_all_pages(self) -> str:
        """Deploy all pages to Netlify"""
        try:
            print("🚀 Deploying all pages to Netlify...")
            
            # Copy all pages
            results = self.copy_all_pages_to_deploy()
            
            # Count successes
            successful = [k for k, v in results.items() if v]
            failed = [k for k, v in results.items() if not v]
            
            if not successful:
                return "❌ No pages copied successfully"
            
            # Commit and push
            commit_message = f"Deploy all pages: {len(successful)} pages updated"
            if self.git_commit_and_push(commit_message):
                result = f"✅ {len(successful)} pages deployed successfully!"
                if failed:
                    result += f"\n⚠️ Failed pages: {', '.join(failed)}"
                result += "\n🌐 Site will update at: yoursite.netlify.app"
                return result
            else:
                return "❌ Failed to push deployment"
                
        except Exception as e:
            return f"❌ Deployment error: {e}"
    
    def get_deploy_status(self) -> str:
        """Check the current deployment status"""
        try:
            # Check if deploy directory exists and has content
            if not self.public_dir.exists():
                return "❌ Deploy directory not found"
            
            files = list(self.public_dir.glob("*.html"))
            page_count = len([f for f in files if f.name != "index.html"])
            
            # Check git status for uncommitted changes
            os.chdir(self.project_root)
            result = subprocess.run(["git", "status", "--porcelain", "deploy/"], 
                                  capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                status = "🔄 Changes ready to deploy"
            else:
                status = "✅ Deployed (up to date)"
            
            return f"{status}\n📁 {page_count} pages in deploy directory\n📂 Files: {', '.join([f.name for f in files])}"
            
        except Exception as e:
            return f"❌ Status check error: {e}"


# Tool functions for the agent
def deploy_page_to_netlify(page_id: str) -> str:
    """Deploy a specific page to Netlify via Git"""
    deployer = NetlifyDeploy()
    return deployer.deploy_page(page_id)

def deploy_all_to_netlify() -> str:
    """Deploy all pages to Netlify via Git"""
    deployer = NetlifyDeploy()
    return deployer.deploy_all_pages()

def check_netlify_deploy_status() -> str:
    """Check current Netlify deployment status"""
    deployer = NetlifyDeploy()
    return deployer.get_deploy_status()


if __name__ == "__main__":
    # Command line interface
    import sys
    
    deployer = NetlifyDeploy()
    
    if len(sys.argv) < 2:
        print("Usage: python netlify_deploy.py [deploy-page <id>|deploy-all|status]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "deploy-page" and len(sys.argv) > 2:
        page_id = sys.argv[2]
        print(deployer.deploy_page(page_id))
    elif command == "deploy-all":
        print(deployer.deploy_all_pages())
    elif command == "status":
        print(deployer.get_deploy_status())
    else:
        print("Unknown command. Use: deploy-page <id>, deploy-all, or status") 