#!/usr/bin/env python3
"""
Enhanced WordPress Visual Editor with Coming Soon handling
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
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import components
from backend.main import create_wordpress_memory_agent
from backend.wordpress_tools import WordPressAPI
from langchain_core.messages import HumanMessage, AIMessage

# Page config
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

if "current_page_data" not in st.session_state:
    st.session_state.current_page_data = None

if "pages_list" not in st.session_state:
    st.session_state.pages_list = []

if "preview_mode" not in st.session_state:
    st.session_state.preview_mode = "iframe"  # iframe or content

if "site_in_coming_soon" not in st.session_state:
    st.session_state.site_in_coming_soon = False

# CSS
st.markdown("""
<style>
    .main > div { padding-top: 0rem; }
    .block-container { padding-top: 1rem; }
    
    /* Preview container */
    .preview-container {
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        min-height: 600px;
        overflow-y: auto;
    }
    
    /* WordPress content styling */
    .wp-content {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
    }
    
    .wp-content h1 { font-size: 2.5em; margin: 0.67em 0; }
    .wp-content h2 { font-size: 2em; margin: 0.83em 0; }
    .wp-content h3 { font-size: 1.5em; margin: 1em 0; }
    .wp-content p { margin: 1em 0; }
    
    /* Chat styling */
    .chat-message {
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 10px;
    }
    
    .user-msg {
        background: #007bff;
        color: white;
        margin-left: 20%;
    }
    
    .assistant-msg {
        background: #f1f3f4;
        color: #333;
        margin-right: 20%;
    }
    
    /* Navigation */
    .nav-button {
        margin: 0 5px;
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer { display: none; }
</style>
""", unsafe_allow_html=True)

def check_coming_soon_mode():
    """Check if site is in coming soon mode"""
    if st.session_state.wp_api:
        try:
            response = requests.get(st.session_state.wp_api.base_url, timeout=5)
            if "coming soon" in response.text.lower() or "maintenance" in response.text.lower():
                st.session_state.site_in_coming_soon = True
                st.session_state.preview_mode = "content"  # Switch to content mode
                return True
        except:
            pass
    return False

def fetch_site_structure():
    """Fetch all pages"""
    if not st.session_state.wp_api:
        return
    
    try:
        pages_response = st.session_state.wp_api.request("/wp/v2/pages", params={"per_page": 100})
        if not pages_response.startswith("Error"):
            st.session_state.pages_list = json.loads(pages_response)
    except Exception as e:
        st.error(f"Error fetching pages: {e}")

def get_page_data(page_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get page content and metadata"""
    if not st.session_state.wp_api:
        return None
    
    try:
        if page_id:
            response = st.session_state.wp_api.request(f"/wp/v2/pages/{page_id}")
            if not response.startswith("Error"):
                return json.loads(response)
        else:
            # Get homepage content
            return {
                "title": {"rendered": "Welcome to " + st.session_state.wp_api.base_url},
                "content": {"rendered": "<p>Homepage content - select a page to view its content</p>"},
                "id": None
            }
    except:
        return None

def render_page_content(page_data: Dict[str, Any]):
    """Render page content in the preview area"""
    if page_data:
        st.markdown(f"## {page_data.get('title', {}).get('rendered', 'Untitled')}")
        
        # Show page metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"📄 Page ID: {page_data.get('id', 'Homepage')}")
        with col2:
            st.info(f"📅 Status: {page_data.get('status', 'N/A')}")
        with col3:
            if st.button("🔗 View Live", key="view_live"):
                st.write(f"URL: {page_data.get('link', st.session_state.wp_api.base_url)}")
        
        st.markdown("---")
        
        # Render content
        content = page_data.get('content', {}).get('rendered', '')
        if content:
            st.markdown(f'<div class="wp-content">{content}</div>', unsafe_allow_html=True)
        else:
            st.info("This page has no content yet. Start adding content using the chat!")

def render_iframe_preview():
    """Render site in iframe"""
    if st.session_state.current_page_url:
        iframe_html = f"""
        <iframe 
            src="{st.session_state.current_page_url}"
            width="100%"
            height="600"
            frameborder="0"
            style="border: 1px solid #ddd; border-radius: 8px;"
        ></iframe>
        """
        components.html(iframe_html, height=650)

def main():
    """Main application"""
    # Check coming soon mode on startup
    if "startup_check" not in st.session_state:
        st.session_state.startup_check = True
        check_coming_soon_mode()
        fetch_site_structure()
    
    # Header
    st.title("🎨 WordPress Visual Editor")
    
    # Coming soon warning
    if st.session_state.site_in_coming_soon:
        st.warning("⚠️ Your site is in 'Coming Soon' mode. Showing page content directly instead of live preview.")
    
    # Main layout
    col1, col2 = st.columns([3, 1])
    
    # Main content area
    with col1:
        # Navigation bar
        nav_cols = st.columns([1, 3, 1, 1, 1])
        
        with nav_cols[0]:
            if st.button("🏠 Home"):
                st.session_state.current_page_id = None
                st.session_state.current_page_data = get_page_data()
                st.session_state.current_page_url = st.session_state.wp_api.base_url
                st.rerun()
        
        with nav_cols[1]:
            if st.session_state.pages_list:
                page_options = ["Select a page..."] + [
                    f"{p.get('title', {}).get('rendered', 'Untitled')}" 
                    for p in st.session_state.pages_list
                ]
                selected_idx = st.selectbox(
                    "Navigate to:",
                    range(len(page_options)),
                    format_func=lambda x: page_options[x],
                    label_visibility="collapsed"
                )
                
                if selected_idx > 0:
                    selected_page = st.session_state.pages_list[selected_idx - 1]
                    st.session_state.current_page_id = selected_page['id']
                    st.session_state.current_page_data = selected_page
                    st.session_state.current_page_url = selected_page.get('link', '')
                    st.rerun()
        
        with nav_cols[2]:
            preview_mode = st.radio(
                "View:",
                ["Live", "Content"],
                index=0 if st.session_state.preview_mode == "iframe" else 1,
                horizontal=True,
                label_visibility="collapsed"
            )
            if preview_mode == "Live" and not st.session_state.site_in_coming_soon:
                st.session_state.preview_mode = "iframe"
            else:
                st.session_state.preview_mode = "content"
        
        with nav_cols[3]:
            if st.button("🔄 Refresh"):
                if st.session_state.current_page_id:
                    st.session_state.current_page_data = get_page_data(st.session_state.current_page_id)
                st.rerun()
        
        with nav_cols[4]:
            if st.button("➕ New Page"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Create a new blank page",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
        
        # Preview area
        st.markdown("---")
        
        if st.session_state.preview_mode == "content" or st.session_state.site_in_coming_soon:
            # Show content directly
            if not st.session_state.current_page_data and st.session_state.current_page_id:
                st.session_state.current_page_data = get_page_data(st.session_state.current_page_id)
            elif not st.session_state.current_page_data:
                st.session_state.current_page_data = get_page_data()  # Homepage
            
            with st.container():
                render_page_content(st.session_state.current_page_data)
        else:
            # Show iframe
            render_iframe_preview()
    
    # Chat sidebar
    with col2:
        st.markdown("### 💬 AI Assistant")
        
        # Status
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            if st.session_state.wp_api:
                st.success("✅ Connected")
            else:
                st.error("❌ Disconnected")
        
        with status_col2:
            if st.session_state.current_page_id:
                st.info(f"📄 Page {st.session_state.current_page_id}")
            else:
                st.info("🏠 Homepage")
        
        # Chat display
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-message user-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message assistant-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
        
        # Chat input
        user_input = st.chat_input("What would you like to do?")
        
        if user_input:
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            
            # Process with agent
            with st.spinner("Processing..."):
                try:
                    # Add context
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
                            ai_response = ai_messages[-1].content
                            
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": ai_response,
                                "timestamp": datetime.now().strftime("%I:%M %p")
                            })
                            
                            # Check for navigation commands
                            if "navigate to" in ai_response.lower():
                                # Extract page info from response
                                if "ID:" in ai_response:
                                    try:
                                        page_id = int(ai_response.split("ID:")[1].split(")")[0].strip())
                                        st.session_state.current_page_id = page_id
                                        st.session_state.current_page_data = get_page_data(page_id)
                                    except:
                                        pass
                            
                            # Refresh if content was changed
                            if any(word in ai_response.lower() for word in 
                                  ["updated", "changed", "added", "created", "modified"]):
                                if st.session_state.current_page_id:
                                    st.session_state.current_page_data = get_page_data(
                                        st.session_state.current_page_id
                                    )
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Quick actions
        with st.expander("⚡ Quick Actions"):
            if st.button("🎨 Change Background", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Change the background color to a nice gradient",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
            
            if st.button("📝 Add Section", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Add a new content section",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()
            
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        # Help text
        with st.expander("💡 Help"):
            st.markdown("""
            **Natural Language Commands:**
            - "Navigate to [page name]"
            - "Create a new page called..."
            - "Change the background to..."
            - "Add a section with..."
            - "Update the heading to..."
            
            **Tips:**
            - The AI knows which page you're viewing
            - Changes update automatically
            - Use Content view if Live preview doesn't work
            """)

if __name__ == "__main__":
    main()