#!/usr/bin/env python3
"""
Simple Streamlit Interface for Web Design Agent
Just: Edit Files → Git Push → Netlify Deploy
"""

import streamlit as st
import sys
import os
import time
from pathlib import Path
import streamlit.components.v1 as components

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.simple_agent import create_simple_agent
from langchain_core.messages import HumanMessage, AIMessage

# Define directory paths locally since agent no longer exports them
DEPLOY_DIR = project_root / "deploy" / "public"
WORKING_DIR = project_root / "working" / "pages"

def get_working_version(page_name):
    """Create working version by copying from deploy directory if it doesn't exist."""
    try:
        # Determine source file path
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

def deploy_working_version(page_name):
    """Deploy working version back to live site (copy working → deploy)."""
    try:
        # Working file path
        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
        
        if not working_file.exists():
            return f"❌ No working version found for '{page_name}'"
        
        # Destination file path
        dest_file = DEPLOY_DIR / f"{page_name}.html"
        
        # Copy working version to deploy
        import shutil
        shutil.copy2(working_file, dest_file)
        
        return f"✅ Deployed working version of '{page_name}' to live site: {dest_file}"
        
    except Exception as e:
        return f"❌ Error deploying working version: {str(e)}"

# Page config
st.set_page_config(
    page_title="Simple Web Design Agent",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_available_pages():
    """Get list of available page names for dropdown."""
    pages = []
    try:
        # Get pages from deploy directory
        if DEPLOY_DIR.exists():
            for page_file in DEPLOY_DIR.iterdir():
                if page_file.is_file() and page_file.suffix == ".html":
                    pages.append(page_file.stem)
            
            # Also check pages subdirectory
            pages_subdir = DEPLOY_DIR / "pages"
            if pages_subdir.exists():
                for page_file in pages_subdir.iterdir():
                    if page_file.is_file() and page_file.suffix == ".html":
                        pages.append(f"pages/{page_file.stem}")
        
        return sorted(pages) if pages else ["No pages found"]
    except Exception:
        return ["Error loading pages"]

# Initialize session state
if "agent" not in st.session_state:
    try:
        st.session_state.agent = create_simple_agent()
        st.session_state.messages = []
        
        # Auto-load the main page (index) on startup
        main_page = "index"
        if (DEPLOY_DIR / f"{main_page}.html").exists():
            st.session_state.current_page = main_page
            
            # Create working version automatically
            get_working_version(main_page)
            
            # Load working version content for immediate display
            working_file = WORKING_DIR / f"{main_page}.html"
            if working_file.exists():
                try:
                    with open(working_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        st.session_state.working_page_content = content
                        st.session_state.last_update = str(time.time())

                except Exception as e:
                    st.session_state.working_page_content = None
            else:
                st.session_state.working_page_content = None
        else:
            st.session_state.current_page = None
            
        st.success("✅ Simple agent initialized and main page loaded!")
    except Exception as e:
        st.error(f"❌ Failed to initialize agent: {e}")
        st.stop()

# Sidebar for all controls and chat
with st.sidebar:
    st.header("🎛️ Controls")
    
    # Quick actions with proper agent invocation
    if st.button("📋 List Pages", use_container_width=True):
        with st.spinner("Listing pages..."):
            try:
                # Use the agent's list_directory tool
                response = st.session_state.agent.invoke({
                    "messages": [HumanMessage(content="List all pages in deploy/public directory")]
                })
                result = response['messages'][-1].content if response and 'messages' in response else "No response"
                st.session_state.messages.append(("user", "List pages"))
                st.session_state.messages.append(("assistant", result))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    if st.button("📊 Check Git Status", use_container_width=True):
        with st.spinner("Checking git status..."):
            try:
                from backend.git_utils import ui_check_git_status
                result = ui_check_git_status()
                st.session_state.messages.append(("user", "Check git status"))
                st.session_state.messages.append(("assistant", result))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Commit & Push All", use_container_width=True):
            with st.spinner("Committing and pushing all changes..."):
                try:
                    from backend.git_utils import ui_commit_and_push_all
                    result = ui_commit_and_push_all("Quick commit via UI")
                    st.session_state.messages.append(("user", "Commit and push all changes"))
                    st.session_state.messages.append(("assistant", result))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col2:
        if st.button("📄 Commit Current Page", use_container_width=True):
            current_page = st.session_state.get("current_page")
            if current_page:
                with st.spinner(f"Committing {current_page} page..."):
                    try:
                        from backend.git_utils import ui_commit_current_page
                        result = ui_commit_current_page(current_page, f"Update {current_page} page via UI")
                        st.session_state.messages.append(("user", f"Commit {current_page} page only"))
                        st.session_state.messages.append(("assistant", result))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.error("Select a page first")
    
    st.divider()
    
    # Page Controls
    st.subheader("📝 Page Controls")
    available_pages = get_available_pages()
    
    # Set default to current page or index
    default_index = 0
    if st.session_state.get("current_page") in available_pages:
        default_index = available_pages.index(st.session_state.current_page)
    elif "index" in available_pages:
        default_index = available_pages.index("index")
    
    page_name = st.selectbox(
        "Select Page", 
        available_pages,
        index=default_index,
        help="Choose a page to edit"
    )
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("👁️ View", use_container_width=True):
            if page_name and page_name != "No pages found" and page_name != "Error loading pages":
                st.session_state.current_page = page_name
                
                # Initialize working content - get working version first
                with st.spinner(f"Loading {page_name}..."):
                    try:
                        get_working_version(page_name)
                        
                        # Load working version content
                        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
                        if working_file.exists():
                            with open(working_file, 'r', encoding='utf-8') as f:
                                new_content = f.read()
                                st.session_state.working_page_content = new_content
                                # Force refresh with timestamp
                                st.session_state.last_update = str(time.time())
                        else:
                            st.error(f"Working file not found: {working_file}")
                    except Exception as e:
                        st.error(f"Error loading working version: {e}")
                st.rerun()
    
    with col_b:
        if st.button("📋 Deploy", use_container_width=True):
            if page_name and page_name != "No pages found" and page_name != "Error loading pages":
                with st.spinner(f"Deploying {page_name}..."):
                    try:
                        result = deploy_working_version(page_name)
                        st.session_state.messages.append(("user", f"Deploy {page_name}"))
                        st.session_state.messages.append(("assistant", result))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    st.divider()
    
    # Chat interface in sidebar
    st.subheader("💬 Chat with Agent")
    
    # Show current page context
    if "current_page" in st.session_state and st.session_state.current_page:
        st.info(f"📄 Currently viewing: **{st.session_state.current_page}**")
        st.caption("Agent will edit this page when no specific page is mentioned")
    
    # Display recent chat messages in compact format
    if st.session_state.messages:
        with st.container(height=300):  # Scrollable chat area
            for role, message in st.session_state.messages[-10:]:  # Show last 10 messages
                if role == "user":
                    st.markdown(f"**🧑 You:** {message}")
                else:
                    st.markdown(f"**🤖 Agent:** {message}")
    
    # Chat input
    current_page_hint = ""
    if "current_page" in st.session_state and st.session_state.current_page:
        current_page_hint = f" (will edit {st.session_state.current_page})"
    
    if prompt := st.chat_input(f"Ask the agent to edit pages...{current_page_hint}"):
        # Add context about current page if one is selected
        current_page_context = ""
        if "current_page" in st.session_state and st.session_state.current_page:
            current_page_context = f"\n\nCONTEXT: User is currently viewing page '{st.session_state.current_page}' in the canvas. If they don't specify a page name, assume they mean this page."
        
        # Combine user prompt with context
        full_prompt = prompt + current_page_context
        
        st.session_state.messages.append(("user", prompt))  # Store original for display
        
        with st.spinner("Agent thinking..."):
            try:
                response = st.session_state.agent.invoke({
                    "messages": [HumanMessage(content=full_prompt)]  # Send with context
                })
                
                if response and 'messages' in response:
                    assistant_response = response['messages'][-1].content
                    st.session_state.messages.append(("assistant", assistant_response))
                    
                    # If the agent modified a page, reload the working version immediately
                    if "current_page" in st.session_state and st.session_state.current_page:
                        page_name = st.session_state.current_page
                        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
                        if working_file.exists():
                            try:
                                with open(working_file, 'r', encoding='utf-8') as f:
                                    # Force reload the working version to show changes
                                    new_content = f.read()
                                    st.session_state.working_page_content = new_content
                                    # Add timestamp to force iframe refresh
                                    st.session_state.last_update = str(time.time())
                                    st.session_state.content_hash = hash(new_content)  # Force refresh
                            except Exception as e:
                                st.error(f"Error reloading working content: {e}")
                else:
                    st.session_state.messages.append(("assistant", "I couldn't process that request."))
                
                st.rerun()
            except Exception as e:
                st.session_state.messages.append(("assistant", f"Error: {str(e)}"))
                st.rerun()
    
    st.divider()
    
    # Help section
    st.subheader("📚 Quick Help")
    st.markdown("""
    **Context-Aware Commands:**
    - "Change the background to blue" ← edits current page
    - "Add another 😊" ← edits current page
    - "Make the text larger" ← edits current page
    - Or specify: "Change happy page to green"
    
    **Workflow:**
    1. 👁️ View a page (sets context)
    2. 💬 Chat without specifying page name
    3. 📋 Deploy when ready
    4. 🚀 Choose commit option:
       - **Commit Current Page**: Just this page
       - **Commit & Push All**: All changes
    
    **Git Controls:**
    - 📊 **Check Git Status**: See what's changed
    - 📄 **Commit Current Page**: Deploy just this page
    - 🚀 **Commit & Push All**: Deploy everything
    """)
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main area - Dual page canvas
st.title("🌐 Web Design Agent - Page Editor")

if "current_page" in st.session_state and st.session_state.current_page:
    page_name = st.session_state.current_page
    
    # Determine original page path
    if "/" in page_name:  # pages/index format
        original_page_path = DEPLOY_DIR / f"{page_name}.html"
    else:
        original_page_path = DEPLOY_DIR / f"{page_name}.html"
    
    if original_page_path.exists():
        # Load original content from deploy directory
        with open(original_page_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Load working content if available, otherwise use original
        working_file = WORKING_DIR / f"{page_name.replace('/', '_')}.html"
        working_content = original_content  # Default fallback
        
        if working_file.exists():
            with open(working_file, 'r', encoding='utf-8') as f:
                working_content = f.read()
        
        # Use session state working content if available (for real-time updates)
        session_working_content = st.session_state.get("working_page_content")
        if session_working_content:
            working_content = session_working_content
        
        # Two large columns for page display - equal width
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader(f"📄 Original: {page_name}")
            # Display original page in large iframe
            components.html(original_content, height=900, scrolling=True)
        
        with col_right:
            st.subheader(f"✏️ Working Version: {page_name}")
            

            # Display working version in large iframe
            if working_content:
                # Simple approach - just display the content with a unique comment at the end
                timestamp = st.session_state.get('last_update', str(time.time()))
                # Add comment at the END to avoid breaking HTML structure
                display_content = working_content + f"\n<!-- Last updated: {timestamp} -->"
                components.html(display_content, height=900, scrolling=True)
            else:
                st.warning("❌ No working content loaded!")
                st.info("Try clicking 'Force Reload Working Version' in the debug section above.")
    else:
        st.error(f"❌ Page '{page_name}' not found")
else:
    # Welcome screen when no page is selected
    available_pages = get_available_pages()
    st.markdown(f"""
    ## 👋 Welcome to the Web Design Agent!
    
    ### 🚀 **Simple Workflow:**
    
    1. **📄 Select a page** from the dropdown in the sidebar
    2. **👁️ Click "View"** to see the dual-canvas editor
    3. **💬 Chat with the agent** to make changes to your page
    4. **📋 Click "Deploy"** to push working version to live site
    5. **🚀 Click "Commit & Push All"** to save everything to Git
    
    ### 📋 **Features:**
    - **Left Canvas**: Original live page from `deploy/public/`
    - **Right Canvas**: Your working version with edits
    - **Safe Editing**: Changes go to working version first
    - **Live Updates**: Changes appear instantly in working version
    - **Git Integration**: All changes are tracked and deployable
    
    ### 💡 **Example Commands:**
    - *"Change the background color of the happy page to blue"*
    - *"Add a welcome message to the about page"*  
    - *"Make the heading text larger on lawyer-now"*
    - *"Update the title of the index page"*
    
    ### 📄 **Available Pages:**
    {', '.join(available_pages)}
    
    **👈 Start by selecting a page from the dropdown in the sidebar!**
    """)

# Custom CSS for better layout
st.markdown("""
<style>
.stButton > button {
    width: 100%;
    margin: 2px 0;
}

/* Make sidebar wider */
.css-1d391kg {
    width: 350px;
}

/* Adjust main content margin */
.css-18e3th9 {
    padding-left: 1rem;
}

/* Style the iframe containers */
[data-testid="stIFrame"] {
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True) 