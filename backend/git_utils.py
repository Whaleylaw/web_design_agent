#!/usr/bin/env python3
"""
Git utility functions for UI operations
These are standalone functions, not LangChain tools
"""

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def ui_check_git_status() -> str:
    """Check git status for UI display."""
    try:
        os.chdir(PROJECT_ROOT)
        
        # Get status
        result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
        status = result.stdout.strip()
        
        # Get recent commits
        result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
        recent_commits = result.stdout.strip()
        
        output = "📊 Git Status:\n\n"
        if status:
            output += f"🔄 Uncommitted changes:\n{status}\n\n"
            output += "📋 Files ready to commit:\n"
            for line in status.split('\n'):
                if line.strip():
                    status_code = line[:2]
                    filename = line[3:]
                    if status_code.strip() == 'M':
                        output += f"   📝 Modified: {filename}\n"
                    elif status_code.strip() == 'A':
                        output += f"   ➕ Added: {filename}\n"
                    elif status_code.strip() == 'D':
                        output += f"   ❌ Deleted: {filename}\n"
                    elif status_code.strip() == '??':
                        output += f"   ❓ Untracked: {filename}\n"
            output += "\n"
        else:
            output += "✅ Working directory clean\n\n"
        
        output += f"📝 Recent commits:\n{recent_commits}"
        return output
        
    except Exception as e:
        return f"❌ Error checking git status: {str(e)}"

def ui_commit_and_push_all(message: str = "Update website files") -> str:
    """Commit all changes and push to GitHub for UI."""
    try:
        os.chdir(PROJECT_ROOT)
        
        # Add all changes
        result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
        if result.returncode != 0:
            return f"❌ Git add failed: {result.stderr}"
        
        # Check if there are changes to commit
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            return "ℹ️ No changes to commit"
        
        # Commit changes
        result = subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)
        if result.returncode != 0:
            return f"❌ Git commit failed: {result.stderr}"
        
        # Check if upstream is set up
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', '@{upstream}'], capture_output=True, text=True)
        if result.returncode != 0:
            # No upstream set, try to set it up
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip()
            
            # Set upstream to origin/<current_branch>
            upstream_result = subprocess.run(['git', 'branch', '--set-upstream-to=origin/' + current_branch, current_branch], capture_output=True, text=True)
            if upstream_result.returncode == 0:
                print(f"✅ Set upstream branch to origin/{current_branch}")
            else:
                return f"❌ Could not set upstream branch: {upstream_result.stderr}"
        
        # Push to GitHub
        result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        if result.returncode != 0:
            # If push fails, try with --set-upstream as fallback
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip()
            fallback_result = subprocess.run(['git', 'push', '--set-upstream', 'origin', current_branch], capture_output=True, text=True)
            if fallback_result.returncode != 0:
                return f"❌ Git push failed: {result.stderr}\n❌ Fallback push also failed: {fallback_result.stderr}"
        
        return f"✅ Successfully committed and pushed changes!\n📝 Commit message: {message}\n🚀 Netlify will auto-deploy from GitHub"
        
    except Exception as e:
        return f"❌ Git operation failed: {str(e)}"

def ui_commit_current_page(page_name: str, message: str = None) -> str:
    """Commit only the current page for UI."""
    try:
        if not message:
            message = f"Update {page_name} page"
        
        os.chdir(PROJECT_ROOT)
        
        # Determine the file path for the page
        if "/" in page_name:
            file_path = f"deploy/public/{page_name}.html"
        else:
            file_path = f"deploy/public/{page_name}.html"
        
        # Add specific file
        result = subprocess.run(['git', 'add', file_path], capture_output=True, text=True)
        if result.returncode != 0:
            return f"❌ Failed to add {file_path}: {result.stderr}"
        
        # Check if there are changes to commit
        result = subprocess.run(['git', 'status', '--porcelain', '--cached'], capture_output=True, text=True)
        if not result.stdout.strip():
            return "ℹ️ No changes staged for commit"
        
        # Commit changes
        result = subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)
        if result.returncode != 0:
            return f"❌ Git commit failed: {result.stderr}"
        
        # Check if upstream is set up and push
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', '@{upstream}'], capture_output=True, text=True)
        if result.returncode != 0:
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip()
            upstream_result = subprocess.run(['git', 'branch', '--set-upstream-to=origin/' + current_branch, current_branch], capture_output=True, text=True)
            if upstream_result.returncode != 0:
                return f"❌ Could not set upstream branch: {upstream_result.stderr}"
        
        # Push to GitHub
        result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        if result.returncode != 0:
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip()
            fallback_result = subprocess.run(['git', 'push', '--set-upstream', 'origin', current_branch], capture_output=True, text=True)
            if fallback_result.returncode != 0:
                return f"❌ Git push failed: {result.stderr}\n❌ Fallback push also failed: {fallback_result.stderr}"
        
        return f"✅ Successfully committed and pushed {page_name} page!\n📁 File: {file_path}\n📝 Message: {message}\n🚀 Netlify will auto-deploy"
        
    except Exception as e:
        return f"❌ Git operation failed: {str(e)}" 