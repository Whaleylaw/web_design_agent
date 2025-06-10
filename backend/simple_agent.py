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
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore
from backend.markdown_generator import generate_markdown_for_page, generate_all_markdown
import shutil

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
DEPLOY_DIR = PROJECT_ROOT / "deploy" / "public"  # Live pages that Netlify serves
WORKING_DIR = PROJECT_ROOT / "working" / "pages"  # Working versions for editing

def get_model(model_name: str = "claude-sonnet-4-20250514"):
    """Get Claude model"""
    return ChatAnthropic(model=model_name, temperature=0.1)

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
    """Write content to a file. WARNING: This overwrites the entire file. Use search_replace_in_file for targeted edits."""
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
def search_replace_in_file(file_path: str, search_text: str, replace_text: str) -> str:
    """Make a targeted edit by replacing specific text in a file. PREFERRED over write_file for edits."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        if not path.exists():
            return f"❌ File not found: {file_path}"
        
        # Read current content
        current_content = path.read_text(encoding='utf-8')
        original_length = len(current_content)
        
        # Check if search text exists
        if search_text not in current_content:
            return f"❌ Search text not found in {file_path}. Please check the exact text to replace."
        
        # Count occurrences
        occurrences = current_content.count(search_text)
        if occurrences > 1:
            return f"⚠️ Found {occurrences} occurrences of search text in {file_path}. Please be more specific to target exactly one instance."
        
        # Perform replacement
        new_content = current_content.replace(search_text, replace_text)
        
        # Write back to file
        path.write_text(new_content, encoding='utf-8')
        new_length = len(new_content)
        
        return f"✅ Successfully replaced text in {file_path}\n📊 File size: {original_length} → {new_length} characters\n🔄 Made 1 replacement"
        
    except Exception as e:
        return f"❌ Error in search/replace for {file_path}: {str(e)}"

@tool
def verify_file_completeness(file_path: str) -> str:
    """Verify that a file is complete and not truncated. Check for proper HTML structure."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        
        if not path.exists():
            return f"❌ File not found: {file_path}"
        
        content = path.read_text(encoding='utf-8')
        
        # Basic completeness checks
        issues = []
        
        # Check if file is too short (likely truncated)
        if len(content) < 100:
            issues.append("⚠️ File is very short, may be truncated")
        
        # For HTML files, check structure
        if file_path.endswith('.html'):
            if not content.strip().startswith('<!DOCTYPE html>') and not content.strip().startswith('<html'):
                issues.append("⚠️ Missing HTML DOCTYPE or opening tag")
            
            if '</html>' not in content:
                issues.append("❌ Missing closing </html> tag - file appears truncated")
            
            if '</body>' not in content:
                issues.append("❌ Missing closing </body> tag - file appears truncated")
            
            if content.count('<html') != content.count('</html>'):
                issues.append("❌ Mismatched <html> tags")
            
            if content.count('<body') != content.count('</body>'):
                issues.append("❌ Mismatched <body> tags")
        
        # Check for abrupt ending (common in truncated files)
        if content.strip().endswith('...') or content.strip().endswith('<!-- '):
            issues.append("❌ File appears to end abruptly - likely truncated")
        
        if issues:
            return f"🔍 File verification for {file_path}:\n" + "\n".join(issues) + f"\n📊 File size: {len(content)} characters"
        else:
            return f"✅ File {file_path} appears complete\n📊 File size: {len(content)} characters"
        
    except Exception as e:
        return f"❌ Error verifying {file_path}: {str(e)}"

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
        if "/" in page_name:
            file_path = f"deploy/public/{page_name}.html"
        else:
            file_path = f"deploy/public/{page_name}.html"
        
        return commit_specific_files(file_path, message)
        
    except Exception as e:
        return f"❌ Error committing current page: {str(e)}"

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

@tool
def get_page_context(page_name: str) -> str:
    """
    Get page context and layout information to help understand what user is referring to.
    
    Args:
        page_name: Name of the page (e.g., 'index', 'about', 'lawyer-incorporated')
    
    Returns:
        Detailed page context with element mappings and layout description
    """
    project_root = Path(__file__).parent.parent
    context_dir = project_root / "page_contexts"
    context_file = context_dir / f"{page_name}_context.md"
    
    if not context_file.exists():
        return f"Context file not found for page '{page_name}'. Available pages: {[f.stem.replace('_context', '') for f in context_dir.glob('*_context.md')]}"
    
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading context file: {e}"

