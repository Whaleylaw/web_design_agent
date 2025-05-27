#!/usr/bin/env python3
"""
WordPress Visual Canvas - Full HTML rendering with styling like Claude Desktop
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys
from datetime import datetime
import json
from typing import Dict, Any, Optional
import uuid
from dotenv import load_dotenv
import requests
import base64

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from main import create_wordpress_memory_agent
from wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page config - MUST BE FIRST
st.set_page_config(
    page_title="WordPress Visual Canvas",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.messages = []
    st.session_state.current_page_id = None
    st.session_state.current_page_data = None
    st.session_state.pages_list = []
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.agent = None
    st.session_state.wp_api = None
    st.session_state.theme_css = ""

# Initialize on first run
if not st.session_state.initialized:
    with st.spinner("Initializing..."):
        try:
            agent, memory_manager = create_wordpress_memory_agent(use_sqlite=True)
            st.session_state.agent = agent
            st.session_state.memory_manager = memory_manager
            st.session_state.wp_api = WordPressAPI()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Initialization failed: {e}")

# Compact CSS for minimal header
st.markdown("""
<style>
    /* Minimize header space */
    .main > div { 
        padding-top: 0.5rem !important; 
    }
    
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    
    /* Compact title */
    h1 {
        font-size: 1.2rem !important;
        margin: 0 !important;
        padding: 5px 0 !important;
    }
    
    /* Minimize spacing */
    .stSelectbox > div > div {
        padding: 2px !important;
    }
    
    .stButton > button {
        padding: 0.25rem 0.5rem !important;
        font-size: 0.875rem !important;
    }
    
    /* Canvas container */
    .canvas-container {
        border: 1px solid #ddd;
        border-radius: 4px;
        overflow: hidden;
        width: 100%;
        height: calc(100vh - 120px);
        background: white;
    }
    
    /* Chat styling */
    .chat-container {
        height: calc(100vh - 100px);
        display: flex;
        flex-direction: column;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 10px;
    }
    
    .chat-input-area {
        border-top: 1px solid #ddd;
        padding: 10px;
    }
    
    .user-msg {
        background: #0084ff;
        color: white;
        padding: 8px 12px;
        border-radius: 18px;
        margin: 4px 0;
        margin-left: 20%;
        display: inline-block;
    }
    
    .assistant-msg {
        background: #e4e6eb;
        color: #000;
        padding: 8px 12px;
        border-radius: 18px;
        margin: 4px 0;
        margin-right: 20%;
        display: inline-block;
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer, .stDeployButton { display: none; }
    
    /* Compact columns */
    [data-testid="column"] {
        padding: 0 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

def fetch_theme_css():
    """Try to fetch WordPress theme CSS"""
    if st.session_state.wp_api:
        try:
            # Try to get theme info
            theme_response = st.session_state.wp_api.request("/wp/v2/themes")
            if not theme_response.startswith("Error"):
                # For now, use a default WordPress styling
                st.session_state.theme_css = """
                <style>
                    /* WordPress Default Styling */
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
                        font-size: 16px;
                        line-height: 1.6;
                        color: #333;
                        background: #fff;
                        margin: 0;
                        padding: 20px;
                    }
                    
                    h1, h2, h3, h4, h5, h6 {
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                        font-weight: 600;
                        line-height: 1.2;
                    }
                    
                    h1 { font-size: 2.5em; }
                    h2 { font-size: 2em; }
                    h3 { font-size: 1.5em; }
                    
                    p {
                        margin: 0 0 1.5em;
                    }
                    
                    a {
                        color: #0073aa;
                        text-decoration: underline;
                    }
                    
                    a:hover {
                        color: #005177;
                    }
                    
                    /* WordPress blocks */
                    .wp-block-buttons {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 0.5em;
                    }
                    
                    .wp-block-button__link {
                        background-color: #0073aa;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 4px;
                        display: inline-block;
                    }
                    
                    .wp-block-button__link:hover {
                        background-color: #005177;
                    }
                    
                    .wp-block-columns {
                        display: flex;
                        gap: 2em;
                        margin-bottom: 1.5em;
                    }
                    
                    .wp-block-column {
                        flex: 1;
                    }
                    
                    .wp-block-image {
                        margin: 1.5em 0;
                    }
                    
                    .wp-block-image img {
                        max-width: 100%;
                        height: auto;
                    }
                    
                    /* Custom styles from page */
                </style>
                """
        except:
            pass

def fetch_pages():
    """Fetch all pages from WordPress"""
    if st.session_state.wp_api:
        try:
            response = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 100})
            if not response.startswith("Error"):
                pages = json.loads(response)
                st.session_state.pages_list = pages
                return True
        except Exception as e:
            st.error(f"Error fetching pages: {e}")
    return False

def get_page_content(page_id):
    """Get specific page content"""
    if st.session_state.wp_api and page_id:
        try:
            response = st.session_state.wp_api.request(f"/wp/v2/pages/{page_id}")
            if not response.startswith("Error"):
                return json.loads(response)
        except Exception as e:
            st.error(f"Error fetching page content: {e}")
    return None

