#!/usr/bin/env python3
"""
WordPress Visual Editor - Live Site Preview with Natural Language Editing
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import asyncio
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
import uuid
from dotenv import load_dotenv
import time
import base64

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import the agent components
from backend.main import create_wordpress_memory_agent
from backend.wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page configuration - MUST BE FIRST
st.set_page_config(
    page_title="WordPress Visual Editor",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    with st.spinner("Initializing WordPress Agent..."):
        agent, memory_manager = create_wordpress_memory_agent(use_sqlite=True)
        st.session_state.agent = agent
        st.session_state.memory_manager = memory_manager

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "wp_api" not in st.session_state:
    try:
        st.session_state.wp_api = WordPressAPI()
    except Exception as e:
        st.error(f"Failed to initialize WordPress API: {e}")
        st.session_state.wp_api = None

if "current_page_url" not in st.session_state:
    if st.session_state.wp_api:
        st.session_state.current_page_url = st.session_state.wp_api.base_url
    else:
        st.session_state.current_page_url = None

if "current_page_id" not in st.session_state:
    st.session_state.current_page_id = None

if "current_page_type" not in st.session_state:
    st.session_state.current_page_type = "home"

if "pages_list" not in st.session_state:
    st.session_state.pages_list = []

if "posts_list" not in st.session_state:
    st.session_state.posts_list = []

if "needs_refresh" not in st.session_state:
    st.session_state.needs_refresh = False

# Custom CSS for better layout
st.markdown("""
<style>
    /* Main layout improvements */
    .main > div {
        padding-top: 0rem;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    
    /* Site preview styling */
    .site-preview-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
        background: white;
        height: calc(100vh - 200px);
    }
    
    /* Navigation bar styling */
    .nav-container {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    /* Chat styling */
    .chat-container {
        height: calc(100vh - 150px);
        overflow-y: auto;
    }
    
    /* Message styling */
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 85%;
        margin-left: 15%;
    }
    
    .assistant-message {
        background-color: #f1f3f4;
        color: #333;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 85%;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve iframe display */
    iframe {
        width: 100%;
        height: calc(100vh - 250px);
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def fetch_site_structure():
    """Fetch pages and posts for navigation"""
    if not st.session_state.wp_api:
        return
    
    try:
        # Fetch pages
        pages_response = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 100})
        if not pages_response.startswith("Error"):
            st.session_state.pages_list = json.loads(pages_response)
        
        # Fetch posts  
        posts_response = st.session_state.wp_api.request("/wp/v2/posts", params={"per_page": 20, "status": "publish"})
        if not posts_response.startswith("Error"):
            st.session_state.posts_list = json.loads(posts_response)
    except Exception as e:
        st.error(f"Error fetching site structure: {e}")

def get_page_content(page_id: int, page_type: str = "page"):
    """Get the rendered content of a page or post"""
    if not st.session_state.wp_api:
        return None
    
    endpoint = f"/wp/v2/{page_type}s/{page_id}"
    response = st.session_state.wp_api.request(endpoint)
    
    if not response.startswith("Error"):
        data = json.loads(response)
        return {
            "title": data.get("title", {}).get("rendered", ""),
            "content": data.get("content", {}).get("rendered", ""),
            "link": data.get("link", ""),
            "id": data.get("id"),
            "type": page_type
        }
    return None

def navigate_to_page(page_id: int, page_type: str = "page"):
    """Navigate to a specific page or post"""
    page_data = get_page_content(page_id, page_type)
    if page_data:
        st.session_state.current_page_url = page_data["link"]
        st.session_state.current_page_id = page_id
        st.session_state.current_page_type = page_type
        return page_data["title"]
    return None

def process_navigation_command(command: str):
    """Process natural language navigation commands"""
    command_lower = command.lower()
    
    # Check for home navigation
    if "home" in command_lower or "main page" in command_lower or "homepage" in command_lower:
        st.session_state.current_page_url = st.session_state.wp_api.base_url
        st.session_state.current_page_id = None
        st.session_state.current_page_type = "home"
        return "Navigated to homepage"
    
    # Check for page navigation
    for page in st.session_state.pages_list:
        page_title = page.get("title", {}).get("rendered", "").lower()
        if page_title in command_lower or str(page["id"]) in command:
            title = navigate_to_page(page["id"], "page")
            return f"Navigated to page: {title}"
    
    # Check for post navigation
    for post in st.session_state.posts_list:
        post_title = post.get("title", {}).get("rendered", "").lower()
        if post_title in command_lower:
            title = navigate_to_page(post["id"], "post")
            return f"Navigated to post: {title}"
    
    return None

