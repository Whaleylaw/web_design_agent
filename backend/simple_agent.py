#!/usr/bin/env python3
"""
Simplified Web Design Agent
Focuses on: Edit files → Git commit/push → Netlify auto-deploy
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore

# Load environment
load_dotenv()

# Disable LangSmith to avoid errors
os.environ.pop("LANGSMITH_API_KEY", None)
os.environ.pop("LANGSMITH_TRACING", None)

# Project paths
PROJECT_ROOT = Path.cwd()
PAGES_DIR = PROJECT_ROOT / "wordpress_clone" / "pages"
DEPLOY_DIR = PROJECT_ROOT / "deploy" / "public"

def get_model(model_name: str = "gpt-4o-mini"):
    """Get OpenAI model"""
    return ChatOpenAI(model=model_name, temperature=0.1)

@tool
def read_file(file_path: str) -> str:
    """Read a file's contents. Use this to view HTML files."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        if not path.exists():
            return f"❌ File not found: {file_path}"
        
        content = path.read_text(encoding='utf-8')
        
        # Limit content size to prevent loops
        if len(content) > 5000:
            content = content[:5000] + "\n\n... (content truncated for display)"
        
        return f"📄 Contents of {file_path}:\n\n{content}"
    except Exception as e:
        return f"❌ Error reading {file_path}: {str(e)}"

@tool  
def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        path.write_text(content, encoding='utf-8')
        return f"✅ Wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"❌ Error writing {file_path}: {str(e)}"

@tool
def list_pages() -> str:
    """List all available pages."""
    try:
        if not PAGES_DIR.exists():
            return "❌ Pages directory not found"
        
        pages = []
        for page_dir in PAGES_DIR.iterdir():
            if page_dir.is_dir() and page_dir.name.startswith("page_"):
                page_id = page_dir.name.replace("page_", "")
                index_file = page_dir / "index.html"
                if index_file.exists():
                    pages.append(f"📄 Page {page_id}: {index_file}")
        
        if not pages:
            return "ℹ️ No pages found"
        
        return "📋 Available pages:\n\n" + "\n".join(pages)
    except Exception as e:
        return f"❌ Error listing pages: {str(e)}"

@tool
def git_commit_and_push(message: str = "Update website files") -> str:
    """Commit all changes and push to GitHub (triggers Netlify deployment)."""
    try:
        # Change to project directory
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
        
        # Push to GitHub
        result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        if result.returncode != 0:
            return f"❌ Git push failed: {result.stderr}"
        
        return f"✅ Successfully committed and pushed changes!\n📝 Commit message: {message}\n🚀 Netlify will auto-deploy from GitHub"
        
    except Exception as e:
        return f"❌ Git operation failed: {str(e)}"

@tool
def check_git_status() -> str:
    """Check git status and recent commits."""
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
        else:
            output += "✅ Working directory clean\n\n"
        
        output += f"📝 Recent commits:\n{recent_commits}"
        return output
        
    except Exception as e:
        return f"❌ Error checking git status: {str(e)}"

@tool
def copy_to_deploy(page_id: str) -> str:
    """Copy a page to the deploy directory (for Netlify)."""
    try:
        source_file = PAGES_DIR / f"page_{page_id}" / "index.html"
        
        if not source_file.exists():
            return f"❌ Page {page_id} not found"
        
        # Copy to deploy directory
        DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
        dest_file = DEPLOY_DIR / f"page_{page_id}.html"
        
        import shutil
        shutil.copy2(source_file, dest_file)
        
        return f"✅ Copied page {page_id} to deploy directory: {dest_file}"
        
    except Exception as e:
        return f"❌ Error copying page: {str(e)}"

def create_simple_agent():
    """Create a simple agent with just essential tools."""
    model = get_model()
    
    tools = [
        read_file,
        write_file, 
        list_pages,
        git_commit_and_push,
        check_git_status,
        copy_to_deploy
    ]
    
    system_prompt = """You are a simple web design agent. Your workflow is:

1. **Edit Files**: Read and modify HTML/CSS files in wordpress_clone/pages/page_X/index.html
2. **Git Operations**: Commit changes and push to GitHub
3. **Netlify Auto-Deploy**: GitHub push triggers automatic Netlify deployment

CORE COMMANDS:
- read_file() - Read any file
- write_file() - Write/update files
- list_pages() - Show available pages
- git_commit_and_push() - Commit & push to GitHub (triggers Netlify)
- check_git_status() - Check for uncommitted changes
- copy_to_deploy() - Copy pages to deploy directory

WORKFLOW EXAMPLE:
1. User: "Change page 1 background to blue"
2. read_file("wordpress_clone/pages/page_1/index.html")
3. Modify HTML with blue background
4. write_file("wordpress_clone/pages/page_1/index.html", updated_content)
5. git_commit_and_push("Changed page 1 background to blue")

Keep it simple! You just edit files and push to GitHub."""

    return create_react_agent(model, tools, prompt=system_prompt)

if __name__ == "__main__":
    agent = create_simple_agent()
    print("✅ Simple web design agent created!") 