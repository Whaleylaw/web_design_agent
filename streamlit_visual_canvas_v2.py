#!/usr/bin/env python3
"""
WordPress Visual Canvas v2 - Fixed dropdown and auto-load first page
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

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from main import create_wordpress_memory_agent
from wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page config
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
    with st.spinner("Initializing WordPress Visual Canvas..."):
        try:
            agent, memory_manager = create_wordpress_memory_agent(use_sqlite=True)
            st.session_state.agent = agent
            st.session_state.memory_manager = memory_manager
            st.session_state.wp_api = WordPressAPI()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Initialization failed: {e}")

# Compact CSS
st.markdown("""
<style>
    /* Ultra-compact layout */
    .main > div { padding-top: 0.5rem !important; }
    .block-container { 
        padding-top: 0 !important; 
        max-width: 100% !important;
    }
    
    /* Hide title */
    h1 { display: none !important; }
    
    /* Compact controls */
    .stButton > button {
        padding: 0.25rem 0.75rem !important;
        font-size: 0.875rem !important;
        min-height: 2rem !important;
    }
    
    .stSelectbox > div > div {
        padding: 0 !important;
    }
    
    /* Canvas styling */
    .canvas-frame {
        width: 100%;
        height: calc(100vh - 100px);
        border: 1px solid #ddd;
        border-radius: 4px;
        overflow: hidden;
        background: white;
    }
    
    /* Chat styling */
    .chat-container {
        height: calc(100vh - 90px);
        display: flex;
        flex-direction: column;
        background: #f8f9fa;
        border-radius: 4px;
        padding: 10px;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 10px;
        background: white;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    
    .user-msg {
        background: #0084ff;
        color: white;
        padding: 8px 14px;
        border-radius: 18px;
        margin: 4px 0;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .assistant-msg {
        background: #e4e6eb;
        color: #000;
        padding: 8px 14px;
        border-radius: 18px;
        margin: 4px 0;
        max-width: 80%;
        float: left;
        clear: both;
    }
    
    /* Hide elements */
    #MainMenu, footer { display: none; }
    
    /* Responsive columns */
    [data-testid="column"] {
        padding: 0 0.3rem !important;
    }
    
    /* Divider spacing */
    hr { margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

def init_theme_css():
    """Initialize WordPress theme CSS"""
    st.session_state.theme_css = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, sans-serif;
            font-size: 16px;
            line-height: 1.7;
            color: #333;
            background: #fff;
            margin: 0;
            padding: 20px;
        }
        
        /* Typography */
        h1 { font-size: 2.5em; margin: 0.67em 0; font-weight: 600; }
        h2 { font-size: 2em; margin: 0.83em 0; font-weight: 600; }
        h3 { font-size: 1.5em; margin: 1em 0; font-weight: 600; }
        h4 { font-size: 1.2em; margin: 1.33em 0; }
        
        p { margin: 0 0 1.5em; }
        
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
            margin: 1.5em 0;
        }
        
        .wp-block-button__link {
            background: #0073aa;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 4px;
            display: inline-block;
            transition: background 0.2s;
        }
        
        .wp-block-button__link:hover {
            background: #005177;
            color: white;
        }
        
        .wp-block-columns {
            display: flex;
            gap: 2em;
            margin-bottom: 1.5em;
        }
        
        .wp-block-column {
            flex: 1;
        }
        
        .wp-block-image img {
            max-width: 100%;
            height: auto;
        }
        
        /* Custom styles */
    </style>
    """

def fetch_pages():
    """Fetch all pages"""
    if st.session_state.wp_api:
        try:
            response = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 100})
            if not response.startswith("Error"):
                pages = json.loads(response)
                st.session_state.pages_list = pages
                
                # Auto-select first page if none selected
                if pages and not st.session_state.current_page_id:
                    first_page = pages[0]
                    st.session_state.current_page_id = first_page['id']
                    st.session_state.current_page_data = get_page_content(first_page['id'])
                
                return True
        except Exception as e:
            st.error(f"Error fetching pages: {e}")
    return False

def get_page_content(page_id):
    """Get page content"""
    if st.session_state.wp_api and page_id:
        try:
            response = st.session_state.wp_api.request(f"/wp/v2/pages/{page_id}")
            if not response.startswith("Error"):
                return json.loads(response)
        except:
            pass
    return None

def render_html_canvas(page_data):
    """Render page in canvas"""
    if page_data:
        title = page_data.get('title', {}).get('rendered', 'Untitled')
        content = page_data.get('content', {}).get('rendered', '')
        
        # Extract custom CSS
        custom_css = ""
        if "<style>" in content:
            import re
            style_matches = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
            custom_css = '\n'.join(style_matches)
        
        # Build HTML document
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {st.session_state.theme_css}
            <style>{custom_css}</style>
        </head>
        <body>
            <article>
                <h1>{title}</h1>
                {content}
            </article>
        </body>
        </html>
        """
        
        components.html(html_content, height=800, scrolling=True)
    else:
        # Welcome message
        welcome = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .welcome {
                    text-align: center;
                    padding: 60px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                h1 { color: #333; margin-bottom: 15px; }
                p { color: #666; font-size: 18px; }
            </style>
        </head>
        <body>
            <div class="welcome">
                <h1>Welcome to WordPress Visual Canvas</h1>
                <p>Loading your pages...</p>
            </div>
        </body>
        </html>
        """
        components.html(welcome, height=600)

def process_chat(user_input):
    """Process chat message"""
    try:
        context = user_input
        if st.session_state.current_page_id:
            context = f"[User is viewing page ID {st.session_state.current_page_id}] {user_input}"
        
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "visual_canvas_user"
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
        
        return "I couldn't process that request."
    except Exception as e:
        return f"Error: {str(e)}"

# Main app
def main():
    # Initialize theme CSS
    if not st.session_state.theme_css:
        init_theme_css()
    
    # Fetch pages on startup
    if not st.session_state.pages_list:
        fetch_pages()
    
    # Navigation bar
    nav_cols = st.columns([1, 5, 1, 1])
    
    with nav_cols[0]:
        if st.button("🏠 Home", use_container_width=True):
            # Show first page instead of blank
            if st.session_state.pages_list:
                first_page = st.session_state.pages_list[0]
                st.session_state.current_page_id = first_page['id']
                st.session_state.current_page_data = get_page_content(first_page['id'])
            st.rerun()
    
    with nav_cols[1]:
        # Page dropdown
        if st.session_state.pages_list:
            page_titles = [p.get('title', {}).get('rendered', 'Untitled') for p in st.session_state.pages_list]
            
            # Find current index
            current_idx = 0
            for i, page in enumerate(st.session_state.pages_list):
                if page['id'] == st.session_state.current_page_id:
                    current_idx = i
                    break
            
            selected_title = st.selectbox(
                "Page:",
                page_titles,
                index=current_idx,
                label_visibility="visible"
            )
            
            # Handle selection
            selected_idx = page_titles.index(selected_title)
            selected_page = st.session_state.pages_list[selected_idx]
            
            if selected_page['id'] != st.session_state.current_page_id:
                st.session_state.current_page_id = selected_page['id']
                st.session_state.current_page_data = get_page_content(selected_page['id'])
                st.rerun()
        else:
            st.info("Loading pages...")
    
    with nav_cols[2]:
        if st.button("🔄", use_container_width=True, help="Refresh"):
            if st.session_state.current_page_id:
                st.session_state.current_page_data = get_page_content(st.session_state.current_page_id)
            fetch_pages()
            st.rerun()
    
    with nav_cols[3]:
        if st.button("➕ New", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Create a new blank page"})
            st.rerun()
    
    st.markdown("---")
    
    # Main content: Canvas and Chat
    canvas_col, chat_col = st.columns([3, 1])
    
    # Canvas
    with canvas_col:
        with st.container():
            render_html_canvas(st.session_state.current_page_data)
    
    # Chat
    with chat_col:
        st.markdown("#### 💬 Chat")
        
        # Messages area
        chat_msgs = st.container(height=650)
        with chat_msgs:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', unsafe_allow_html=True)
            st.markdown('<div style="clear: both;"></div>', unsafe_allow_html=True)
        
        # Input form
        with st.form("chat", clear_on_submit=True):
            user_input = st.text_input("Message:", label_visibility="collapsed", placeholder="Type a message...")
            if st.form_submit_button("Send", use_container_width=True):
                if user_input:
                    # Add user message
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    # Get response
                    with st.spinner("..."):
                        response = process_chat(user_input)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Refresh if needed
                        if any(word in response.lower() for word in ["updated", "changed", "added", "created"]):
                            if st.session_state.current_page_id:
                                st.session_state.current_page_data = get_page_content(st.session_state.current_page_id)
                        
                        # Handle navigation
                        if "navigate to" in response.lower() and "ID:" in response:
                            try:
                                page_id = int(response.split("ID:")[1].split(")")[0].strip())
                                st.session_state.current_page_id = page_id
                                st.session_state.current_page_data = get_page_content(page_id)
                            except:
                                pass
                    
                    st.rerun()

if __name__ == "__main__":
    main()