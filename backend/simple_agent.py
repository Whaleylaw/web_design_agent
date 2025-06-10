#!/usr/bin/env python3
"""
Simplified Web Design Agent
Basic file operations + Git workflow
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
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

def setup_langgraph_config():
    """Setup LangGraph configuration"""
    os.environ["LANGGRAPH_DEFAULT_RECURSION_LIMIT"] = "50"
    print("✅ LangGraph recursion limit set to 50")

setup_langsmith_tracing()
setup_langgraph_config()

# Project paths  
PROJECT_ROOT = Path.cwd()

def get_model(model_name: str = "claude-sonnet-4-20250514"):
    """Get Claude model"""
    return ChatAnthropic(model=model_name, temperature=0.1)

@tool
def read_file(file_path: str) -> str:
    """Read any file's contents."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        if not path.exists():
            return f"❌ File not found: {file_path}"
        
        content = path.read_text(encoding='utf-8')
        return f"📄 Contents of {file_path}:\n\n{content}"
    except Exception as e:
        return f"❌ Error reading {file_path}: {str(e)}"

@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to any file. Creates new files or overwrites existing ones."""
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
def list_directory(directory_path: str) -> str:
    """List contents of any directory."""
    try:
        path = Path(directory_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        if not path.exists():
            return f"❌ Directory not found: {directory_path}"
        
        if not path.is_dir():
            return f"❌ Path is not a directory: {directory_path}"
        
        items = []
        for item in sorted(path.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} bytes)")
            elif item.is_dir():
                items.append(f"📁 {item.name}/")
        
        if not items:
            return f"📂 Directory {directory_path} is empty"
        
        return f"📂 Contents of {directory_path}:\n\n" + "\n".join(items)
    except Exception as e:
        return f"❌ Error listing {directory_path}: {str(e)}"

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

@tool
def commit_specific_files(files: str, message: str = "Update specific files") -> str:
    """Commit only specific files (comma-separated list) and push to GitHub."""
    try:
        os.chdir(PROJECT_ROOT)
        
        # Parse file list
        file_list = [f.strip() for f in files.split(',')]
        
        # Add specific files
        for file_path in file_list:
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
        
        return f"✅ Successfully committed and pushed specific files!\n📁 Files: {files}\n📝 Message: {message}\n🚀 Netlify will auto-deploy"
        
    except Exception as e:
        return f"❌ Git operation failed: {str(e)}"

@tool
def commit_current_page(page_name: str, message: str = None) -> str:
    """Commit only the current page being worked on."""
    try:
        if not message:
            message = f"Update {page_name} page"
        
        # Determine the file path for the page
        file_path = f"deploy/public/{page_name}.html"
        
        return commit_specific_files(file_path, message)
        
    except Exception as e:
        return f"❌ Error committing current page: {str(e)}"

def create_simple_agent():
    """Create the web design agent with basic file operations"""
    # Load environment variables
    load_dotenv()
    
    # Setup tracing and configuration
    setup_langsmith_tracing()
    setup_langgraph_config()
    
    # Initialize model
    model = get_model()
    
    # Define tools - basic file operations + git
    tools = [
        read_file,
        write_file,
        list_directory,
        check_git_status,
        commit_current_page,
        commit_specific_files,
        git_commit_and_push
    ]

    # Updated system prompt
    system_prompt = """You are a web design agent with basic file system operations.

FOLDER STRUCTURE:
- deploy/public/ = Live HTML pages that Netlify serves
- working/pages/ = Working versions of HTML pages for safe editing  
- markdown/deployed/ = Markdown copies of live pages (for human readability)
- markdown/working/ = Markdown copies of working pages (for human readability)

BASIC TOOLS:
1. read_file(path) - Read any file
2. write_file(path, content) - Write/create any file 
3. list_directory(path) - List directory contents
4. Git tools for committing changes

WORKFLOW:
1. Use list_directory() to see what's in each folder (including discovering available pages)
2. Use read_file() to view HTML or markdown files
3. Use write_file() to create/edit HTML pages
4. Keep markdown files in sync when you edit HTML
5. Use git tools to commit and deploy changes

TO DISCOVER AVAILABLE PAGES: Use list_directory("deploy/public") to see current HTML files

KEY PRINCIPLES:
- You can read/write ANY file in ANY folder
- Markdown files are just readable copies of HTML pages
- When editing HTML, update the corresponding markdown file too
- Nothing is permanent until committed to git
- Always use full relative paths (e.g., "deploy/public/index.html")

Remember: You have full file system access. Use it wisely and keep things organized."""

    # Create agent with recursion limit applied via config
    agent = create_react_agent(model, tools, prompt=system_prompt)
    
    # Wrapper class to automatically apply recursion limit
    class AgentWithConfig:
        def __init__(self, agent):
            self.agent = agent
            
        def invoke(self, inputs, config=None):
            # Merge user config with our default recursion limit
            merged_config = {"recursion_limit": 50}
            if config:
                merged_config.update(config)
            return self.agent.invoke(inputs, config=merged_config)
    
    return AgentWithConfig(agent)

if __name__ == "__main__":
    agent = create_simple_agent()
    print("✅ Simple web design agent created!") 