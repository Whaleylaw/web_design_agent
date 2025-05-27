#!/usr/bin/env python3
"""
WordPress Local Canvas - Edit cloned pages with full preview
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys
from datetime import datetime
import json
from pathlib import Path
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from main import create_wordpress_memory_agent
from langchain_core.messages import HumanMessage, AIMessage

# Page config
st.set_page_config(
    page_title="WordPress Local Canvas",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.messages = []
    st.session_state.current_page_id = None
    st.session_state.pages_list = {}
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.agent = None
    st.session_state.clone_dir = Path("wordpress_clone")
    st.session_state.last_refresh = 0

# Initialize on first run
if not st.session_state.initialized:
    with st.spinner("Initializing..."):
        try:
            # Create agent with local editing tools
            agent, memory_manager = create_wordpress_memory_agent(use_sqlite=True)
            st.session_state.agent = agent
            st.session_state.memory_manager = memory_manager
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Initialization failed: {e}")

# CSS
st.markdown("""
<style>
    /* Minimal header */
    .main > div { padding-top: 0.5rem !important; }
    .block-container { padding-top: 0 !important; max-width: 100% !important; }
    h1 { display: none !important; }
    
    /* Compact controls */
    .stButton > button {
        padding: 0.3rem 0.8rem !important;
        font-size: 0.9rem !important;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-synced {
        background: #d4edda;
        color: #155724;
    }
    
    .status-modified {
        background: #fff3cd;
        color: #856404;
    }
    
    /* Chat */
    .chat-container {
        height: calc(100vh - 100px);
        background: #f8f9fa;
        border-radius: 4px;
        padding: 10px;
    }
    
    .user-msg {
        background: #007bff;
        color: white;
        padding: 8px 14px;
        border-radius: 18px;
        margin: 4px 0;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .assistant-msg {
        background: #e9ecef;
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
    hr { margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

def load_manifest():
    """Load clone manifest"""
    manifest_file = st.session_state.clone_dir / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file) as f:
            manifest = json.load(f)
            st.session_state.pages_list = manifest.get("pages", {})
            return True
    return False

def render_local_html(page_id):
    """Render local HTML file in iframe"""
    page_dir = st.session_state.clone_dir / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    
    if html_file.exists():
        # Read HTML content
        html_content = html_file.read_text()
        
        # Add auto-refresh script
        refresh_script = """
        <script>
        // Auto-refresh every 2 seconds if file modified
        let lastModified = document.lastModified;
        setInterval(() => {
            fetch(window.location.href, {method: 'HEAD'})
                .then(response => {
                    const newModified = response.headers.get('last-modified');
                    if (newModified && newModified !== lastModified) {
                        window.location.reload();
                    }
                });
        }, 2000);
        </script>
        """
        
        # Insert before closing body tag
        html_content = html_content.replace('</body>', refresh_script + '</body>')
        
        # Render in iframe
        components.html(html_content, height=800, scrolling=True)
    else:
        st.error(f"HTML file not found for page {page_id}")

def check_changes():
    """Check if local files have changes"""
    try:
        from wordpress_push import WordPressPush
        pusher = WordPressPush(st.session_state.clone_dir)
        changes = pusher.detect_changes()
        return changes
    except:
        return []

def process_chat(user_input):
    """Process chat with context"""
    try:
        # Add context about local editing
        context = f"[User is editing LOCAL page ID {st.session_state.current_page_id} in the cloned files] {user_input}"
        context += "\nIMPORTANT: Use the local editing tools (read_local_page_html, edit_local_page_content, add_local_page_css) to make changes to the LOCAL files, not the WordPress API."
        
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "local_canvas_user"
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

# Main UI
def main():
    # Check if clone exists
    if not load_manifest():
        st.warning("No local clone found. Click 'Clone Site' to download your WordPress pages.")
    
    # Navigation bar
    nav_cols = st.columns([1, 4, 1, 1, 1, 1])
    
    with nav_cols[0]:
        if st.button("🏠 Home"):
            if st.session_state.pages_list:
                first_id = list(st.session_state.pages_list.keys())[0]
                st.session_state.current_page_id = first_id
                st.rerun()
    
    with nav_cols[1]:
        # Page selector
        if st.session_state.pages_list:
            page_options = []
            page_ids = []
            
            for page_id, info in st.session_state.pages_list.items():
                page_options.append(info["title"])
                page_ids.append(page_id)
            
            if page_options:
                # Find current index
                current_idx = 0
                if st.session_state.current_page_id:
                    try:
                        current_idx = page_ids.index(str(st.session_state.current_page_id))
                    except:
                        pass
                
                selected_title = st.selectbox(
                    "Local Page:",
                    page_options,
                    index=current_idx
                )
                
                # Update selection
                selected_idx = page_options.index(selected_title)
                new_id = page_ids[selected_idx]
                
                if str(new_id) != str(st.session_state.current_page_id):
                    st.session_state.current_page_id = new_id
                    st.rerun()
        else:
            st.info("No pages cloned yet")
    
    with nav_cols[2]:
        if st.button("🔄 Refresh"):
            st.session_state.last_refresh = time.time()
            load_manifest()
            st.rerun()
    
    with nav_cols[3]:
        if st.button("📥 Clone"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Clone the WordPress site locally"
            })
            st.rerun()
    
    with nav_cols[4]:
        # Check for changes
        changes = check_changes()
        if changes:
            if st.button(f"📤 Push ({len(changes)})"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Push local changes to WordPress"
                })
                st.rerun()
        else:
            st.button("✓ Synced", disabled=True)
    
    with nav_cols[5]:
        # Status indicator
        if changes:
            st.markdown('<span class="status-badge status-modified">Modified</span>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-synced">In Sync</span>', 
                       unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main content
    canvas_col, chat_col = st.columns([3, 1])
    
    # Canvas - show local HTML
    with canvas_col:
        if st.session_state.current_page_id and st.session_state.pages_list:
            # Show page info
            page_info = st.session_state.pages_list.get(str(st.session_state.current_page_id), {})
            if page_info:
                st.caption(f"📝 Editing: {page_info.get('title', 'Unknown')} (ID: {st.session_state.current_page_id})")
            
            # Render local HTML
            with st.container():
                render_local_html(st.session_state.current_page_id)
        else:
            # Welcome message
            st.info("""
            ## WordPress Local Canvas
            
            This editor works with local copies of your WordPress pages:
            
            1. **Clone Site** - Download all pages locally
            2. **Edit Locally** - Make changes without affecting live site  
            3. **See Full HTML** - Agent can read actual page structure
            4. **Push Changes** - Upload changes when ready
            
            Click "Clone" to get started!
            """)
    
    # Chat
    with chat_col:
        st.markdown("#### 💬 Chat")
        
        # Info box
        with st.expander("ℹ️ Local Editing Mode", expanded=False):
            st.info("""
            You're editing LOCAL files.
            Changes are saved locally until you push.
            
            The agent can now:
            - See full HTML structure
            - Understand existing styles
            - Make precise edits
            """)
        
        # Messages
        chat_msgs = st.container(height=550)
        with chat_msgs:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', 
                               unsafe_allow_html=True)
            st.markdown('<div style="clear: both;"></div>', unsafe_allow_html=True)
        
        # Input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Message:", placeholder="Try: Change the background to blue")
            if st.form_submit_button("Send"):
                if user_input:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    with st.spinner("..."):
                        response = process_chat(user_input)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Auto-refresh if content changed
                        if any(word in response.lower() for word in ["updated", "changed", "added", "edited"]):
                            st.session_state.last_refresh = time.time()
                    
                    st.rerun()

if __name__ == "__main__":
    import time
    main()