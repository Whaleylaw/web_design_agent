#!/usr/bin/env python3
"""
Simple Streamlit Interface for Web Design Agent
Just: Edit Files → Git Push → Netlify Deploy
"""

import streamlit as st
import sys
import os
from pathlib import Path
import streamlit.components.v1 as components

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.simple_agent import create_simple_agent
from langchain_core.messages import HumanMessage, AIMessage

# Page config
st.set_page_config(
    page_title="Simple Web Design Agent",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "agent" not in st.session_state:
    try:
        st.session_state.agent = create_simple_agent()
        st.session_state.messages = []
        st.success("✅ Simple agent initialized!")
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
                from backend.simple_agent import list_pages
                result = list_pages.invoke({})
                st.session_state.messages.append(("user", "List pages"))
                st.session_state.messages.append(("assistant", result))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    if st.button("📊 Check Git Status", use_container_width=True):
        with st.spinner("Checking git status..."):
            try:
                from backend.simple_agent import check_git_status
                result = check_git_status.invoke({})
                st.session_state.messages.append(("user", "Check git status"))
                st.session_state.messages.append(("assistant", result))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    if st.button("🚀 Commit & Push All", use_container_width=True):
        with st.spinner("Committing and pushing..."):
            try:
                from backend.simple_agent import git_commit_and_push
                result = git_commit_and_push.invoke({"message": "Quick commit via UI"})
                st.session_state.messages.append(("user", "Commit and push changes"))
                st.session_state.messages.append(("assistant", result))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.divider()
    
    # Page Controls
    st.subheader("📝 Page Controls")
    page_id = st.text_input("Page ID", value="1", help="Enter page ID: 1, 6, 13, 16, 21, or 53")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("👁️ View", use_container_width=True):
            st.session_state.current_page = page_id
            # Initialize working content as copy of original
            page_path = f"wordpress_clone/pages/page_{page_id}/index.html"
            if Path(page_path).exists():
                with open(page_path, 'r', encoding='utf-8') as f:
                    st.session_state.working_page_content = f.read()
            st.rerun()
    
    with col_b:
        if st.button("📋 Deploy", use_container_width=True):
            with st.spinner(f"Copying page {page_id}..."):
                try:
                    from backend.simple_agent import copy_to_deploy
                    result = copy_to_deploy.invoke({"page_id": page_id})
                    st.session_state.messages.append(("user", f"Copy page {page_id} to deploy"))
                    st.session_state.messages.append(("assistant", result))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.divider()
    
    # Chat interface in sidebar
    st.subheader("💬 Chat with Agent")
    
    # Display recent chat messages in compact format
    if st.session_state.messages:
        with st.container(height=300):  # Scrollable chat area
            for role, message in st.session_state.messages[-10:]:  # Show last 10 messages
                if role == "user":
                    st.markdown(f"**🧑 You:** {message}")
                else:
                    st.markdown(f"**🤖 Agent:** {message}")
    
    # Chat input
    if prompt := st.chat_input("Ask the agent to edit pages..."):
        st.session_state.messages.append(("user", prompt))
        
        with st.spinner("Agent thinking..."):
            try:
                response = st.session_state.agent.invoke({
                    "messages": [HumanMessage(content=prompt)]
                })
                
                if response and 'messages' in response:
                    assistant_response = response['messages'][-1].content
                    st.session_state.messages.append(("assistant", assistant_response))
                    
                    # If the agent modified a page, reload the working version
                    if "current_page" in st.session_state:
                        current_page_path = f"wordpress_clone/pages/page_{st.session_state.current_page}/index.html"
                        if Path(current_page_path).exists():
                            with open(current_page_path, 'r', encoding='utf-8') as f:
                                st.session_state.working_page_content = f.read()
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
    **Simple Commands:**
    - "Change the background to blue"
    - "Add a header saying Welcome"
    - "Make the text larger"
    - "Change the title"
    
    **Workflow:**
    1. 👁️ View a page
    2. 💬 Chat to make changes  
    3. 📋 Deploy when ready
    4. 🚀 Commit & push to save
    """)
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main area - Dual page canvas
st.title("🌐 Web Design Agent - Page Editor")

if "current_page" in st.session_state and st.session_state.current_page:
    page_path = f"wordpress_clone/pages/page_{st.session_state.current_page}/index.html"
    
    if Path(page_path).exists():
        # Load original content
        with open(page_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Use working content if available, otherwise use original
        working_content = st.session_state.get("working_page_content", original_content)
        
        # Two large columns for page display - equal width
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader(f"📄 Original Page {st.session_state.current_page}")
            # Display original page in large iframe
            components.html(original_content, height=900, scrolling=True)
        
        with col_right:
            st.subheader(f"✏️ Working Version Page {st.session_state.current_page}")
            # Display working version in large iframe
            components.html(working_content, height=900, scrolling=True)
    else:
        st.error(f"❌ Page {st.session_state.current_page} not found at {page_path}")
        st.info("Available pages: 1, 6, 13, 16, 21, 53")
else:
    # Welcome screen when no page is selected
    st.markdown("""
    ## 👋 Welcome to the Web Design Agent!
    
    ### 🚀 **Simple Workflow:**
    
    1. **📄 Select a page** in the sidebar (1, 6, 13, 16, 21, or 53)
    2. **👁️ Click "View"** to see the dual-canvas editor
    3. **💬 Chat with the agent** to make changes to your page
    4. **📋 Click "Deploy"** when ready to push to Netlify
    5. **🚀 Click "Commit & Push All"** to save everything to Git
    
    ### 📋 **Features:**
    - **Left Canvas**: Original page version
    - **Right Canvas**: Your working version with edits
    - **Live Updates**: Changes appear instantly in the working version
    - **Git Integration**: All changes are tracked and deployable
    
    ### 💡 **Example Commands:**
    - *"Change the background color to blue"*
    - *"Add a welcome message at the top"*  
    - *"Make the heading text larger"*
    - *"Change the page title to 'My Website'"*
    
    **👈 Start by selecting a page ID in the sidebar!**
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