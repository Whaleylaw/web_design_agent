#!/usr/bin/env python3
"""
WordPress Local Canvas - Edit cloned pages with full preview
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import time
from datetime import datetime
import json
from pathlib import Path
import uuid
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import components
from backend.main import create_wordpress_memory_agent
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
    st.session_state.initialization_error = None

# Initialize on first run
if not st.session_state.initialized:
    with st.spinner("Initializing WordPress Memory Agent..."):
        try:
            # Initialize the agent - add explicit debugging
            if 'agent' not in st.session_state or st.session_state.agent is None:
                st.info("🔄 Creating new agent instance...")
                try:
                    # Use the robust checkpointer initialization
                    agent, memory_manager = create_wordpress_memory_agent(
                        use_sqlite=True, 
                        model_name="auto"
                    )
                    
                    # Explicit validation that agent was created successfully
                    if agent is None:
                        raise ValueError("Agent creation returned None")
                        
                    # Only set session state if agent is valid
                    st.session_state.agent = agent
                    st.session_state.memory_manager = memory_manager
                    st.success("🧠 WordPress Memory Agent initialized with enhanced duplicate prevention!")
                    st.info(f"✅ Agent type: {type(agent).__name__}")
                    
                except Exception as e:
                    st.error(f"Failed to initialize agent: {e}")
                    st.error("Trying fallback initialization...")
                    
                    # Clear any partially set state
                    if 'agent' in st.session_state:
                        del st.session_state.agent
                    if 'memory_manager' in st.session_state:
                        del st.session_state.memory_manager
                    
                    try:
                        # Fallback to no persistence
                        agent, memory_manager = create_wordpress_memory_agent(
                            use_sqlite=False, 
                            model_name="auto"
                        )
                        
                        # Explicit validation for fallback too
                        if agent is None:
                            raise ValueError("Fallback agent creation returned None")
                            
                        st.session_state.agent = agent
                        st.session_state.memory_manager = memory_manager
                        st.warning("⚠️ Agent initialized without SQLite persistence (using in-memory)")
                        st.info(f"✅ Fallback agent type: {type(agent).__name__}")
                        
                    except Exception as e2:
                        st.error(f"Failed to initialize agent even with fallback: {e2}")
                        # Ensure agent is None if initialization failed
                        st.session_state.agent = None
                        st.session_state.memory_manager = None
                        st.stop()
            else:
                st.info(f"✅ Agent already initialized: {type(st.session_state.agent).__name__}")
                
            # Final validation before proceeding
            if st.session_state.agent is None:
                st.error("❌ Agent is None after initialization!")
                st.error("Please refresh the page to try again.")
                st.stop()
                
            st.session_state.initialized = True
            st.session_state.initialization_error = None
            
        except Exception as e:
            st.session_state.initialization_error = str(e)
            st.error(f"Failed to initialize agent: {e}")
            st.error("Please check your .env file and ensure API keys are set correctly.")
            # Ensure clean state on error
            st.session_state.agent = None
            st.session_state.memory_manager = None
            st.stop()

# CSS
st.markdown("""
<style>
    /* Main layout styling */
    .main > div { padding-top: 1rem !important; }
    .block-container { padding-top: 1rem !important; max-width: 100% !important; }
    
    /* Title styling */
    h1 { 
        font-size: 1.4rem !important; 
        margin-bottom: 1rem !important;
        margin-top: 0 !important;
        text-align: center !important;
    }
    
    /* Left panel styling */
    .stColumn:first-child {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-right: 1rem !important;
    }
    
    /* Compact button styling */
    .stButton > button {
        padding: 0.4rem 0.8rem !important;
        font-size: 0.9rem !important;
        margin: 0.2rem 0 !important;
        width: 100% !important;
    }
    
    /* Selectbox styling */
    .stSelectbox {
        margin-bottom: 0.5rem !important;
    }
    
    .stSelectbox label {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.3rem !important;
    }
    
    /* Text area for chat input */
    .stTextArea textarea {
        min-height: 80px !important;
        max-height: 120px !important;
    }
    
    /* Chat container styling */
    .stContainer > div {
        max-height: 400px !important;
        overflow-y: auto !important;
        padding: 0.5rem !important;
        background-color: white !important;
        border-radius: 4px !important;
        border: 1px solid #ddd !important;
    }
    
    /* Chat message styling */
    .chat-user {
        background: #e3f2fd;
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.2rem 0;
        border-left: 3px solid #2196f3;
    }
    
    .chat-assistant {
        background: #f5f5f5;
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.2rem 0;
        border-left: 3px solid #4caf50;
    }
    
    /* Chat debug section styling */
    .chat-debug {
        background: #fff8e1;
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.2rem 0 0.5rem 0;
        border-left: 3px solid #ff9800;
        font-family: monospace;
        font-size: 0.85rem;
    }
    
    .chat-debug details {
        margin: 0;
        padding: 0;
    }
    
    .chat-debug summary {
        cursor: pointer;
        font-weight: bold;
        color: #e65100;
        padding: 0.3rem;
        background: #ffe0b2;
        border-radius: 4px;
        margin-bottom: 0.5rem;
    }
    
    .chat-debug summary:hover {
        background: #ffcc80;
    }
    
    .chat-debug details[open] summary {
        margin-bottom: 0.5rem;
        border-bottom: 1px solid #ff9800;
    }
    
    /* Section headers in left panel */
    .stMarkdown h3 {
        font-size: 1.1rem !important;
        margin: 1rem 0 0.5rem 0 !important;
        color: #333 !important;
        border-bottom: 2px solid #e0e0e0 !important;
        padding-bottom: 0.2rem !important;
    }
    
    /* Success/info/warning messages in left panel */
    .stSuccess, .stInfo, .stWarning, .stError {
        padding: 0.5rem !important;
        margin: 0.5rem 0 !important;
        font-size: 0.9rem !important;
    }
    
    /* Right panel iframe styling */
    .stColumn:last-child iframe {
        border: 2px solid #ddd !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    /* Side-by-side iframe styling for comparison */
    .stColumn iframe {
        border: 2px solid #ddd !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        width: 100% !important;
    }
    
    /* Local version styling */
    .stColumn:nth-child(1) iframe {
        border-color: #4caf50 !important;
    }
    
    /* Clone version styling */
    .stColumn:nth-child(2) iframe {
        border-color: #2196f3 !important;
    }
    
    /* Comparison headers */
    .stColumn h4 {
        font-size: 1rem !important;
        margin: 0.5rem 0 !important;
        text-align: center !important;
        padding: 0.3rem !important;
        border-radius: 4px !important;
    }
    
    /* Local version header styling */
    .stColumn:nth-child(1) h4 {
        background-color: #e8f5e8 !important;
        color: #2e7d32 !important;
        border: 1px solid #4caf50 !important;
    }
    
    /* Clone version header styling */
    .stColumn:nth-child(2) h4 {
        background-color: #e3f2fd !important;
        color: #1565c0 !important;
        border: 1px solid #2196f3 !important;
    }
    
    /* Expander styling in left panel */
    .streamlit-expanderHeader {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    /* Code blocks for diffs */
    .stCode {
        font-size: 0.8rem !important;
        max-height: 200px !important;
        overflow-y: auto !important;
    }
    
    /* Streaming display styling */
    .streaming-display {
        background: linear-gradient(45deg, #f8f9fa, #e9ecef) !important;
        border: 2px dashed #6c757d !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        animation: pulse 2s infinite !important;
    }
    
    @keyframes pulse {
        0% { border-color: #6c757d; }
        50% { border-color: #007bff; }
        100% { border-color: #6c757d; }
    }
    
    /* Tool call styling in streaming */
    .tool-call {
        background-color: #fff3cd !important;
        border-left: 4px solid #ffc107 !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.2rem 0 !important;
        font-family: monospace !important;
        font-size: 0.8rem !important;
    }
    
    /* Agent response styling in streaming */
    .agent-response {
        background-color: #d1ecf1 !important;
        border-left: 4px solid #17a2b8 !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.2rem 0 !important;
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer { display: none; }
    
    /* Reduce spacing */
    .element-container { margin-bottom: 0.5rem !important; }
    
    /* Form styling */
    .stForm {
        border: none !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

def load_manifest():
    """Load clone manifest"""
    manifest_file = st.session_state.clone_dir / "manifest.json"
    if manifest_file.exists():
        try:
            with open(manifest_file) as f:
                manifest = json.load(f)
            st.session_state.pages_list = manifest.get("pages", {})
            return True
        except json.JSONDecodeError as e:
            st.error(f"Manifest file is corrupted: {e}")
            st.error("Try re-cloning the site to fix the manifest.")
            st.session_state.pages_list = {}
            return False
        except Exception as e:
            st.error(f"Error loading manifest: {e}")
            st.session_state.pages_list = {}
            return False
    return False

def render_local_html(page_id):
    """Render local HTML file in iframe"""
    page_dir = st.session_state.clone_dir / f"pages/page_{page_id}"
    html_file = page_dir / "index.html"
    
    if html_file.exists():
        # Read and display HTML content exactly as-is
        html_content = html_file.read_text()
        
        # Only add DOCTYPE if missing to ensure proper rendering
        if not html_content.strip().lower().startswith('<!doctype'):
            html_content = '<!DOCTYPE html>\n' + html_content
        
        # Render the raw HTML directly in iframe
        components.html(html_content, height=900, scrolling=True)
    else:
        st.error(f"HTML file not found for page {page_id}")
        st.info("Try cloning the site or creating a new page.")

def render_clone_html(page_id):
    """Render clone HTML file in iframe"""
    page_dir = st.session_state.clone_dir / f"pages/page_{page_id}"
    clone_file = page_dir / "clone.html"
    
    if clone_file.exists():
        # Read and display clone HTML content
        clone_content = clone_file.read_text()
        
        # Only add DOCTYPE if missing to ensure proper rendering
        if not clone_content.strip().lower().startswith('<!doctype'):
            clone_content = '<!DOCTYPE html>\n' + clone_content
        
        # Render the clone HTML in iframe
        components.html(clone_content, height=900, scrolling=True)
    else:
        st.error(f"Clone file not found for page {page_id}")
        st.info("Try cloning the site to create the clone file.")

def check_changes():
    """Check if local files have changes using the change log"""
    try:
        change_log_file = Path("temp/change_log.json")
        
        if not change_log_file.exists():
            return []
        
        with open(change_log_file, 'r') as f:
            changes = json.load(f)
        
        # Return only unpushed changes
        unpushed_changes = [c for c in changes if not c.get("pushed", False)]
        return unpushed_changes
        
    except Exception as e:
        print(f"Error checking changes: {e}")
        return []

def check_real_sync_status():
    """Check sync status using V2 file comparison system (much more reliable)"""
    try:
        from backend.wordpress_sync_v2 import WordPressSyncV2
        
        # Check if clone exists
        if not st.session_state.clone_dir.exists():
            return {"status": "no_clone", "message": "No local clone found"}
        
        # Always use V2 sync system (no migration needed)
        sync = WordPressSyncV2(str(st.session_state.clone_dir))
        status = sync.sync_status_v2()
        
        # Convert V2 status to frontend format
        if status["status"] == "synced":
            return {
                "status": "synced",
                "local_changes": 0,
                "wordpress_changes": 0,
                "message": "All files match their WordPress snapshots"
            }
        elif status["status"] == "local_only_pages":
            local_only_count = len(status.get("local_only", []))
            return {
                "status": "local_only",
                "local_changes": local_only_count,
                "wordpress_changes": 0,
                "message": f"{local_only_count} local pages not yet published to WordPress"
            }
        elif status["status"] == "needs_sync":
            modified_count = len(status.get("changes", []))
            local_only_count = len(status.get("local_only", []))
            total_changes = modified_count + local_only_count
            
            # Check if these are likely enhancements vs actual changes
            enhanced_pages = 0
            actual_changes = 0
            
            for change in status.get("changes", []):
                if change.get("status") == "modified":
                    # These are enhanced local versions - not problems to fix
                    enhanced_pages += 1
                else:
                    # These might be actual issues
                    actual_changes += 1
            
            if enhanced_pages > 0 and actual_changes == 0:
                # All changes are enhanced local versions
                return {
                    "status": "enhanced",
                    "local_changes": enhanced_pages,
                    "wordpress_changes": 0,
                    "message": f"{enhanced_pages} enhanced local versions (styled/improved)"
                }
            else:
                return {
                    "status": "local_newer",
                    "local_changes": total_changes,
                    "wordpress_changes": 0,
                    "message": f"{modified_count} modified pages, {local_only_count} local-only pages"
                }
        else:
            return {
                "status": "local_newer",
                "local_changes": len(status["changes"]),
                "wordpress_changes": 0,
                "message": f"{len(status['changes'])} pages have local modifications"
            }
            
    except Exception as e:
        return {"status": "error", "message": f"Sync check failed: {e}"}

def perform_push():
    """Actually perform the push operation"""
    try:
        # Check if agent is initialized
        if st.session_state.agent is None:
            return "Error: Agent not initialized."
        
        # Use the agent to push changes
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "local_canvas_user"
            },
            "recursion_limit": 50  # Increased limit for reflection workflow
        }
        
        # Create a message to push all changes
        response = st.session_state.agent.invoke(
            {"messages": [HumanMessage(content="Use push_changes_to_wordpress to push all unpushed changes to WordPress")]},
            config=config
        )
        
        if response and "messages" in response:
            ai_messages = [msg for msg in response["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                return ai_messages[-1].content
        
        return "Push operation completed."
        
    except Exception as e:
        return f"Error during push: {str(e)}"

def check_navigation_commands():
    """Check for navigation commands from the agent"""
    try:
        nav_file = Path("temp/navigation_command.json")
        if nav_file.exists():
            with open(nav_file, 'r') as f:
                command = json.load(f)
            
            if command.get("action") == "navigate":
                new_page_id = str(command.get("page_id"))
                
                # Debug: Show what we're trying to navigate to
                st.info(f"🔄 Navigation command received: Page {new_page_id}")
                
                # Reload manifest to ensure we have latest page list
                load_manifest()
                
                # Check if this page exists in our local clone
                if new_page_id in st.session_state.pages_list:
                    if str(new_page_id) != str(st.session_state.current_page_id):
                        st.session_state.current_page_id = new_page_id
                        # Remove the command file so we don't process it again
                        nav_file.unlink()
                        st.success(f"✅ Navigated to page {new_page_id}")
                        return True
                    else:
                        # Already on this page
                        nav_file.unlink()
                        st.info(f"ℹ️ Already viewing page {new_page_id}")
                        return False
                else:
                    # Page not in local clone
                    nav_file.unlink()
                    st.warning(f"⚠️ Page {new_page_id} not found in local clone. Available pages: {list(st.session_state.pages_list.keys())}")
                    return False
            
            # Remove processed command file
            nav_file.unlink()
            
    except Exception as e:
        # Show navigation errors for debugging
        st.error(f"Navigation error: {e}")
    
    return False

def check_refresh_commands():
    """Check for refresh commands from the agent"""
    try:
        refresh_file = Path("temp/refresh_command.json")
        if refresh_file.exists():
            # Remove the command file and trigger refresh
            refresh_file.unlink()
            return True
    except Exception:
        pass
    return False

def check_cache_clear_commands():
    """Check for cache clear commands from the agent"""
    try:
        cache_clear_file = Path("temp/clear_cache_command.json")
        if cache_clear_file.exists():
            # Clear all sync status cache entries
            for key in list(st.session_state.keys()):
                if key.startswith('sync_status_cache_'):
                    del st.session_state[key]
            
            # Remove the command file
            cache_clear_file.unlink()
            return True
    except Exception:
        pass
    return False

def process_chat(user_input):
    """Legacy non-streaming version for fallback"""
    try:
        # Check if agent is initialized
        if st.session_state.agent is None:
            return "Error: Agent not initialized. Please refresh the page or check your configuration."
        
        # Add context about local editing
        context = f"[User is editing LOCAL page ID {st.session_state.current_page_id} in the cloned files] {user_input}"
        context += "\nIMPORTANT: Use the filesystem tools (read_file, write_file, etc.) to make changes to the LOCAL files. Use wp_navigate_to_page to change which page is displayed."
        
        config = {
            "configurable": {
                "thread_id": st.session_state.session_id,
                "user_id": "local_canvas_user"
            },
            "recursion_limit": 50  # Increased limit for reflection workflow
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

def get_sync_status():
    """Get sync status with caching but force refresh after operations"""
    
    # Check for force refresh commands (including new force refresh files)
    refresh_commands = [
        "temp/refresh_command.json",
        "temp/clear_cache_command.json",
        "temp/force_refresh_0.json",
        "temp/force_refresh_1.json"
    ]
    
    force_refresh_detected = False
    
    for cmd_file in refresh_commands:
        if os.path.exists(cmd_file):
            try:
                # Clear all sync status caches
                for key in list(st.session_state.keys()):
                    if key.startswith('sync_status_cache') or key == 'pages_list':
                        del st.session_state[key]
                
                # Remove the command file
                os.remove(cmd_file)
                print(f"🔄 Cache cleared due to {cmd_file}")
                force_refresh_detected = True
                
            except Exception as e:
                print(f"Warning: Cache clear failed: {e}")
    
    # Force refresh if pages were just loaded/changed
    if 'force_sync_refresh' in st.session_state:
        for key in list(st.session_state.keys()):
            if key.startswith('sync_status_cache'):
                del st.session_state[key]
        del st.session_state['force_sync_refresh']
        force_refresh_detected = True
    
    cache_key = "sync_status_cache"
    cache_time_key = "sync_status_cache_time"
    
    # If force refresh detected, don't use cache at all
    if force_refresh_detected:
        print("🔄 Force refresh detected - bypassing cache entirely")
    
    # Check if we have a valid cached result (max 5 seconds old, or bypass if force refresh)
    if (not force_refresh_detected and 
        cache_key in st.session_state and 
        cache_time_key in st.session_state and
        time.time() - st.session_state[cache_time_key] < 5):
        return st.session_state[cache_key]
    
    # Get fresh sync status
    try:
        # Use the existing function that properly imports the sync system
        status = check_real_sync_status()
        
        # Cache the result
        st.session_state[cache_key] = status
        st.session_state[cache_time_key] = time.time()
        
        return status
            
    except Exception as e:
        print(f"Error getting sync status: {e}")
        return {"status": "error", "message": f"Sync check failed: {str(e)}"}

# Main UI
def main():
    # Add title
    st.title("📝 Local Website Editor")
    
    # Check if clone exists
    if not load_manifest():
        st.warning("No local pages found. Click 'Clone Site' to download your website pages.")
    
    # Set default page if none selected and pages exist
    if not st.session_state.current_page_id and st.session_state.pages_list:
        st.session_state.current_page_id = list(st.session_state.pages_list.keys())[0]
    
    # Check for navigation commands from the agent
    if check_navigation_commands():
        st.rerun()
    
    # Check for refresh commands from the agent
    if check_refresh_commands():
        load_manifest()  # Reload the manifest
        st.rerun()
    
    # Check for cache clear commands from the agent
    if check_cache_clear_commands():
        st.rerun()  # Refresh after clearing cache
    
    # Main layout: Left panel (controls/chat) and Right panel (page display)
    left_panel, right_panel = st.columns([1, 2])  # Left panel smaller, right panel larger for page display
    
    # LEFT PANEL - All controls and chat
    with left_panel:
        st.markdown("### 🎛️ Controls")
        
        # Page selector (more compact)
        if st.session_state.pages_list:
            page_options = []
            page_ids = []
            
            for page_id, info in st.session_state.pages_list.items():
                # Show both page title and ID number for easy reference
                page_options.append(f"{info['title']} ({page_id})")
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
                    "Page:",
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
        
        # Sync status (using improved caching)
        sync_status = get_sync_status()
        
        # Very compact status
        if sync_status["status"] == "synced":
            st.success("✅ Synced", icon="✅")
        elif sync_status["status"] == "enhanced":
            st.info(f"🎨 {sync_status['local_changes']} enhanced", icon="🎨")
        elif sync_status["status"] == "local_only":
            st.info(f"📝 {sync_status['local_changes']} local pages", icon="📝")
        elif sync_status["status"] == "local_newer":
            st.warning(f"🔄 {sync_status['local_changes']} changes", icon="🔄")
        elif sync_status["status"] == "error":
            st.error(f"❌ {sync_status.get('message', 'Unknown error')}", icon="❌")
        else:
            st.warning(f"⚠️ {sync_status.get('message', 'Unknown status')}", icon="⚠️")
        
        # Compact action buttons in a single row
        if sync_status["status"] == "local_newer" or sync_status["status"] == "local_only":
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄", help="Refresh", use_container_width=True):
                    # Force a complete refresh
                    st.session_state.force_sync_refresh = True
                    for key in list(st.session_state.keys()):
                        if key.startswith('sync_status_cache') or key.startswith('pages_list'):
                            del st.session_state[key]
                    load_manifest()
                    st.rerun()
            with col2:
                if st.button("📥", help="Clone", use_container_width=True):
                    clone_message = "Use clone_wordpress_site_v2 to download all WordPress pages"
                    st.session_state.messages.append({"role": "user", "content": clone_message})
                    st.rerun()
            with col3:
                if st.button("🚀", help="Deploy to Netlify", use_container_width=True):
                    push_message = "Use deploy_all_to_netlify to deploy all pages to Netlify"
                    st.session_state.messages.append({"role": "user", "content": push_message})
                    # Force refresh after push
                    st.session_state.force_sync_refresh = True
                    st.rerun()
        elif sync_status["status"] == "enhanced":
            # Enhanced pages are already synced to WordPress, just with local styling
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄", help="Refresh", use_container_width=True):
                    # Force a complete refresh
                    st.session_state.force_sync_refresh = True
                    for key in list(st.session_state.keys()):
                        if key.startswith('sync_status_cache') or key.startswith('pages_list'):
                            del st.session_state[key]
                    load_manifest()
                    st.rerun()
            with col2:
                if st.button("📥", help="Clone", use_container_width=True):
                    clone_message = "Use clone_wordpress_site_v2 to download all WordPress pages"
                    st.session_state.messages.append({"role": "user", "content": clone_message})
                    st.rerun()
        else:
            # For synced status or error - show refresh and clone buttons only
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄", help="Refresh", use_container_width=True):
                    # Force a complete refresh
                    st.session_state.force_sync_refresh = True
                    for key in list(st.session_state.keys()):
                        if key.startswith('sync_status_cache') or key.startswith('pages_list'):
                            del st.session_state[key]
                    load_manifest()
                    st.rerun()
            with col2:
                if st.button("📥", help="Clone", use_container_width=True):
                    clone_message = "Use clone_wordpress_site_v2 to download all WordPress pages"
                    st.session_state.messages.append({"role": "user", "content": clone_message})
                    st.rerun()
        
        # Chat section - now gets much more space
        st.markdown("### 💬 Chat")
        
        # Debug section for agent status
        with st.expander("🔧 Debug Info", expanded=False):
            st.write(f"**Agent Status:** {'✅ Initialized' if st.session_state.agent is not None else '❌ Not Initialized'}")
            if st.session_state.agent is not None:
                st.write(f"**Agent Type:** {type(st.session_state.agent).__name__}")
            st.write(f"**Session Initialized:** {st.session_state.initialized}")
            st.write(f"**Current Page:** {st.session_state.current_page_id}")
            st.write(f"**Messages Count:** {len(st.session_state.messages)}")
            
            if st.button("🔄 Force Reinitialize Agent", help="Manually reinitialize the agent if it's broken"):
                st.session_state.agent = None
                st.session_state.memory_manager = None
                st.session_state.initialized = False
                st.info("Agent cleared. Page will refresh to reinitialize...")
                st.rerun()
        
        # Chat messages in a larger scrollable container
        chat_container = st.container(height=600)  # Much taller now
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-user">🗣️ <strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    # Check if this is an enhanced message with debug details
                    content = msg["content"]
                    if "<details>" in content:
                        # Split main response from debug details
                        if "<details>" in content:
                            main_response = content.split("<details>")[0].strip()
                            debug_section = "<details>" + content.split("<details>")[1]
                        else:
                            main_response = content
                            debug_section = ""
                        
                        # Display main response
                        st.markdown(f'<div class="chat-assistant">🤖 <strong>Assistant:</strong> {main_response}</div>', unsafe_allow_html=True)
                        
                        # Display expandable debug section if present
                        if debug_section:
                            st.markdown(f'<div class="chat-debug">{debug_section}</div>', unsafe_allow_html=True)
                    else:
                        # Regular assistant message
                        st.markdown(f'<div class="chat-assistant">🤖 <strong>Assistant:</strong> {content}</div>', unsafe_allow_html=True)
        
        # Compact chat input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area("Message:", placeholder="Try: 'Change background to blue'", height=80, label_visibility="collapsed")
            send_button = st.form_submit_button("📤 Send", use_container_width=True)
            
            if send_button and user_input:
                # Add user message immediately
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.rerun()  # Show user message immediately
        
        # Process streaming response if there's a new user message to process
        if (st.session_state.messages and 
            st.session_state.messages[-1]["role"] == "user" and 
            len([msg for msg in st.session_state.messages if msg["role"] == "assistant"]) < 
            len([msg for msg in st.session_state.messages if msg["role"] == "user"])):
            
            # Get the last user message
            last_user_message = st.session_state.messages[-1]["content"]
            
            # Show streaming response
            with st.spinner("🤖 Agent thinking..."):
                # Create streaming container
                streaming_container = st.empty()
                
                try:
                    # Critical safety check - ensure agent is not None
                    if st.session_state.agent is None:
                        st.error("❌ Agent is None! Cannot process message.")
                        st.error("Please refresh the page to reinitialize the agent.")
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": "❌ Error: Agent not properly initialized. Please refresh the page and try again."
                        })
                        st.rerun()
                        return
                    
                    # Use streaming to show real-time progress
                    response_content = ""
                    tool_calls_made = []
                    thinking_content = ""
                    final_messages = []
                    streaming_log = []  # Capture all streaming activity
                    
                    # Add context about local editing
                    context = f"[User is editing LOCAL page ID {st.session_state.current_page_id} in the cloned files] {last_user_message}"
                    context += "\nIMPORTANT: Use the filesystem tools (read_file, write_file, etc.) to make changes to the LOCAL files. Use wp_navigate_to_page to change which page is displayed."
                    
                    config = {
                        "configurable": {
                            "thread_id": st.session_state.session_id,
                            "user_id": "local_canvas_user"
                        },
                        "recursion_limit": 50  # Increased limit for reflection workflow
                    }
                    
                    # Stream the agent response with correct LangGraph format
                    chunk_count = 0
                    for chunk in st.session_state.agent.stream(
                        {"messages": [HumanMessage(content=context)]},
                        config=config,
                        stream_mode="updates"  # This is the key!
                    ):
                        chunk_count += 1
                        
                        # Log this step for preservation
                        step_log = {
                            "step": chunk_count,
                            "nodes": {},
                            "tool_calls": [],
                            "content": ""
                        }
                        
                        # Update display for each chunk
                        streaming_display = f'<div class="streaming-display">'
                        streaming_display += f"<h4>🤖 Agent Working (Step {chunk_count})</h4>"
                        
                        # Show the actual chunk data (node updates)
                        if chunk:
                            streaming_display += f'<div class="agent-response"><strong>🔄 Update:</strong><br>'
                            
                            # LangGraph chunks are dictionaries with node names as keys
                            for node_name, node_data in chunk.items():
                                streaming_display += f"<strong>{node_name}:</strong> "
                                
                                # Log node activity
                                step_log["nodes"][node_name] = str(node_data)[:500]
                                
                                # Handle different node data types
                                if hasattr(node_data, 'get') and 'messages' in node_data:
                                    # This is likely a messages update
                                    messages = node_data['messages']
                                    if messages:
                                        last_msg = messages[-1]
                                        if hasattr(last_msg, 'content'):
                                            content_preview = last_msg.content[:200]
                                            streaming_display += f"{content_preview}..."
                                            step_log["content"] = last_msg.content
                                            # Store for final response
                                            if hasattr(last_msg, 'type') and last_msg.type == 'ai':
                                                response_content = last_msg.content
                                        elif hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                            # Tool call message
                                            tool_calls = last_msg.tool_calls
                                            tool_call = f"🔧 {tool_calls[0]['name']}(...)"
                                            tool_calls_made.append(tool_call)
                                            step_log["tool_calls"].append({
                                                "name": tool_calls[0]['name'],
                                                "args": str(tool_calls[0].get('args', ''))[:200]
                                            })
                                            streaming_display += f"Tool call: {tool_call}"
                                        else:
                                            streaming_display += str(last_msg)[:100]
                                        
                                        # Keep track of final messages for response
                                        final_messages = messages
                                    else:
                                        streaming_display += "Empty messages"
                                else:
                                    # Other node data
                                    streaming_display += str(node_data)[:200]
                                
                                streaming_display += "<br>"
                            
                            streaming_display += '</div>'
                        
                        # Show accumulated tool calls
                        if tool_calls_made:
                            streaming_display += "<br><strong>📋 Tool Calls Made:</strong><br>"
                            for call in tool_calls_made[-3:]:  # Show last 3 tool calls
                                streaming_display += f'<div class="tool-call">{call}</div>'
                            if len(tool_calls_made) > 3:
                                streaming_display += f"<small>... and {len(tool_calls_made) - 3} more tool calls</small><br>"
                        
                        streaming_display += '<br><div style="text-align: center; color: #666;">⏳ <em>Processing...</em></div>'
                        streaming_display += '</div>'
                        
                        # Update the display immediately
                        streaming_container.markdown(streaming_display, unsafe_allow_html=True)
                        
                        # Add to streaming log
                        streaming_log.append(step_log)
                        
                        # Force immediate update with small delay
                        time.sleep(0.1)
                    
                    # Clear streaming display
                    streaming_container.empty()
                    
                    # Extract final response from the last messages
                    if final_messages:
                        ai_messages = [msg for msg in final_messages if hasattr(msg, 'type') and msg.type == 'ai']
                        if ai_messages:
                            response_content = ai_messages[-1].content
                    
                    # Create enhanced assistant message with expandable details
                    final_response = response_content if response_content else "Processing completed."
                    
                    # Create expandable debug section
                    debug_section = f"""
                    
<details>
<summary>🔍 <strong>View Process Details</strong> ({len(streaming_log)} steps)</summary>

**🔄 Step-by-Step Process:**
"""
                    
                    for step in streaming_log:
                        debug_section += f"""
**Step {step['step']}:**
"""
                        for node_name, node_data in step['nodes'].items():
                            debug_section += f"- **{node_name}:** {node_data[:200]}...\n"
                        
                        if step['tool_calls']:
                            tool_names = [tc['name'] for tc in step['tool_calls']]
                            debug_section += f"- **🔧 Tool Calls:** {', '.join(tool_names)}\n"
                            for tc in step['tool_calls']:
                                debug_section += f"  - {tc['name']}({tc['args'][:100]}...)\n"
                        
                        if step['content']:
                            debug_section += f"- **Content:** {step['content'][:100]}...\n"
                    
                    debug_section += """
</details>"""
                    
                    # Combine final response with debug section
                    enhanced_message = final_response + debug_section
                    
                    # Add enhanced response to chat
                    st.session_state.messages.append({"role": "assistant", "content": enhanced_message})
                    
                    # Check for navigation commands after agent response
                    navigation_occurred = check_navigation_commands()
                    
                    # Auto-refresh if content changed or navigation occurred
                    if any(word in final_response.lower() for word in ["updated", "changed", "added", "edited", "navigated"]) or navigation_occurred:
                        st.session_state.last_refresh = time.time()
                    
                except Exception as e:
                    streaming_container.empty()
                    error_msg = f"Error during streaming: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
                st.rerun()
    
    # RIGHT PANEL - Side-by-side page comparison
    with right_panel:
        if st.session_state.current_page_id and st.session_state.pages_list:
            # Show page info
            page_info = st.session_state.pages_list.get(str(st.session_state.current_page_id), {})
            if page_info:
                st.markdown(f"### 📝 {page_info.get('title', 'Unknown')} (ID: {st.session_state.current_page_id})")
            else:
                st.markdown(f"### 📝 Page {st.session_state.current_page_id}")
            
            # Side-by-side display of local vs clone
            local_col, clone_col = st.columns(2)
            
            with local_col:
                st.markdown("#### ✏️ **Local Version** (Working Copy)")
                render_local_html(st.session_state.current_page_id)
            
            with clone_col:
                st.markdown("#### 📄 **Clone Version** (WordPress Snapshot)")
                render_clone_html(st.session_state.current_page_id)
        else:
            # Welcome message when no page is selected
            st.markdown("""
            ## 🚀 Welcome to Local Website Editor
            
            ### 🎯 Quick Start:
            1. **📥 Clone** - Download pages from your website
            2. **🔍 Select Page** - Choose from dropdown on the left
            3. **💬 Chat** - Tell the AI what to change
            4. **📤 Deploy** - Deploy changes to Netlify when ready
            
            ### 💬 Example Commands:
            - "Show me page 21"
            - "Change the background to blue"
            - "Add a contact form"
            - "Make the text larger"
            - "Deploy this page to Netlify"
            """)

if __name__ == "__main__":
    main()