def render_site_preview():
    """Render the WordPress site preview"""
    if st.session_state.current_page_url:
        # Create HTML that includes the WordPress site
        iframe_html = f"""
        <div class="site-preview-container">
            <iframe 
                src="{st.session_state.current_page_url}" 
                id="wp-preview"
                frameborder="0"
                width="100%"
                height="100%"
                style="width: 100%; height: calc(100vh - 250px);"
            ></iframe>
        </div>
        """
        
        # Use components.html to render the iframe
        components.html(iframe_html, height=700)
    else:
        st.info("🌐 No WordPress site connected. Please check your wp-sites.json configuration.")

def main():
    """Main application"""
    # Fetch site structure on first load
    if not st.session_state.pages_list and not st.session_state.posts_list:
        fetch_site_structure()
    
    # Layout: Main content (3/4) and Chat sidebar (1/4)
    col1, col2 = st.columns([3, 1])
    
    # Main content area - Site preview
    with col1:
        # Navigation controls
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 3, 1, 1])
        
        with nav_col1:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.current_page_url = st.session_state.wp_api.base_url
                st.session_state.current_page_id = None
                st.session_state.current_page_type = "home"
                st.rerun()
        
        with nav_col2:
            if st.session_state.pages_list:
                page_options = ["Select a page..."] + [
                    f"{p.get('title', {}).get('rendered', 'Untitled')}" 
                    for p in st.session_state.pages_list
                ]
                selected_idx = st.selectbox(
                    "Navigate to page:",
                    range(len(page_options)),
                    format_func=lambda x: page_options[x],
                    key="page_nav"
                )
                
                if selected_idx > 0:
                    selected_page = st.session_state.pages_list[selected_idx - 1]
                    navigate_to_page(selected_page['id'], "page")
                    st.rerun()
        
        with nav_col3:
            if st.session_state.current_page_id:
                st.info(f"📄 ID: {st.session_state.current_page_id}")
            else:
                st.info("🏠 Homepage")
        
        with nav_col4:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Site preview
        st.markdown("---")
        render_site_preview()
    
    # Chat sidebar
    with col2:
        st.markdown("### 🤖 WordPress AI Assistant")
        
        # Connection status
        if st.session_state.wp_api:
            st.success("✅ Connected")
        else:
            st.error("❌ Not connected")
        
        # Current page info
        if st.session_state.current_page_id:
            st.info(f"Viewing: Page ID {st.session_state.current_page_id}")
        
        # Chat messages display
        chat_container = st.container(height=400)
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Chat input
        user_input = st.chat_input("Describe what you want to do...")
        
        if user_input:
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            
            # Check for navigation commands first
            nav_result = process_navigation_command(user_input)
            if nav_result:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": nav_result,
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
            else:
                # Process with agent
                with st.spinner("Processing..."):
                    try:
                        # Add context about current page
                        context_prompt = user_input
                        if st.session_state.current_page_id:
                            context_prompt = f"[User is viewing {st.session_state.current_page_type} ID {st.session_state.current_page_id}] {user_input}"
                        
                        # Configure agent
                        config = {
                            "configurable": {
                                "thread_id": st.session_state.session_id,
                                "user_id": "streamlit_user"
                            }
                        }
                        
                        # Get response
                        response = st.session_state.agent.invoke(
                            {"messages": [HumanMessage(content=context_prompt)]},
                            config=config
                        )
                        
                        # Extract AI response
                        if response and "messages" in response:
                            ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
                            if ai_messages:
                                ai_response = ai_messages[-1].content
                                
                                # Add to messages
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": ai_response,
                                    "timestamp": datetime.now().strftime("%I:%M %p")
                                })
                                
                                # Check if we need to refresh
                                if any(word in ai_response.lower() for word in ["updated", "changed", "added", "created", "modified"]):
                                    st.session_state.needs_refresh = True
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Quick actions
        with st.expander("⚡ Quick Actions", expanded=False):
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("📝 New Post", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "Create a new blog post",
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
                    st.rerun()
                
                if st.button("📄 New Page", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "Create a new blank page",
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
                    st.rerun()
            
            with col_b:
                if st.button("🖼️ Upload", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "I want to upload media files",
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
                    st.rerun()
                
                if st.button("🗑️ Clear Chat", use_container_width=True):
                    st.session_state.messages = []
                    st.rerun()
        
        # File uploader (hidden by default)
        uploaded_file = st.file_uploader(
            "Upload files",
            type=['png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'],
            key="file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            st.info(f"File ready: {uploaded_file.name}")
            if st.button("Process Upload"):
                # Handle file upload through agent
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"Upload this file: {uploaded_file.name}",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()

if __name__ == "__main__":
    main()