def render_html_canvas(page_data):
    """Render HTML content with full styling in an iframe-like canvas"""
    if page_data:
        title = page_data.get('title', {}).get('rendered', 'Untitled')
        content = page_data.get('content', {}).get('rendered', '')
        
        # Extract any custom CSS from the content
        custom_css = ""
        if "<style>" in content:
            import re
            style_matches = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
            custom_css = '\n'.join(style_matches)
        
        # Build complete HTML document
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {st.session_state.theme_css}
            <style>
                {custom_css}
            </style>
        </head>
        <body>
            <article>
                <h1>{title}</h1>
                {content}
            </article>
        </body>
        </html>
        """
        
        # Render in iframe-like component
        components.html(html_content, height=800, scrolling=True)
    else:
        # Welcome screen
        welcome_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .welcome {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #333; margin-bottom: 10px; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div class="welcome">
                <h1>WordPress Visual Canvas</h1>
                <p>Select a page from the dropdown to start editing</p>
                <p>or use the chat to create a new page</p>
            </div>
        </body>
        </html>
        """
        components.html(welcome_html, height=600)

def process_chat_message(user_input):
    """Process user message through the agent"""
    try:
        context = user_input
        if st.session_state.current_page_id:
            context = f"[User is viewing page ID {st.session_state.current_page_id}] {user_input}"
        
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "streamlit_user"
            }
        }
        
        response = st.session_state.agent.invoke(
            {"messages": [HumanMessage(content=context)]},
            config=config
        )
        
        if response and "messages" in response:
            ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                return ai_messages[-1].content
        
        return "I couldn't process that request. Please try again."
        
    except Exception as e:
        return f"Error: {str(e)}"

# Main UI
def main():
    # Fetch initial data
    if not st.session_state.pages_list:
        fetch_pages()
        fetch_theme_css()
        
        # Auto-select first page if available
        if st.session_state.pages_list and not st.session_state.current_page_id:
            first_page = st.session_state.pages_list[0]
            st.session_state.current_page_id = first_page['id']
            st.session_state.current_page_data = get_page_content(first_page['id'])
    
    # Header with navigation
    nav_container = st.container()
    with nav_container:
        col1, col2, col3, col4, col5 = st.columns([1, 4, 1, 1, 1])
        
        with col1:
            if st.button("🏠 Home", use_container_width=True, help="Go to homepage"):
                st.session_state.current_page_id = None
                st.session_state.current_page_data = None
                st.rerun()
        
            # Page selector dropdown
            page_options = []
            page_map = {}
            
            # Build options list
            for page in st.session_state.pages_list:
                title = page.get('title', {}).get('rendered', 'Untitled')
                page_id = page.get('id')
                page_options.append(title)
                page_map[title] = page_id
            
            # Find current selection
            current_index = 0
            if st.session_state.current_page_id:
                for i, page in enumerate(st.session_state.pages_list):
                    if page['id'] == st.session_state.current_page_id:
                        current_index = i
                        break
            
            # Show dropdown
            if page_options:
                selected = st.selectbox(
                    "Select page:",
                    page_options,
                    index=current_index,
                    key="page_dropdown"
                )
                
                # Handle selection
                if selected in page_map:
                    new_id = page_map[selected]
                    if new_id != st.session_state.current_page_id:
                        st.session_state.current_page_id = new_id
                        st.session_state.current_page_data = get_page_content(new_id)
                        st.rerun()
            else:
                st.info("No pages found")
        
        with col3:
            if st.button("🔄", help="Refresh", use_container_width=True):
                if st.session_state.current_page_id:
                    st.session_state.current_page_data = get_page_content(st.session_state.current_page_id)
                fetch_pages()
                st.rerun()
        
        with col4:
            if st.button("➕", help="New Page", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Create a new blank page"
                })
                st.rerun()
        
        with col5:
            # Status indicator
            if st.session_state.wp_api:
                st.success("✅ Connected")
    
    # Main content area with canvas and chat
    st.markdown("---")
    
    canvas_col, chat_col = st.columns([3, 1])
    
    # Canvas area
    with canvas_col:
        with st.container():
            render_html_canvas(st.session_state.current_page_data)
    
    # Chat sidebar
    with chat_col:
        st.markdown("### 💬 Chat")
        
        # Chat messages
        chat_container = st.container(height=650)
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
        
        # Chat input
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input("Message:", key="chat_input", label_visibility="collapsed")
            col1, col2 = st.columns([3, 1])
            with col2:
                submit = st.form_submit_button("Send", use_container_width=True)
            
            if submit and user_input:
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input
                })
                
                with st.spinner("..."):
                    ai_response = process_chat_message(user_input)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    
                    # Refresh if content changed
                    if any(kw in ai_response.lower() for kw in ["updated", "changed", "added", "created"]):
                        if st.session_state.current_page_id:
                            st.session_state.current_page_data = get_page_content(st.session_state.current_page_id)
                    
                    # Handle navigation
                    if "navigate to" in ai_response.lower() and "ID:" in ai_response:
                        try:
                            page_id = int(ai_response.split("ID:")[1].split(")")[0].strip())
                            st.session_state.current_page_id = page_id
                            st.session_state.current_page_data = get_page_content(page_id)
                        except:
                            pass
                
                st.rerun()

if __name__ == "__main__":
    main()