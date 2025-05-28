#!/usr/bin/env python3
"""
WordPress Agent Streamlit UI v3 - Live Site Preview
A visual editor that shows the actual WordPress site with AI-powered editing
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
import requests
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import the agent components
from backend.main import create_wordpress_memory_agent
from backend.wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page configuration
st.set_page_config(
    page_title="WordPress Visual Editor",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for the visual editor
st.markdown("""
<style>
    /* Remove default padding */
    .stApp {
        background-color: #f5f5f5;
    }
    
    /* Main content area */
    .main-content {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: calc(100vh - 100px);
        overflow: hidden;
    }
    
    /* Navigation bar */
    .nav-bar {
        background-color: #23282d;
        color: white;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    
    /* Chat sidebar */
    .chat-container {
        height: calc(100vh - 120px);
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
    }
    
    .chat-input-area {
        padding: 20px;
        border-top: 1px solid #ddd;
    }
    
    /* Chat messages */
    .user-message {
        background-color: #0073aa;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 80%;
        margin-left: 20%;
    }
    
    .assistant-message {
        background-color: #f0f0f0;
        color: #333;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 80%;
    }
    
    /* Loading indicator */
    .loading-indicator {
        text-align: center;
        padding: 20px;
        color: #666;
    }
    
    /* Page info */
    .page-info {
        background-color: #f0f0f0;
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-size: 0.9em;
    }
    
    /* Hide streamlit elements */
    .stDeployButton {
        display: none;
    }
    
    footer {
        display: none;
    }
    
    /* Responsive iframe */
    .responsive-iframe {
        width: 100%;
        height: calc(100vh - 180px);
        border: none;
        border-radius: 0 0 8px 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
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
    st.session_state.current_page_type = "home"  # home, page, post

if "pages_list" not in st.session_state:
    st.session_state.pages_list = []

if "posts_list" not in st.session_state:
    st.session_state.posts_list = []

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
    except:
        pass

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
        
        # Add navigation message to chat
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Navigated to {page_type}: {page_data['title']}",
            "timestamp": datetime.now().strftime("%I:%M %p")
        })

def render_site_preview():
    """Render the WordPress site in an iframe"""
    if st.session_state.current_page_url:
        # Create a responsive iframe
        iframe_html = f"""
        <iframe 
            src="{st.session_state.current_page_url}"
            class="responsive-iframe"
            id="wordpress-preview"
            onload="window.parent.postMessage({{type: 'iframe-loaded', url: this.contentWindow.location.href}}, '*')"
        ></iframe>
        """
        components.html(iframe_html, height=700)
    else:
        st.info("No WordPress site connected. Please check your configuration.")

def render_navigation_bar():
    """Render the navigation bar above the site preview"""
    col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
    
    with col1:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_page_url = st.session_state.wp_api.base_url
            st.session_state.current_page_id = None
            st.session_state.current_page_type = "home"
            st.rerun()
    
    with col2:
        # Page selector
        if st.session_state.pages_list:
            page_options = ["Select a page..."] + [
                f"{p.get('title', {}).get('rendered', 'Untitled')} (ID: {p['id']})" 
                for p in st.session_state.pages_list
            ]
            selected_page = st.selectbox(
                "Navigate to:",
                page_options,
                key="page_selector",
                label_visibility="collapsed"
            )
            
            if selected_page != "Select a page...":
                # Extract ID from selection
                page_id = int(selected_page.split("ID: ")[1].rstrip(")"))
                navigate_to_page(page_id, "page")
                st.rerun()
    
    with col3:
        # Current page info
        if st.session_state.current_page_id:
            st.info(f"📄 Page ID: {st.session_state.current_page_id}")
        else:
            st.info("🏠 Homepage")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

def render_chat_sidebar():
    """Render the persistent chat interface"""
    st.markdown("### 🤖 WordPress AI Assistant")
    
    # Current page context
    if st.session_state.current_page_id:
        st.markdown(f"""
        <div class="page-info">
        <strong>Current Page:</strong> ID {st.session_state.current_page_id}<br>
        <strong>Type:</strong> {st.session_state.current_page_type.title()}
        </div>
        """, unsafe_allow_html=True)
    
    # Chat messages container
    chat_container = st.container(height=500)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(message["timestamp"])
    
    # Chat input
    if prompt := st.chat_input("Describe what you want to change..."):
        # Add context about current page
        context_prompt = prompt
        if st.session_state.current_page_id:
            context_prompt = f"[User is viewing {st.session_state.current_page_type} ID {st.session_state.current_page_id}] {prompt}"
        
        # Add user message
        timestamp = datetime.now().strftime("%I:%M %p")
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })
        
        # Process with agent
        try:
            config = {
                "configurable": {
                    "thread_id": st.session_state.session_id,
                    "user_id": "streamlit_user"
                }
            }
            
            # Get response from agent
            response = st.session_state.agent.invoke(
                {"messages": [HumanMessage(content=context_prompt)]},
                config=config
            )
            
            # Extract the response
            if response and "messages" in response:
                ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
                if ai_messages:
                    ai_response = ai_messages[-1].content
                    
                    # Add assistant message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response,
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
            
            # Refresh the page if content was updated
            if "updated" in ai_response.lower() or "changed" in ai_response.lower():
                time.sleep(1)  # Give WordPress time to process
                st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Quick actions
    with st.expander("Quick Actions", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 New Post", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Create a new blog post",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
        
        with col2:
            if st.button("📄 New Page", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Create a new page",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Main app
def main():
    """Main application entry point"""
    # Fetch site structure on first load
    if not st.session_state.pages_list and not st.session_state.posts_list:
        fetch_site_structure()
    
    # Create layout
    col1, col2 = st.columns([3, 1])  # Site preview: 3/4, Chat: 1/4
    
    # Site preview area
    with col1:
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        # Navigation bar
        render_navigation_bar()
        
        # Site preview
        render_site_preview()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat sidebar
    with col2:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        render_chat_sidebar()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Instructions for first-time users
    if len(st.session_state.messages) == 0:
        with col2:
            st.info("""
            👋 **Welcome to WordPress Visual Editor!**
            
            You can:
            - Navigate to any page using the dropdown
            - Ask me to change anything you see
            - Create new pages or posts
            - Upload content and iterate on designs
            
            Try: "Change the background color to blue" or "Add a new section with contact information"
            """)

if __name__ == "__main__":
    main()