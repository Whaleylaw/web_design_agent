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

# Enable LangSmith tracing for debugging
def setup_langsmith_tracing():
    """Setup LangSmith tracing if available"""
    try:
        if os.getenv("LANGSMITH_API_KEY"):
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = "web-design-agent"
            print("✅ LangSmith tracing enabled")
        return True
    except Exception as e:
        print(f"⚠️ LangSmith setup failed: {e}")
        return False

setup_langsmith_tracing()

# Project paths  
PROJECT_ROOT = Path.cwd()
DEPLOY_DIR = PROJECT_ROOT / "deploy" / "public"  # Live pages that Netlify serves
WORKING_DIR = PROJECT_ROOT / "working" / "pages"  # Working versions for editing

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
    """List all available pages by their actual names."""
    try:
        if not DEPLOY_DIR.exists():
            return "❌ Deploy directory not found"
        
        pages = []
        for page_file in DEPLOY_DIR.iterdir():
            if page_file.is_file() and page_file.suffix == ".html":
                page_name = page_file.stem  # filename without .html
                pages.append(f"📄 {page_name}: {page_file}")
        
        # Also check pages subdirectory
        pages_subdir = DEPLOY_DIR / "pages"
        if pages_subdir.exists():
            for page_file in pages_subdir.iterdir():
                if page_file.is_file() and page_file.suffix == ".html":
                    page_name = f"pages/{page_file.stem}"
                    pages.append(f"📄 {page_name}: {page_file}")
        
        if not pages:
            return "ℹ️ No pages found"
        
        pages.sort()  # Sort alphabetically
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
def get_working_version(page_name: str) -> str:
    """Get the working version of a page, creating it if it doesn't exist."""
    try:
        # Determine source file path
        if "/" in page_name:  # pages/index format
            source_file = DEPLOY_DIR / f"{page_name}.html"
        else:
            source_file = DEPLOY_DIR / f"{page_name}.html"
        
        if not source_file.exists():
            return f"❌ Page '{page_name}' not found in deploy directory"
        
        # Create working directory if needed
        WORKING_DIR.mkdir(parents=True, exist_ok=True)
        
        # Working file path
        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
        
        # If working version doesn't exist, copy from deploy
        if not working_file.exists():
            import shutil
            shutil.copy2(source_file, working_file)
            return f"✅ Created working version: {working_file}"
        
        return f"✅ Working version exists: {working_file}"
        
    except Exception as e:
        return f"❌ Error getting working version: {str(e)}"

@tool
def deploy_working_version(page_name: str) -> str:
    """Deploy working version back to live site (copy working → deploy)."""
    try:
        # Working file path
        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
        
        if not working_file.exists():
            return f"❌ No working version found for '{page_name}'"
        
        # Determine destination file path
        if "/" in page_name:  # pages/index format
            dest_file = DEPLOY_DIR / f"{page_name}.html"
        else:
            dest_file = DEPLOY_DIR / f"{page_name}.html"
        
        # Copy working version to deploy
        import shutil
        shutil.copy2(working_file, dest_file)
        
        return f"✅ Deployed working version of '{page_name}' to live site: {dest_file}"
        
    except Exception as e:
        return f"❌ Error deploying working version: {str(e)}"

def create_simple_agent():
    """Create a simple agent with just essential tools."""
    model = get_model()
    
    tools = [
        read_file,
        write_file, 
        list_pages,
        get_working_version,
        deploy_working_version,
        git_commit_and_push,
        check_git_status
    ]
    
    system_prompt = """You are a precise web design agent that edits HTML pages for Netlify deployment.

CRITICAL ACCURACY RULES:
1. 🎯 ALWAYS check if user is viewing a page in the canvas (CONTEXT message)
2. 📖 ALWAYS read the file first before making ANY changes  
3. ✅ ALWAYS verify you're editing the correct page after reading
4. 🔍 ALWAYS double-check your work using reflection

PAGE CONTEXT AWARENESS:
- If user message includes "CONTEXT: User is currently viewing page 'X'", use that page when no specific page is mentioned
- When user says "change the background" without specifying a page, use the currently viewed page
- When user says "add a 😊" without specifying a page, use the currently viewed page
- Only ask for page clarification if no page is specified AND no page is currently being viewed

REFLECTION PROCESS - After each action, ask yourself:
- "Did I edit the correct page that the user intended?"
- "Did I use the currently viewed page context when appropriate?"
- "Did I make the exact changes requested?"
- "Are my changes actually saved to the right file?"

WORKFLOW FOR EVERY EDIT:
1. Check for CONTEXT about currently viewed page
2. If user doesn't specify page, use the currently viewed page from context
3. get_working_version(page_name) - Get/create working version
4. read_file("working/pages/[page_name].html") - Read working version
5. Make changes carefully to working version
6. write_file("working/pages/[page_name].html", updated_content)
7. Confirm: "I successfully modified [page_name] with [specific changes]"

AVAILABLE TOOLS:
- list_pages() - Show all pages (happy, about, lawyer-now, etc.)
- get_working_version(page_name) - Create working copy for editing
- read_file() - Read any file content
- write_file() - Write/update files  
- deploy_working_version(page_name) - Deploy working version to live site
- git_commit_and_push() - Commit & push (only when asked)
- check_git_status() - Check uncommitted changes

IMPORTANT:
- Use currently viewed page context to avoid asking unnecessary questions
- NEVER commit changes unless user explicitly asks
- ALWAYS state which page you modified and what changes you made
- Preserve all existing HTML structure"""

    return create_react_agent(model, tools, prompt=system_prompt)

if __name__ == "__main__":
    agent = create_simple_agent()
    print("✅ Simple web design agent created!") 