#!/usr/bin/env python3
"""
Fixed WordPress Visual Editor - Working page selection and chat
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

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import components
from backend.main import create_wordpress_memory_agent
from backend.wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page config - MUST BE FIRST
st.set_page_config(
    page_title="WordPress Visual Editor",
    page_icon="🎨",
    layout="wide"
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

# Initialize on first run
if not st.session_state.initialized:
    with st.spinner("Initializing WordPress Agent..."):
        try:
            # Create agent
            agent, memory_manager = create_wordpress_memory_agent(use_sqlite=True)
            st.session_state.agent = agent
            st.session_state.memory_manager = memory_manager
            
            # Initialize WordPress API
            st.session_state.wp_api = WordPressAPI()
            
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Initialization failed: {e}")

# CSS
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    
    .content-display {
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        min-height: 500px;
    }
    
    .chat-msg-user {
        background: #0084ff;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        margin-left: 20%;
    }
    
    .chat-msg-assistant {
        background: #f0f0f0;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        margin-right: 20%;
    }
    
    .page-title {
        font-size: 2em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    .page-content {
        line-height: 1.6;
    }
    
    .page-content h1 { font-size: 2em; margin: 20px 0 10px 0; }
    .page-content h2 { font-size: 1.5em; margin: 20px 0 10px 0; }
    .page-content h3 { font-size: 1.2em; margin: 20px 0 10px 0; }
    .page-content p { margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# Helper functions
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

def display_page_content(page_data):
    """Display page content in the main area"""
    if page_data:
        # Title
        title = page_data.get('title', {}).get('rendered', 'Untitled')
        st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
        
        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"📄 Page ID: {page_data.get('id', 'N/A')}")
        with col2:
            st.info(f"📅 Status: {page_data.get('status', 'N/A')}")
        with col3:
            st.info(f"🔗 Slug: {page_data.get('slug', 'N/A')}")
        
        st.markdown("---")
        
        # Content
        content = page_data.get('content', {}).get('rendered', '')
        if content:
            st.markdown(f'<div class="page-content">{content}</div>', unsafe_allow_html=True)
        else:
            st.info("This page has no content yet. Use the chat to add content!")
    else:
        st.info("Select a page from the dropdown to view its content.")

def process_chat_message(user_input):
    """Process user message through the agent"""
    try:
        # Add context about current page
        context = user_input
        if st.session_state.current_page_id:
            context = f"[User is viewing page ID {st.session_state.current_page_id}] {user_input}"
        
        # Configure agent
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "streamlit_user"
            }
        }
        
        # Get response
        response = st.session_state.agent.invoke(
            {"messages": [HumanMessage(content=context)]},
            config=config
        )
        
        # Extract AI response
        if response and "messages" in response:
            ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                return ai_messages[-1].content
        
        return "I couldn't process that request. Please try again."
        
    except Exception as e:
        return f"Error: {str(e)}"

# Main UI
def main():
    st.title("🎨 WordPress Visual Editor")
    
    # Fetch pages on first load
    if not st.session_state.pages_list:
        fetch_pages()
    
    # Layout: Content (75%) and Chat (25%)
    col_main, col_chat = st.columns([3, 1])
    
    # Main content area
    with col_main:
        # Navigation bar
        nav_cols = st.columns([1, 4, 1])
        
        with nav_cols[0]:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.current_page_id = None
                st.session_state.current_page_data = None
                st.rerun()
        
        with nav_cols[1]:
            # Page dropdown
            page_options = ["Select a page..."]
            page_map = {}
            
            for page in st.session_state.pages_list:
                title = page.get('title', {}).get('rendered', 'Untitled')
                page_id = page.get('id')
                option_text = f"{title} (ID: {page_id})"
                page_options.append(option_text)
                page_map[option_text] = page_id
            
            selected_option = st.selectbox(
                "Navigate to page:",
                page_options,
                key="page_selector"
            )
            
            # Handle page selection
            if selected_option != "Select a page..." and selected_option in page_map:
                selected_id = page_map[selected_option]
                if selected_id != st.session_state.current_page_id:
                    st.session_state.current_page_id = selected_id
                    st.session_state.current_page_data = get_page_content(selected_id)
                    st.rerun()
        
        with nav_cols[2]:
            if st.button("🔄 Refresh", use_container_width=True):
                if st.session_state.current_page_id:
                    st.session_state.current_page_data = get_page_content(st.session_state.current_page_id)
                fetch_pages()
                st.rerun()
        
        # Display area
        st.markdown("---")
        
        # Show current page content
        if st.session_state.current_page_data:
            display_page_content(st.session_state.current_page_data)
        else:
            # Show homepage/welcome message
            st.markdown("## Welcome to WordPress Visual Editor")
            st.info("Select a page from the dropdown above to start editing, or use the chat to create a new page.")
            
            # Show site info if available
            if st.session_state.wp_api:
                st.markdown(f"**Connected to:** {st.session_state.wp_api.base_url}")
    
    # Chat sidebar
    with col_chat:
        st.markdown("### 💬 AI Assistant")
        
        # Connection status
        if st.session_state.wp_api:
            st.success("✅ Connected")
        else:
            st.error("❌ Not connected")
        
        # Chat container
        chat_container = st.container(height=400)
        
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-msg-user">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-msg-assistant">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
        
        # Chat input - using form to prevent rerun issues
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input("Type your message:", key="chat_input")
            submit = st.form_submit_button("Send", use_container_width=True)
            
            if submit and user_input:
                # Add user message
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Get AI response
                with st.spinner("Thinking..."):
                    ai_response = process_chat_message(user_input)
                    
                    # Add AI response
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    
                    # Check if we need to refresh page content
                    refresh_keywords = ["updated", "changed", "added", "created", "modified"]
                    if any(keyword in ai_response.lower() for keyword in refresh_keywords):
                        if st.session_state.current_page_id:
                            st.session_state.current_page_data = get_page_content(
                                st.session_state.current_page_id
                            )
                    
                    # Check for navigation
                    if "navigate to" in ai_response.lower() and "ID:" in ai_response:
                        try:
                            # Extract page ID from response
                            page_id = int(ai_response.split("ID:")[1].split(")")[0].strip())
                            st.session_state.current_page_id = page_id
                            st.session_state.current_page_data = get_page_content(page_id)
                        except:
                            pass
                
                st.rerun()
        
        # Quick actions
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 New Page", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Create a new blank page"
                })
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        # Help section
        with st.expander("💡 Help & Examples"):
            st.markdown("""
            **Try these commands:**
            - "Navigate to the About page"
            - "Create a new page called Services"
            - "Change the background to light blue"
            - "Add a contact section"
            - "Update the heading text"
            """)

if __name__ == "__main__":
    main()