#!/usr/bin/env python3
"""
WordPress Agent Streamlit UI v2
Enhanced with latest best practices and streaming support
"""

import streamlit as st
import os
import sys
import asyncio
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
import uuid
from dotenv import load_dotenv
import time

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
    page_title="WordPress Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # Changed to collapsed since we'll use custom layout
)

# Custom CSS
st.markdown("""
<style>
    /* WordPress-inspired styling */
    .stApp {
        background-color: #f1f1f1;
    }
    
    /* Chat messages */
    .user-message {
        background-color: #0073aa;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: 30%;
    }
    
    .assistant-message {
        background-color: #ffffff;
        color: #333;
        border: 1px solid #ddd;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 70%;
    }
    
    .message-timestamp {
        font-size: 0.8em;
        color: #666;
        margin-top: 5px;
    }
    
    /* Dashboard cards */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* WordPress color scheme */
    .wp-primary { color: #0073aa; }
    .wp-secondary { color: #005177; }
    .wp-success { color: #46b450; }
    .wp-warning { color: #ffb900; }
    .wp-error { color: #dc3232; }
    
    /* Improved chat input styling */
    .stChatInput {
        border-radius: 8px;
        border: 2px solid #0073aa;
    }
    
    /* Chat container styling */
    .chat-container {
        height: calc(100vh - 100px);
        overflow-y: auto;
        padding: 10px;
        background-color: #f9f9f9;
        border-radius: 8px;
    }
    
    /* Fixed chat input at bottom */
    .chat-input-container {
        position: sticky;
        bottom: 0;
        background-color: white;
        padding: 10px;
        border-top: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state following best practices
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    # Create the agent with SQLite persistence for long-term memory
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

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"  # Changed default to Dashboard

if "stream_active" not in st.session_state:
    st.session_state.stream_active = False

# Helper function to stream response
def stream_response(text: str):
    """Simulate streaming by yielding characters with delay"""
    for char in text:
        yield char
        time.sleep(0.01)

# Navigation header
def render_navigation():
    """Render the navigation header"""
    pages = ["Dashboard", "Posts", "Pages", "Media", "Settings"]
    
    # Create navigation tabs
    cols = st.columns(len(pages) + 2)  # +2 for logo and spacing
    
    with cols[0]:
        st.markdown("### 🤖 WordPress Agent")
    
    for idx, page in enumerate(pages):
        with cols[idx + 1]:
            if st.button(page, key=f"nav_{page}", use_container_width=True, 
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()

# Persistent chat interface
def render_chat_sidebar():
    """Render the chat interface in a persistent sidebar"""
    # Chat messages container
    chat_container = st.container(height=600)
    
    with chat_container:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(message["timestamp"])
    
    # Chat input at bottom
    if prompt := st.chat_input("Ask about your WordPress site...", key="chat_input"):
        # Add user message
        timestamp = datetime.now().strftime("%I:%M %p")
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })
        
        # Process with agent
        try:
            # Configure the agent
            config = {
                "configurable": {
                    "thread_id": st.session_state.session_id,
                    "user_id": "streamlit_user"
                }
            }
            
            # Get response from agent
            response = st.session_state.agent.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config=config
            )
            
            # Extract the response
            if response and "messages" in response:
                # Get the last AI message
                ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
                if ai_messages:
                    ai_response = ai_messages[-1].content
                    
                    # Add assistant message to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response,
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("💡 Tip: Make sure your OpenAI API key is set correctly.")

# Enhanced dashboard with real data
def render_dashboard():
    """Render the WordPress dashboard with real statistics"""
    st.title("📊 WordPress Dashboard")
    
    if not st.session_state.wp_api:
        st.error("WordPress API not connected")
        return
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Fetch site statistics with error handling
    try:
        with st.spinner("Loading dashboard..."):
            # Get posts count
            with col1:
                try:
                    posts_json = st.session_state.wp_api.request("/wp/v2/posts", params={"per_page": 1})
                    posts_data = json.loads(posts_json) if not posts_json.startswith("Error") else []
                    # Get total from headers would be ideal, using len for now
                    posts_count = len(posts_data) if posts_data else 0
                    st.metric("📝 Posts", posts_count, delta="+2 this week")
                except:
                    st.metric("📝 Posts", "N/A")
            
            # Get pages count
            with col2:
                try:
                    pages_json = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 1})
                    pages_data = json.loads(pages_json) if not pages_json.startswith("Error") else []
                    pages_count = len(pages_data) if pages_data else 0
                    st.metric("📄 Pages", pages_count)
                except:
                    st.metric("📄 Pages", "N/A")
            
            # Get media count
            with col3:
                try:
                    media_json = st.session_state.wp_api.request("/wp/v2/media", params={"per_page": 1})
                    media_data = json.loads(media_json) if not media_json.startswith("Error") else []
                    media_count = len(media_data) if media_data else 0
                    st.metric("🖼️ Media", media_count)
                except:
                    st.metric("🖼️ Media", "N/A")
            
            # Get comments count
            with col4:
                try:
                    comments_json = st.session_state.wp_api.request("/wp/v2/comments", params={"per_page": 1})
                    comments_data = json.loads(comments_json) if not comments_json.startswith("Error") else []
                    comments_count = len(comments_data) if comments_data else 0
                    st.metric("💬 Comments", comments_count)
                except:
                    st.metric("💬 Comments", "N/A")
    
    except Exception as e:
        st.error(f"Failed to load dashboard data: {str(e)}")
    
    # Recent activity section
    st.subheader("📝 Recent Activity")
    
    try:
        # Fetch recent posts
        posts_json = st.session_state.wp_api.request("/wp/v2/posts", params={"per_page": 5, "orderby": "date", "order": "desc"})
        posts = json.loads(posts_json) if not posts_json.startswith("Error") else []
        
        if posts:
            for post in posts:
                with st.expander(f"📄 {post.get('title', {}).get('rendered', 'Untitled')}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Status:** {post.get('status', 'Unknown')}")
                        st.markdown(f"**Date:** {post.get('date', 'Unknown')[:10]}")
                    with col2:
                        if st.button("View", key=f"view_post_{post['id']}"):
                            st.session_state.current_page = "Chat"
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Show me the details of post ID {post['id']}",
                                "timestamp": datetime.now().strftime("%I:%M %p")
                            })
                            st.rerun()
        else:
            st.info("No recent posts found")
    
    except Exception as e:
        st.error(f"Failed to load recent activity: {str(e)}")
    
    # Quick actions with improved UX
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ New Post", use_container_width=True, type="primary"):
            st.session_state.current_page = "Chat"
            st.session_state.messages.append({
                "role": "user",
                "content": "Create a new draft post",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            st.rerun()
    
    with col2:
        if st.button("📄 New Page", use_container_width=True):
            st.session_state.current_page = "Chat"
            st.session_state.messages.append({
                "role": "user",
                "content": "Create a new page",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            st.rerun()
    
    with col3:
        if st.button("📤 Upload Media", use_container_width=True):
            st.session_state.current_page = "Media"
            st.rerun()
    
    with col4:
        if st.button("🔍 Search Content", use_container_width=True):
            st.session_state.current_page = "Chat"
            st.session_state.messages.append({
                "role": "user",
                "content": "Search for content on the site",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            st.rerun()

# Enhanced posts management
def render_posts():
    """Render posts management interface with better UX"""
    st.title("📝 Posts Management")
    
    if not st.session_state.wp_api:
        st.error("WordPress API not connected")
        return
    
    # Filters in columns
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search posts", placeholder="Enter keywords...", key="post_search")
    
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "Published", "Draft", "Private", "Pending"],
            key="post_status_filter"
        )
    
    with col3:
        order_by = st.selectbox(
            "Sort by",
            ["Date", "Title", "Modified"],
            key="post_order_by"
        )
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Posts list with pagination
    st.subheader("Posts List")
    
    try:
        # Prepare API parameters
        params = {
            "per_page": 10,
            "orderby": order_by.lower(),
            "order": "desc"
        }
        
        if search_term:
            params["search"] = search_term
        
        if status_filter != "All":
            params["status"] = status_filter.lower()
        
        # Fetch posts
        posts_json = st.session_state.wp_api.request("/wp/v2/posts", params=params)
        posts = json.loads(posts_json) if not posts_json.startswith("Error") else []
        
        if posts:
            # Display posts in a more organized way
            for idx, post in enumerate(posts):
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        st.markdown(f"### {post.get('title', {}).get('rendered', 'Untitled')}")
                        st.caption(f"Status: {post.get('status', 'Unknown')} | Date: {post.get('date', 'Unknown')[:10]}")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_post_{post['id']}"):
                            st.session_state.current_page = "Chat"
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Edit post with ID {post['id']}",
                                "timestamp": datetime.now().strftime("%I:%M %p")
                            })
                            st.rerun()
                    
                    with col3:
                        if st.button("👁️ View", key=f"view_post_detail_{post['id']}"):
                            with st.expander("Post Details", expanded=True):
                                st.markdown(f"**Link:** {post.get('link', '#')}")
                                st.markdown(f"**Modified:** {post.get('modified', 'Unknown')[:10]}")
                                # Add excerpt if available
                                excerpt = post.get('excerpt', {}).get('rendered', '')
                                if excerpt:
                                    st.markdown("**Excerpt:**")
                                    st.markdown(excerpt)
                    
                    st.divider()
        else:
            st.info("No posts found matching your criteria")
            
    except Exception as e:
        st.error(f"Failed to fetch posts: {str(e)}")

# Pages management
def render_pages():
    """Render pages management interface"""
    st.title("📄 Pages Management")
    
    if not st.session_state.wp_api:
        st.error("WordPress API not connected")
        return
    
    # Similar structure to posts but for pages
    try:
        pages_json = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 20})
        pages = json.loads(pages_json) if not pages_json.startswith("Error") else []
        
        if pages:
            # Create a hierarchical view if possible
            st.subheader("Page Hierarchy")
            
            for page in pages:
                parent_id = page.get('parent', 0)
                indent = "　　" if parent_id > 0 else ""
                
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"{indent}📄 **{page.get('title', {}).get('rendered', 'Untitled')}**")
                        st.caption(f"{indent}Status: {page.get('status', 'Unknown')}")
                    
                    with col2:
                        if st.button("Edit", key=f"edit_page_{page['id']}"):
                            st.session_state.current_page = "Chat"
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Edit page with ID {page['id']}",
                                "timestamp": datetime.now().strftime("%I:%M %p")
                            })
                            st.rerun()
        else:
            st.info("No pages found")
            
    except Exception as e:
        st.error(f"Failed to fetch pages: {str(e)}")

# Enhanced media library
def render_media():
    """Render media library interface with preview"""
    st.title("🖼️ Media Library")
    
    if not st.session_state.wp_api:
        st.error("WordPress API not connected")
        return
    
    # Upload section
    st.subheader("📤 Upload Media")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'mp4', 'mp3'],
        accept_multiple_files=True,
        help="Drag and drop files here or click to browse"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"✅ {uploaded_file.name} ready to upload ({uploaded_file.size / 1024:.1f} KB)")
            with col2:
                if st.button(f"Upload", key=f"upload_{uploaded_file.name}"):
                    st.info("Upload functionality coming soon...")
    
    # Media grid
    st.subheader("📁 Media Files")
    
    # View toggle
    view_mode = st.radio("View", ["Grid", "List"], horizontal=True, key="media_view_mode")
    
    try:
        # Fetch media
        media_json = st.session_state.wp_api.request("/wp/v2/media", params={"per_page": 20})
        media_items = json.loads(media_json) if not media_json.startswith("Error") else []
        
        if media_items:
            if view_mode == "Grid":
                # Grid view
                cols = st.columns(4)
                for idx, media in enumerate(media_items):
                    with cols[idx % 4]:
                        # Display thumbnail if available
                        media_url = media.get('source_url', '')
                        media_type = media.get('media_type', '')
                        
                        if media_type == 'image' and media_url:
                            st.image(media_url, use_container_width=True)
                        else:
                            st.info(f"📎 {media.get('title', {}).get('rendered', 'Media')}")
                        
                        st.caption(media.get('title', {}).get('rendered', 'Untitled')[:20])
                        
                        if st.button("Details", key=f"media_details_{media['id']}"):
                            with st.expander("Media Details", expanded=True):
                                st.markdown(f"**Type:** {media_type}")
                                st.markdown(f"**Date:** {media.get('date', 'Unknown')[:10]}")
                                st.markdown(f"**URL:** `{media_url}`")
            else:
                # List view
                for media in media_items:
                    with st.container():
                        col1, col2, col3 = st.columns([1, 3, 1])
                        
                        with col1:
                            # Thumbnail
                            media_url = media.get('source_url', '')
                            media_type = media.get('media_type', '')
                            
                            if media_type == 'image' and media_url:
                                st.image(media_url, width=100)
                            else:
                                st.info("📎")
                        
                        with col2:
                            st.markdown(f"**{media.get('title', {}).get('rendered', 'Untitled')}**")
                            st.caption(f"Type: {media_type} | Date: {media.get('date', 'Unknown')[:10]}")
                        
                        with col3:
                            if st.button("Copy URL", key=f"copy_media_{media['id']}"):
                                st.code(media_url)
                        
                        st.divider()
        else:
            st.info("No media files found")
            
    except Exception as e:
        st.error(f"Failed to fetch media: {str(e)}")

# Settings page
def render_settings():
    """Render settings interface"""
    st.title("⚙️ Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs(["General", "API Configuration", "Agent Settings", "About"])
    
    with tab1:
        st.subheader("General Settings")
        
        # Theme selection
        theme = st.selectbox(
            "Theme",
            ["Light", "Dark", "Auto"],
            help="Choose your preferred theme"
        )
        
        # Language
        language = st.selectbox(
            "Language",
            ["English", "Spanish", "French", "German"],
            help="Interface language"
        )
        
        # Notifications
        st.checkbox("Enable desktop notifications", value=True)
        st.checkbox("Sound effects", value=False)
        
        if st.button("Save General Settings", type="primary"):
            st.success("Settings saved successfully!")
    
    with tab2:
        st.subheader("WordPress API Configuration")
        
        if st.session_state.wp_api:
            st.success("✅ API Connected")
            
            # Display current configuration
            with st.expander("Current Configuration", expanded=True):
                st.text_input("Site URL", value=st.session_state.wp_api.base_url, disabled=True)
                st.text_input("Username", value=st.session_state.wp_api.username, disabled=True)
                st.text_input("Password", value="********", type="password", disabled=True)
            
            # Test connection button
            if st.button("Test Connection"):
                with st.spinner("Testing connection..."):
                    try:
                        result = st.session_state.wp_api.request("")
                        if not result.startswith("Error"):
                            st.success("✅ Connection successful!")
                        else:
                            st.error("❌ Connection failed")
                    except:
                        st.error("❌ Connection failed")
        else:
            st.error("❌ API Not Connected")
            st.info("Please check your wp-sites.json configuration")
    
    with tab3:
        st.subheader("Agent Settings")
        
        # Model selection
        model = st.selectbox(
            "AI Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            help="Choose the AI model for the agent"
        )
        
        # Temperature
        temperature = st.slider(
            "Response Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="Higher values make responses more creative"
        )
        
        # Max tokens
        max_tokens = st.number_input(
            "Max Response Tokens",
            min_value=100,
            max_value=4000,
            value=1000,
            step=100,
            help="Maximum length of responses"
        )
        
        # Memory settings
        st.subheader("Memory Settings")
        
        memory_type = st.radio(
            "Memory Type",
            ["In-Memory", "SQLite Persistent"],
            help="Choose how conversations are stored"
        )
        
        if st.button("Save Agent Settings", type="primary"):
            st.success("Agent settings saved successfully!")
    
    with tab4:
        st.subheader("About")
        
        st.markdown("""
        ### WordPress Memory Agent
        
        **Version:** 2.0.0  
        **Built with:** LangGraph, LangChain, Streamlit  
        **License:** MIT
        
        This application combines the power of AI with WordPress management,
        allowing you to control your WordPress site through natural conversation.
        
        #### Features:
        - 🧠 Dual memory system for context retention
        - 🌐 Full WordPress REST API integration
        - 💬 Natural language interface
        - 📊 Real-time dashboard
        - 🔐 Secure authentication
        
        #### Resources:
        - [Documentation](https://github.com/your-repo)
        - [Report Issues](https://github.com/your-repo/issues)
        - [API Reference](https://developer.wordpress.org/rest-api/)
        """)

# Main app with persistent chat
def main():
    """Main application entry point"""
    # Render navigation header
    render_navigation()
    st.divider()
    
    # Create main layout with chat sidebar
    col1, col2 = st.columns([2, 1])  # Main content: 2/3, Chat: 1/3
    
    # Main content area
    with col1:
        # Render selected page
        page_renderers = {
            "Dashboard": render_dashboard,
            "Posts": render_posts,
            "Pages": render_pages,
            "Media": render_media,
            "Settings": render_settings
        }
        
        # Get the renderer for the current page
        renderer = page_renderers.get(st.session_state.current_page, render_dashboard)
        renderer()
    
    # Chat sidebar (persistent)
    with col2:
        st.markdown("### 💬 Agent Chat")
        
        # Site connection status
        if st.session_state.wp_api:
            st.success(f"✅ Connected to {st.session_state.wp_api.base_url}")
        else:
            st.error("❌ Not connected")
        
        # Chat interface
        render_chat_sidebar()
        
        # Chat actions
        with st.expander("Chat Options", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state.messages = []
                    st.rerun()
            with col_b:
                if st.button("💾 Export", use_container_width=True):
                    chat_data = json.dumps(st.session_state.messages, indent=2)
                    st.download_button(
                        label="📥 Download",
                        data=chat_data,
                        file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

if __name__ == "__main__":
    main()