@tool
def create_page(page_name: str, title: str = None, heading: str = None, content: str = None) -> str:
    """
    Create a new HTML page with basic structure.
    
    Args:
        page_name: Name of the page (without .html extension)
        title: Page title (defaults to page_name)
        heading: Main heading (defaults to title)
        content: Additional content to include (optional)
    
    Returns:
        Success message with file path
    """
    try:
        if not title:
            title = page_name.replace('-', ' ').replace('_', ' ').title()
        if not heading:
            heading = title
        
        # Create basic HTML structure
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - LawyersInc</title>
    <style>
        :root {{
            --primary: #2c3e50;
            --secondary: #34495e;
            --accent: #e74c3c;
            --text: #333;
            --light-bg: #f8f9fa;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: var(--light-bg);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        h1 {{
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 2rem;
            text-align: center;
        }}

        .back-link {{
            display: inline-block;
            margin-bottom: 2rem;
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }}

        .back-link:hover {{
            text-decoration: underline;
        }}

        .content {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Home</a>
        <div class="content">
            <h1>{heading}</h1>
            {content or '<p>This page is under construction. More information coming soon.</p>'}
        </div>
    </div>
</body>
</html>'''

        # Create in deploy directory
        deploy_file = DEPLOY_DIR / f"{page_name}.html"
        with open(deploy_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Also create working version
        working_file = WORKING_DIR / f"{page_name}.html"
        with open(working_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return f"✅ Created new page: {page_name}.html\\n📁 Deploy: {deploy_file}\\n📁 Working: {working_file}\\n🎯 Ready to edit and deploy!"
        
    except Exception as e:
        return f"❌ Error creating page: {str(e)}"

@tool
def read_page_as_markdown(page_name: str, version: str = "working") -> str:
    """
    Read a page as markdown to see it like a human would.
    
    Args:
        page_name: Name of the page
        version: "deployed" or "working"
    
    Returns:
        Markdown content of the page
    """
    try:
        markdown_file = PROJECT_ROOT / "markdown" / version / f"{page_name}.md"
        
        if not markdown_file.exists():
            # Generate it if it doesn't exist
            result = generate_markdown_for_page(page_name, version)
            if "❌" in result:
                return result
        
        with open(markdown_file, 'r', encoding='utf-8') as f:
            return f.read()
        
    except Exception as e:
        return f"❌ Error reading markdown: {str(e)}"

@tool
def update_markdown_after_html_change(page_name: str) -> str:
    """
    Update the working markdown after changing HTML.
    Simple function to keep markdown in sync with HTML changes.
    """
    try:
        return generate_markdown_for_page(page_name, "working")
    except Exception as e:
        return f"❌ Error updating markdown: {str(e)}"

@tool
def undo_page_changes(page_name: str) -> str:
    """
    Simple undo: copy deployed version to working version (both HTML and markdown).
    This reverts all changes back to the live/deployed state.
    """
    try:
        # Copy HTML: deployed → working
        deployed_html = DEPLOY_DIR / f"{page_name}.html"
        working_html = WORKING_DIR / f"{page_name}.html"
        
        if not deployed_html.exists():
            return f"❌ Deployed page '{page_name}' not found"
        
        WORKING_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(deployed_html, working_html)
        
        # Update working markdown to match
        markdown_result = generate_markdown_for_page(page_name, "working")
        
        return f"✅ Reverted '{page_name}' to deployed version\n📁 HTML: {working_html}\n📝 {markdown_result}"
        
    except Exception as e:
        return f"❌ Error undoing changes: {str(e)}"

def create_simple_agent():
    """Create the web design agent with enhanced page context understanding"""
    # Load environment variables
    load_dotenv()
    
    # Setup tracing and configuration
    setup_langsmith_tracing()
    setup_langgraph_config()
    
    # Initialize model
    model = get_model()
    
    # Define tools - keep it simple
    tools = [
        get_working_version,
        deploy_working_version, 
        search_replace_in_file,
        verify_file_completeness,
        list_pages,
        check_git_status,
        commit_current_page,
        commit_specific_files,
        git_commit_and_push,
        get_page_context,
        create_page,
        read_page_as_markdown,  # Read pages like humans do
        update_markdown_after_html_change,  # Keep markdown in sync
        undo_page_changes  # Simple undo function
    ]

    # Updated system prompt - keep it simple
    system_prompt = """You are a web design agent helping users modify HTML pages.

SIMPLE WORKFLOW:
1. To see a page like a human: use read_page_as_markdown(page_name, "deployed" or "working")
2. To make changes: use search_replace_in_file() on HTML files
3. After HTML changes: call update_markdown_after_html_change() to keep markdown in sync
4. To undo changes: use undo_page_changes() - copies deployed → working
5. When user asks to CREATE a new page: use create_page() first, then link it from existing pages

UNDERSTANDING PAGES:
- Read markdown versions to see pages like humans do
- Compare deployed vs working markdown to see what changed
- Use page context for layout understanding when needed

SIMPLE UNDO:
- When user says "undo" or "revert": use undo_page_changes(page_name)
- This copies deployed version to working version (both HTML and markdown)

CRITICAL ACCURACY RULES:
- Always use surgical edits with search_replace_in_file() 
- Never rewrite entire files
- Keep markdown in sync after HTML changes
- Verify file completeness after edits

AVAILABLE PAGES: index, about, happy, lawyer-now, lawyer-incorporated, color-test, test, personal-injury

Remember: Keep it simple. Read markdown to see pages, edit HTML precisely, update markdown, undo by copying deployed → working."""

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
    print("✅ Simple web design agent created with page context support!") 