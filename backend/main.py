#!/usr/bin/env python3
"""
LangGraph Memory Agent Template

An advanced agent with sophisticated memory capabilities including both short-term
conversation memory and long-term semantic memory for persistent knowledge.
"""

import os
import sys
import uuid
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import requests
from requests.auth import HTTPBasicAuth
import hashlib
import re

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver  
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore

try:
    from backend.persistent_store import PersistentJSONStore
except ImportError:
    # Fallback for direct execution
    from persistent_store import PersistentJSONStore

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Anthropic support
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# LangSmith imports for tracing
try:
    from langsmith import traceable
    from langsmith.wrappers import wrap_openai
    # Anthropic models will be automatically traced by LangSmith when enabled
    import anthropic
    LANGSMITH_AVAILABLE = True
    print("🔍 LangSmith SDK imported successfully")
except ImportError as e:
    LANGSMITH_AVAILABLE = False
    print(f"⚠️  LangSmith import failed: {e}")
    # Create dummy decorators if LangSmith is not available
    def traceable(name: str = None, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def wrap_openai(client):
        return client

# Enhanced Task Completion Cache with Circuit Breaker
class TaskCompletionCache:
    """Tracks recently completed tasks to prevent unnecessary repetition"""
    
    def __init__(self):
        self.completed_tasks: Dict[str, Dict] = {}
        self.processed_messages: Set[str] = set()
        self.failed_operations: Dict[str, Dict] = {}  # Track failed operations
        
    def _normalize_request(self, content: str, page_id: str = "") -> str:
        """Normalize request content for better duplicate detection"""
        # Remove context prefixes and system instructions
        content = re.sub(r'\[User is editing LOCAL page ID \d+ in the cloned files\]', '', content)
        content = re.sub(r'IMPORTANT: Use the filesystem tools.*?displayed\.', '', content)
        
        # Normalize common variations
        content = content.lower().strip()
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        
        # Add page context for more specific matching
        return f"page_{page_id}:{content}"
    
    def _hash_content(self, content: str, page_id: str = "") -> str:
        """Create a hash of the normalized task content"""
        normalized = self._normalize_request(content, page_id)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def mark_completed(self, content: str, page_id: str = ""):
        """Mark a task as completed"""
        task_hash = self._hash_content(content, page_id)
        self.completed_tasks[task_hash] = {
            "content": content,
            "page_id": page_id,
            "normalized": self._normalize_request(content, page_id),
            "completed_at": datetime.now(),
            "count": self.completed_tasks.get(task_hash, {}).get("count", 0) + 1
        }
        print(f"📝 Cached completion: {self._normalize_request(content, page_id)[:50]}... (count: {self.completed_tasks[task_hash]['count']})")
    
    def is_recently_completed(self, content: str, page_id: str = "", within_minutes: int = 30) -> bool:
        """Check if this task was recently completed"""
        task_hash = self._hash_content(content, page_id)
        
        if task_hash in self.completed_tasks:
            completed_info = self.completed_tasks[task_hash]
            time_diff = datetime.now() - completed_info["completed_at"]
            
            if time_diff < timedelta(minutes=within_minutes):
                count = completed_info["count"]
                print(f"🔄 Duplicate detected: {completed_info['normalized'][:50]}... (completed {count} times recently)")
                return True
        
        return False
    
    def was_message_processed(self, message_content: str) -> bool:
        """Check if this exact message was already processed"""
        # Create a more specific hash that includes key parts but ignores timestamps
        clean_content = re.sub(r'\[User is editing LOCAL page ID \d+ in the cloned files\]', '[EDITING_PAGE]', message_content)
        clean_content = re.sub(r'IMPORTANT: Use the filesystem tools.*?displayed\.', '', clean_content)
        
        # IMPORTANT: Don't block push operations - they should be retryable
        if "push" in clean_content.lower() and any(keyword in clean_content.lower() for keyword in ["push_changes", "push all"]):
            print("🔄 Push operation detected - allowing retry (not blocking)")
            return False
        
        msg_hash = hashlib.md5(clean_content.encode()).hexdigest()
        if msg_hash in self.processed_messages:
            print(f"⚠️ Exact message already processed: {clean_content[:50]}...")
            return True
        
        self.processed_messages.add(msg_hash)
        # Keep only last 50 messages to prevent memory bloat
        if len(self.processed_messages) > 50:
            self.processed_messages = set(list(self.processed_messages)[-50:])
        
        return False
    
    def mark_failed_operation(self, content: str, page_id: str = "", error: str = ""):
        """Mark an operation as failed to prevent immediate retries"""
        task_hash = self._hash_content(content, page_id)
        self.failed_operations[task_hash] = {
            "content": content,
            "page_id": page_id,
            "failed_at": datetime.now(),
            "error": error,
            "count": self.failed_operations.get(task_hash, {}).get("count", 0) + 1
        }
        print(f"🚫 Circuit breaker: Marked operation as failed ({self.failed_operations[task_hash]['count']} times)")
    
    def is_recently_failed(self, content: str, page_id: str = "", within_minutes: int = 5) -> bool:
        """Check if this operation recently failed (circuit breaker)"""
        task_hash = self._hash_content(content, page_id)
        
        if task_hash in self.failed_operations:
            failed_info = self.failed_operations[task_hash]
            time_diff = datetime.now() - failed_info["failed_at"]
            
            if time_diff < timedelta(minutes=within_minutes):
                count = failed_info["count"]
                print(f"🚫 Circuit breaker: Operation recently failed {count} times - blocking retry")
                return True
        
        return False

# Global cache instance
task_cache = TaskCompletionCache()

def extract_page_id(content: str) -> str:
    """Extract page ID from message content"""
    page_match = re.search(r'LOCAL page ID (\d+)', content)
    return page_match.group(1) if page_match else ""

# Environment setup
def load_environment():
    """Load environment variables and validate required keys."""
    # Load environment variables from .env file
    load_dotenv()
    
    # At least one model provider API key is required
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    if not (has_openai or has_anthropic):
        raise ValueError("At least one model provider API key is required: OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    if has_openai:
        print("✅ OpenAI API key found")
    if has_anthropic and ANTHROPIC_AVAILABLE:
        print("✅ Anthropic API key found")
    elif has_anthropic and not ANTHROPIC_AVAILABLE:
        print("⚠️  ANTHROPIC_API_KEY found but langchain-anthropic package not installed")
        print("   Install with: pip install langchain-anthropic")
    
    # Setup LangSmith tracing if available
    setup_langsmith_tracing()

def setup_langsmith_tracing():
    """Configure LangSmith tracing if environment variables are set."""
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    
    if not langsmith_api_key:
        print("ℹ️  LangSmith tracing disabled (no LANGSMITH_API_KEY found)")
        return
        
    if not LANGSMITH_AVAILABLE:
        print("⚠️  LANGSMITH_API_KEY found but langsmith package not available")
        print("   Install with: pip install langsmith")
        return
        
    try:
        # Enable tracing
        os.environ["LANGSMITH_TRACING"] = "true"
        
        # Set endpoint (defaults to main US endpoint)
        if not os.getenv("LANGSMITH_ENDPOINT"):
            os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
        
        # Set project name if not already set
        if not os.getenv("LANGSMITH_PROJECT"):
            os.environ["LANGSMITH_PROJECT"] = "Web Design Agent"
        
        print("✅ LangSmith tracing enabled")
        print(f"   Project: {os.getenv('LANGSMITH_PROJECT')}")
        print(f"   Endpoint: {os.getenv('LANGSMITH_ENDPOINT')}")
        print(f"   API Key: {langsmith_api_key[:8]}...")
        
    except Exception as e:
        print(f"⚠️  LangSmith tracing setup failed: {e}")
        print("   Continuing without tracing...")

def get_model(model_name: str = "auto", temperature: float = 0.1):
    """Get the appropriate model based on available API keys and preferences."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY")) and ANTHROPIC_AVAILABLE
    
    if model_name == "auto":
        # Auto-select based on available keys, prefer Claude Sonnet 4 if available
        if has_anthropic:
            model_name = "claude-sonnet-4-20250514"
        elif has_openai:
            model_name = "gpt-4o-mini"
        else:
            raise ValueError("No model provider API keys available")
    
    # Create the appropriate model
    if model_name.startswith("claude"):
        if not has_anthropic:
            raise ValueError("Anthropic API key required for Claude models")
        model = ChatAnthropic(model=model_name, temperature=temperature)
        print(f"✅ Using Anthropic model: {model_name}")
        
        # Wrap with LangSmith tracing if available
        if LANGSMITH_AVAILABLE and os.getenv("LANGSMITH_API_KEY"):
            try:
                # LangChain models are automatically traced by LangSmith when enabled
                print("   🔍 LangSmith tracing enabled for Anthropic")
            except Exception as e:
                print(f"   ⚠️  LangSmith tracing setup failed: {e}")
        
    elif model_name.startswith("gpt"):
        if not has_openai:
            raise ValueError("OpenAI API key required for GPT models")
        model = ChatOpenAI(model=model_name, temperature=temperature)
        print(f"✅ Using OpenAI model: {model_name}")
        
        # Wrap with LangSmith tracing if available
        if LANGSMITH_AVAILABLE and os.getenv("LANGSMITH_API_KEY"):
            try:
                # LangChain models are automatically traced by LangSmith when enabled
                print("   🔍 LangSmith tracing enabled for OpenAI")
            except Exception as e:
                print(f"   ⚠️  LangSmith tracing setup failed: {e}")
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    
    return model

class MemoryManager:
    """Manages both short-term and long-term memory for the agent."""
    
    def __init__(self, store: BaseStore, embeddings: OpenAIEmbeddings):
        self.store = store
        self.embeddings = embeddings
    
    def create_memory(self, user_id: str, content: str, memory_type: str = "general", importance: int = 5) -> str:
        """Create a new memory entry."""
        memory_id = str(uuid.uuid4())
        namespace = ("memories", user_id)
        
        memory_data = {
            "content": content,
            "type": memory_type,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed": datetime.now().isoformat()
        }
        
        self.store.put(namespace, memory_id, memory_data)
        return memory_id
    
    def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant memories using semantic similarity."""
        namespace = ("memories", user_id)
        
        try:
            results = self.store.search(namespace, query=query, limit=limit)
            
            # Update access counts
            for result in results:
                memory_data = result.value
                memory_data["access_count"] = memory_data.get("access_count", 0) + 1
                memory_data["last_accessed"] = datetime.now().isoformat()
                self.store.put(namespace, result.key, memory_data)
            
            return [{"id": r.key, **r.value} for r in results]
        except Exception as e:
            print(f"Memory search error: {e}")
            return []
    
    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        namespace = ("memories", user_id)
        
        try:
            # Get all memories (this is a simplified approach)
            # In a real implementation, you'd want pagination
            memories = []
            results = self.store.search(namespace, query="", limit=100)
            return [{"id": r.key, **r.value} for r in results]
        except Exception:
            return []
    
    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        namespace = ("memories", user_id)
        
        try:
            self.store.delete(namespace, memory_id)
            return True
        except Exception:
            return False

def create_memory_tools(memory_manager: MemoryManager):
    """Create tools for memory management."""
    
    @tool
    def remember_information(information: str, memory_type: str = "general", importance: int = 5) -> str:
        """Store important information in long-term memory.
        
        Args:
            information: The information to remember
            memory_type: Type of memory (personal, preference, fact, etc.)
            importance: Importance level 1-10 (higher = more important)
        """
        # This will be populated with user_id from config in the agent
        return f"I'll remember: {information}"
    
    @tool
    def recall_information(query: str) -> str:
        """Search for relevant information in long-term memory.
        
        Args:
            query: What to search for in memory
        """
        return f"Searching memory for: {query}"
    
    @tool
    def list_memories(memory_type: str = "all") -> str:
        """List stored memories, optionally filtered by type.
        
        Args:
            memory_type: Filter by memory type (or 'all' for everything)
        """
        return f"Listing memories of type: {memory_type}"
    
    return [remember_information, recall_information, list_memories]

def create_wordpress_tools():
    """Create tools for WordPress API interaction."""
    # Import all WordPress tools from the comprehensive module
    try:
        from backend.wordpress_tools import get_all_wordpress_tools
        from backend.visual_editor_tools import (
            wp_add_custom_css_to_page,
            wp_add_content_block_to_page,
            wp_get_page_structure,
            wp_update_page_section
        )
        from backend.navigation_tools import (
            wp_navigate_to_page,
            wp_create_blank_page,
            wp_list_all_pages,
            wp_add_page_to_menu
        )
        from backend.disable_coming_soon_tool import wp_disable_coming_soon_mode
        from backend.filesystem_tools import (
            read_file,
            write_file,
            append_file,
            delete_file,
            copy_file,
            move_file,
            create_directory,
            delete_directory,
            list_directory,
            get_file_info,
            search_files,
            delete_local_page,
            restore_local_page_from_wordpress,
            get_allowed_directories,
            add_page_to_manifest,
            rebuild_manifest_from_files,
            update_page_title_in_manifest,
            create_local_page,
            refresh_streamlit_interface,
            get_change_log,
            mark_changes_as_pushed,
            clear_change_log,
            push_changes_to_wordpress,
            check_wordpress_sync_status,
            clone_wordpress_site_locally,
            debug_sync_comparison,
            migrate_to_v2_sync_system,
            clone_wordpress_site_v2,
            check_sync_status_v2,
            show_page_diff_v2,
            push_changes_v2,
            force_overwrite_from_wordpress,
            get_clone_history_v2,
            restore_from_clone_v2,
            verify_work_quality
        )
    except ImportError:
        # Fallback for direct execution
        from wordpress_tools import get_all_wordpress_tools
        from visual_editor_tools import (
            wp_add_custom_css_to_page,
            wp_add_content_block_to_page,
            wp_get_page_structure,
            wp_update_page_section
        )
        from navigation_tools import (
            wp_navigate_to_page,
            wp_create_blank_page,
            wp_list_all_pages,
            wp_add_page_to_menu
        )
        from disable_coming_soon_tool import wp_disable_coming_soon_mode
        from filesystem_tools import (
            read_file,
            write_file,
            append_file,
            delete_file,
            copy_file,
            move_file,
            create_directory,
            delete_directory,
            list_directory,
            get_file_info,
            search_files,
            delete_local_page,
            restore_local_page_from_wordpress,
            get_allowed_directories,
            add_page_to_manifest,
            rebuild_manifest_from_files,
            update_page_title_in_manifest,
            create_local_page,
            refresh_streamlit_interface,
            get_change_log,
            mark_changes_as_pushed,
            clear_change_log,
            push_changes_to_wordpress,
            check_wordpress_sync_status,
            clone_wordpress_site_locally,
            debug_sync_comparison,
            migrate_to_v2_sync_system,
            clone_wordpress_site_v2,
            check_sync_status_v2,
            show_page_diff_v2,
            push_changes_v2,
            force_overwrite_from_wordpress,
            get_clone_history_v2,
            restore_from_clone_v2,
            verify_work_quality
        )
    
    # Combine all tools
    wordpress_tools = get_all_wordpress_tools()
    visual_tools = [
        wp_add_custom_css_to_page,
        wp_add_content_block_to_page,
        wp_get_page_structure,
        wp_update_page_section
    ]
    navigation_tools = [
        wp_navigate_to_page,
        wp_create_blank_page,
        wp_list_all_pages,
        wp_add_page_to_menu
    ]
    filesystem_tools = [
        read_file,
        write_file,
        append_file,
        delete_file,
        copy_file,
        move_file,
        create_directory,
        delete_directory,
        list_directory,
        get_file_info,
        search_files,
        delete_local_page,
        restore_local_page_from_wordpress,
        get_allowed_directories,
        add_page_to_manifest,
        rebuild_manifest_from_files,
        update_page_title_in_manifest,
        create_local_page,
        refresh_streamlit_interface,
        get_change_log,
        mark_changes_as_pushed,
        clear_change_log,
        push_changes_to_wordpress,
        check_wordpress_sync_status,
        clone_wordpress_site_locally,
        debug_sync_comparison,
        migrate_to_v2_sync_system,
        clone_wordpress_site_v2,
        check_sync_status_v2,
        show_page_diff_v2,
        push_changes_v2,
        force_overwrite_from_wordpress,
        get_clone_history_v2,
        restore_from_clone_v2,
        verify_work_quality
    ]
    
    utility_tools = [wp_disable_coming_soon_mode]
    
    return wordpress_tools + visual_tools + navigation_tools + filesystem_tools + utility_tools

def create_memory_agent_system(use_sqlite: bool = False, model_name: str = "auto"):
    """Create and configure the memory agent system."""
    load_environment()
    
    # Initialize components
    model = get_model(model_name)
    embeddings = OpenAIEmbeddings()
    
    # Handle checkpointer properly
    checkpointer = None
    if use_sqlite:
        try:
            # Create database directory if it doesn't exist
            db_path = "memory_agent.db"
            
            # Use the context manager properly or create the checkpointer directly
            try:
                # Try the direct approach first
                from langgraph.checkpoint.sqlite import SqliteSaver
                import sqlite3
                
                # Create connection and pass it to SqliteSaver
                conn = sqlite3.connect(db_path, check_same_thread=False)
                checkpointer = SqliteSaver(conn)
                print(f"✅ Using SQLite persistence ({db_path})")
                
            except Exception as e:
                print(f"⚠️ SQLite checkpointer failed: {e}")
                print("   Falling back to in-memory persistence")
                checkpointer = MemorySaver()
                
        except Exception as e:
            print(f"⚠️ Checkpointer setup failed: {e}")
            print("   Using in-memory persistence")
            checkpointer = MemorySaver()
    else:
        # Use in-memory for LangGraph Studio compatibility
        checkpointer = MemorySaver()
        print("✅ Using in-memory persistence")
    
    # Set up long-term memory store
    store = InMemoryStore()
    memory_manager = MemoryManager(store, embeddings)
    
    # Create memory tools
    memory_tools = create_memory_tools(memory_manager)
    
    @traceable(name="Memory Agent Node", run_type="chain")
    def memory_agent_node(state: MessagesState, config: RunnableConfig, *, store: BaseStore):
        """Memory-enhanced agent node."""
        user_id = config["configurable"].get("user_id", "default_user")
        namespace = ("memories", user_id)
        
        # Get the latest user message
        messages = state["messages"]
        if not messages:
            return {"messages": []}
        
        last_message = messages[-1]
        
        # Search for relevant memories
        if last_message.type == "human":
            relevant_memories = memory_manager.search_memories(user_id, last_message.content, limit=3)
            
            # Build context from memories
            memory_context = ""
            if relevant_memories:
                memory_context = "\\n\\nRelevant memories:\\n"
                for memory in relevant_memories:
                    memory_context += f"- {memory['content']} (created: {memory['created_at'][:10]})\\n"
            
            # Check if user wants to remember something
            remember_keywords = ["remember", "save", "store", "don't forget"]
            if any(keyword in last_message.content.lower() for keyword in remember_keywords):
                # Extract what to remember (simplified - in practice you'd use more sophisticated NLP)
                content_to_remember = last_message.content
                memory_id = memory_manager.create_memory(
                    user_id=user_id,
                    content=content_to_remember,
                    memory_type="user_request",
                    importance=7
                )
                memory_context += f"\\n[Stored in memory: {content_to_remember}]"
            
            # Create system message with memory context
            system_content = f"""You are an AI assistant with advanced memory capabilities.

Your memory features:
- You can remember information across conversations
- You have access to relevant memories from past interactions
- You can store new information when asked

Memory context for this conversation:{memory_context}

Guidelines:
- Reference relevant memories when helpful
- Offer to remember important information
- Be transparent about what you remember
- Ask clarifying questions about memory preferences"""

            # Prepare messages for the model
            if messages[0].type != "system":
                model_messages = [SystemMessage(content=system_content)] + messages
            else:
                model_messages = [SystemMessage(content=system_content)] + messages[1:]
        else:
            model_messages = messages
        
        # Generate response
        response = model.invoke(model_messages)
        return {"messages": [response]}
    
    # Build the graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("memory_agent", memory_agent_node)
    workflow.add_edge(START, "memory_agent")
    
    # Compile with memory capabilities - use robust compilation
    try:
        if checkpointer:
            agent = workflow.compile(
                checkpointer=checkpointer,
                store=store
            )
        else:
            agent = workflow.compile(store=store)
        
        print("✅ Memory agent created successfully!")
        return agent, memory_manager
        
    except Exception as e:
        print(f"❌ Error compiling memory agent workflow: {e}")
        print("   Trying without checkpointer...")
        
        # Fallback: compile without checkpointer
        agent = workflow.compile(store=store)
        print("✅ Memory agent created successfully (no persistence)!")
        return agent, memory_manager

def create_wordpress_memory_agent(use_sqlite: bool = False, model_name: str = "auto"):
    """Create an advanced agent with WordPress capabilities and memory.
    
    Args:
        use_sqlite: Whether to use SQLite for checkpointing (default: False for Studio)
        model_name: Model to use ("auto", "openai", "anthropic", or specific model name)
    
    Returns:
        Tuple of (agent, memory_manager)
    """
    setup_langsmith_tracing()
    
    model = get_model(model_name)
    embeddings = OpenAIEmbeddings()
    
    # Create memory store
    store = InMemoryStore()
    memory_manager = MemoryManager(store, embeddings)
    
    # Enhanced memory tools with actual implementation
    @tool
    @traceable(name="Remember Information", run_type="tool")
    def remember_info(information: str, memory_type: str = "general") -> str:
        """Store information in long-term memory."""
        user_id = "demo_user"
        memory_id = memory_manager.create_memory(user_id, information, memory_type)
        return f"✅ Remembered: {information}"
    
    @tool
    @traceable(name="Search Memory", run_type="tool")
    def search_memory(query: str) -> str:
        """Search through stored memories."""
        user_id = "demo_user"
        memories = memory_manager.search_memories(user_id, query, limit=3)
        
        if not memories:
            return "No relevant memories found."
        
        result = "Found relevant memories:\\n"
        for memory in memories:
            result += f"- {memory['content']}\\n"
        return result
    
    @tool
    @traceable(name="List All Memories", run_type="tool")
    def list_all_memories() -> str:
        """List all stored memories."""
        user_id = "demo_user"
        memories = memory_manager.get_all_memories(user_id)
        
        if not memories:
            return "No memories stored yet."
        
        result = f"Stored memories ({len(memories)} total):\\n"
        for memory in memories:
            result += f"- {memory['content']} (type: {memory['type']})\\n"
        return result
    
    # Combine memory tools with WordPress tools
    memory_tools = [remember_info, search_memory, list_all_memories]
    wordpress_tools = create_wordpress_tools()
    tools = memory_tools + wordpress_tools
    
    system_prompt = """You are an AI assistant with memory and comprehensive website management capabilities, including visual editing and direct filesystem access.

NETLIFY DEPLOYMENT STRUCTURE - MEMORIZE THIS:
- Local files location: `wordpress_clone/pages/page_X/`
- Each page has: `index.html` (working copy), `metadata.json`
- Deploy location: `deploy/public/` (Git-deployed to Netlify)
- NEVER try `wordpress_clone/page_X/` - always use `wordpress_clone/pages/page_X/`

NETLIFY DEPLOYMENT WORKFLOW:
- "Create a page" = Create LOCAL files only (index.html, metadata.json) 
- "Deploy to Netlify" = Use deploy_page_to_netlify or deploy_all_to_netlify
- "Push" or "publish" = Deploy to Netlify (not WordPress)
- Local files can have complete HTML with beautiful CSS - Netlify handles it perfectly!

IMPORTANT DEPLOYMENT COMMANDS:
- deploy_page_to_netlify(page_id) - Deploy a specific page to Netlify
- deploy_all_to_netlify() - Deploy all pages to Netlify  
- check_netlify_deploy_status() - Check deployment status

LOCAL FILE MANAGEMENT:
- Use read_file, write_file to edit `wordpress_clone/pages/page_X/index.html`
- Create complete HTML documents with full CSS styling
- No size limits - Netlify handles large styled pages perfectly
- Use wp_navigate_to_page to change which page is displayed in the local interface

STYLING APPROACH:
- Create beautiful, complete HTML documents with embedded CSS
- Use modern CSS features: flexbox, grid, animations, CSS variables
- No WordPress limitations - you have complete creative control
- Local files ARE the production files (copied to Netlify exactly as-is)

When user says "push changes" or "deploy", use the Netlify deployment tools, not WordPress tools."""

    # Define the workflow state
    from typing import TypedDict, Annotated, List
    from langgraph.graph.message import add_messages
    from langchain_core.messages import BaseMessage
    
    class WorkflowState(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]
        original_request: str  # Store the original user request for reflection
        current_page_id: str   # Track which page is being edited
        needs_reflection: bool # Flag to trigger reflection
        has_reflected: bool    # Flag to track if we've already reflected
        correction_attempted: bool # Flag to track if we've attempted corrections
        is_duplicate: bool     # Flag to mark duplicate requests
    
    @traceable(name="Main Agent Node", run_type="chain")
    def agent_node(state: WorkflowState):
        """Main agent node that processes user requests and makes changes."""
        global task_cache
        messages = state["messages"]
        
        # Get the current user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.type == "human":
                last_user_msg = msg.content
                break
        
        if not last_user_msg:
            return {"messages": []}
        
        # Extract page ID if present
        page_id = ""
        page_match = re.search(r'LOCAL page ID (\d+)', last_user_msg)
        if page_match:
            page_id = page_match.group(1)
        
        # Check for duplicates BEFORE processing
        if task_cache.was_message_processed(last_user_msg):
            return {
                "messages": [AIMessage(content="⚠️ This exact request was just processed. If you need something different, please clarify your request.")],
                "is_duplicate": True,
                "needs_reflection": False
            }
        
        # Check if this task was recently completed
        if task_cache.is_recently_completed(last_user_msg, page_id):
            completion_info = task_cache.completed_tasks.get(task_cache._hash_content(last_user_msg, page_id), {})
            count = completion_info.get("count", 0)
            
            return {
                "messages": [AIMessage(content=f"✅ This task appears to have been completed recently ({count} times). The work was already done. If you need something different or want to make additional changes, please provide a more specific request.")],
                "is_duplicate": True,
                "needs_reflection": False
            }
        
        # Circuit breaker: Check if this operation recently failed
        if task_cache.is_recently_failed(last_user_msg, page_id):
            return {
                "messages": [AIMessage(content="🚫 This operation recently failed multiple times. Please wait a few minutes before retrying, or try a different approach.")],
                "is_duplicate": True,
                "needs_reflection": False
            }
        
        # Process normally if not a duplicate
        agent = create_react_agent(
            model, 
            tools,
            prompt=system_prompt
        )
        
        # Process with agent
        try:
            response = agent.invoke({"messages": messages})
            
            # Mark this task as completed only if it succeeded
            task_cache.mark_completed(last_user_msg, page_id)
            
            # Determine if we're processing after reflection
            is_post_reflection = state.get("has_reflected", False)
            
            # Disable reflection for now to reduce token usage - can re-enable later
            needs_reflection = False
            # if last_user_msg and not is_post_reflection:
            #     # Only trigger reflection for initial editing requests, not corrections or duplicates
            #     editing_keywords = ["change", "edit", "modify", "update", "add", "remove", "rewrite", "fix", "make"]
            #     if any(keyword in last_user_msg.lower() for keyword in editing_keywords):
            #         needs_reflection = True
            
            return {
                "messages": response["messages"],
                "original_request": last_user_msg or "",
                "needs_reflection": needs_reflection,
                "correction_attempted": is_post_reflection,
                "is_duplicate": False
            }
            
        except Exception as e:
            # Mark this operation as failed to prevent immediate retries
            task_cache.mark_failed_operation(last_user_msg, page_id, str(e))
            
            return {
                "messages": [AIMessage(content=f"❌ Operation failed: {str(e)}. This has been logged to prevent immediate retries.")],
                "is_duplicate": False,
                "needs_reflection": False
            }
    
    @traceable(name="Reflection Node", run_type="chain")
    def reflection_node(state: WorkflowState):
        """Reflection node that reviews completed work and ensures quality."""
        
        # Only run reflection if we haven't already reflected and it's needed
        if state.get("has_reflected", False) or not state.get("needs_reflection", False):
            return {"needs_reflection": False}
        
        messages = state["messages"]
        original_request = state.get("original_request", "")
        current_page_id = state.get("current_page_id", "")
        
        # Don't reflect on duplicate requests
        if state.get("is_duplicate", False):
            return {
                "needs_reflection": False, 
                "has_reflected": True
            }
        
        # Get the last few messages for context
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Determine the scope of the request for better verification
        scope_analysis = ""
        request_lower = original_request.lower()
        
        if any(keyword in request_lower for keyword in ["push all", "clone site", "sync status", "check sync", "refresh", "clear"]):
            scope_analysis = f"""
**REQUEST SCOPE: GLOBAL OPERATION**
This is a system-wide operation, not limited to page {current_page_id}.
SUCCESS CRITERIA: Operation should complete successfully regardless of which specific pages are affected.
"""
        elif any(keyword in request_lower for keyword in ["this page", "current page", "page " + current_page_id]):
            scope_analysis = f"""
**REQUEST SCOPE: PAGE-SPECIFIC OPERATION**
This operation is specifically about page {current_page_id}.
SUCCESS CRITERIA: Changes should be applied to page {current_page_id} only.
"""
        else:
            # Ambiguous - check for visual terms that suggest page-specific
            if any(keyword in request_lower for keyword in ["background", "color", "font", "text", "add", "remove", "change"]):
                scope_analysis = f"""
**REQUEST SCOPE: LIKELY PAGE-SPECIFIC**
This appears to be a visual/content change, likely for page {current_page_id}.
SUCCESS CRITERIA: Changes should be applied to the relevant page(s).
"""
            else:
                scope_analysis = f"""
**REQUEST SCOPE: UNCLEAR - ANALYZE RESULTS**
Determine from the results whether this was intended as page-specific or global.
SUCCESS CRITERIA: Operation should match the apparent intent based on the request type.
"""
        
        reflection_prompt = f"""
🔍 **REFLECTION & VERIFICATION:**

{scope_analysis}

Original request: {original_request}
Page being edited: {current_page_id}

**Assessment:** Please review if the changes made match the original request. If not, make the necessary corrections immediately.

IMPORTANT VERIFICATION RULES:
1. For GLOBAL operations (like "push all changes"): Success if the operation completed properly, regardless of current page
2. For PAGE-SPECIFIC operations: Success if changes were applied to the intended page(s)  
3. Don't flag global operations as errors just because they didn't modify the current page
4. Look at the actual operation type and results to determine success
"""
        
        reflection_message = HumanMessage(content=reflection_prompt)
        
        try:
            # Create reflection config with recursion limit
            config_copy = config.copy() if config else {}
            config_copy.update({
                "recursion_limit": 50
            })
            
            reflection_result = agent.invoke(
                {"messages": recent_messages + [reflection_message]}, 
                config=config_copy
            )
            
            new_messages = reflection_result.get("messages", [])
            
            return {
                "messages": new_messages,
                "needs_reflection": False,
                "has_reflected": True
            }
            
        except Exception as e:
            # If reflection fails, continue without it
            error_message = AIMessage(content=f"⚠️ Reflection could not be completed: {str(e)}")
            return {
                "messages": [error_message],
                "needs_reflection": False,
                "has_reflected": True
            }
    
    def should_reflect(state: WorkflowState) -> str:
        """Conditional edge: decide whether to reflect or end."""
        # Skip reflection for duplicates
        if state.get("is_duplicate", False):
            return "end"
        
        # Only reflect once per request to avoid infinite loops
        if state.get("needs_reflection", False) and not state.get("has_reflected", False):
            return "reflect"
        return "end"
    
    def should_continue_after_reflection(state: WorkflowState) -> str:
        """Conditional edge: after reflection, go back to agent for corrections."""
        # Mark that we've reflected and only allow one correction cycle
        if not state.get("correction_attempted", False):
            return "agent"
        return "end"
    
    # Build the workflow graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("reflect", reflection_node)
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_reflect,
        {"reflect": "reflect", "end": END}
    )
    workflow.add_conditional_edges(
        "reflect", 
        should_continue_after_reflection,
        {"agent": "agent"}
    )
    
    # Handle checkpointer properly
    checkpointer = None
    if use_sqlite:
        try:
            # Create database directory if it doesn't exist
            db_path = "memory_agent.db"
            
            # Use the context manager properly or create the checkpointer directly
            try:
                # Try the direct approach first
                from langgraph.checkpoint.sqlite import SqliteSaver
                import sqlite3
                
                # Create connection and pass it to SqliteSaver
                conn = sqlite3.connect(db_path, check_same_thread=False)
                checkpointer = SqliteSaver(conn)
                print(f"✅ Using SQLite persistence ({db_path})")
                
            except Exception as e:
                print(f"⚠️ SQLite checkpointer failed: {e}")
                print("   Falling back to in-memory persistence")
                checkpointer = MemorySaver()
                
        except Exception as e:
            print(f"⚠️ Checkpointer setup failed: {e}")
            print("   Using in-memory persistence")
            checkpointer = MemorySaver()
    else:
        # Use in-memory for LangGraph Studio compatibility
        checkpointer = MemorySaver()
        print("✅ Using in-memory persistence")
    
    # Compile the graph
    try:
        if checkpointer:
            agent = workflow.compile(checkpointer=checkpointer)
        else:
            agent = workflow.compile()
        
        print("✅ WordPress Memory Agent created successfully!")
        return agent, memory_manager
        
    except Exception as e:
        print(f"❌ Error compiling workflow: {e}")
        print("   Trying without checkpointer...")
        
        # Fallback: compile without checkpointer
        agent = workflow.compile()
        print("✅ WordPress Memory Agent created successfully (no persistence)!")
        return agent, memory_manager

def run_conversation(use_sqlite: bool = False, model_name: str = "auto"):
    """Run an interactive conversation with the WordPress memory agent."""
    # Always use the tool-based agent with WordPress capabilities
    agent, memory_manager = create_wordpress_memory_agent(use_sqlite, model_name)
    
    print("🧠 WordPress Memory Agent initialized with duplicate prevention!")
    print()
    print("💾 Memory capabilities:")
    print("   - Remembers information across conversations")
    print("   - Can search through past memories")
    print("   - Learns your preferences over time")
    print("   - 🚫 Prevents duplicate task processing")
    print()
    print("🌐 WordPress capabilities:")
    print("   - Create, update, and delete posts/pages")
    print("   - Manage media, categories, and tags")
    print("   - Moderate comments and manage users")
    print("   - Update site settings and search content")
    print()
    print("💡 Try saying things like:")
    print("   - 'Remember that I like coffee in the morning'")
    print("   - 'What do you remember about my preferences?'")
    print("   - 'Create a new draft post about web development'")
    print("   - 'Show me all draft posts'")
    print("   - 'Update the site title to My Awesome Site'")
    print("   - 'Get recent comments for moderation'")
    print("   - 'Search for posts about WordPress'")
    print("Type 'memories' to see all stored memories")
    print("Type 'quit' to exit")
    print()
    
    # Configuration for memory persistence
    config = {
        "configurable": {
            "thread_id": "memory_conversation",
            "user_id": "user_123"
        },
        "recursion_limit": 50  # Increased limit for reflection workflow
    }
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye! I'll remember our conversation.")
                break
            
            if user_input.lower() == 'memories':
                memories = memory_manager.get_all_memories("user_123")
                if memories:
                    print("\\n📋 Stored Memories:")
                    for i, memory in enumerate(memories, 1):
                        print(f"{i}. {memory['content']} (type: {memory['type']})")
                else:
                    print("📋 No memories stored yet.")
                print()
                continue
                
            if not user_input:
                continue
            
            # Invoke the memory agent
            response = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )
            
            # Get the last message from the agent
            last_message = response["messages"][-1]
            print(f"Assistant: {last_message.content}")
            print()
            
        except KeyboardInterrupt:
            print("\\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

def run_example(model_name: str = "auto"):
    """Run predefined examples to demonstrate WordPress and memory capabilities."""
    agent, memory_manager = create_wordpress_memory_agent(model_name=model_name)
    
    print("🧠 Running WordPress Memory Agent Examples...")
    print("=" * 50)
    
    config = {
        "configurable": {
            "thread_id": "memory_example",
            "user_id": "example_user"
        },
        "recursion_limit": 50  # Increased limit for reflection workflow
    }
    
    # Example conversation showing memory capabilities
    examples = [
        "Hi! My name is Sarah and I'm a data scientist.",
        "I love working with Python and machine learning.",
        "Remember that I prefer morning meetings and work best with visual data.",
        "What do you remember about me?",
        "I'm working on a new project involving neural networks.",
        "Based on what you know about me, what tools might be helpful for my neural network project?"
    ]
    
    for i, message in enumerate(examples, 1):
        print(f"👤 User: {message}")
        
        try:
            response = agent.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )
            
            last_message = response["messages"][-1]
            print(f"🤖 Assistant: {last_message.content}")
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("-" * 40)
    
    # Show stored memories
    print("\\n📋 Final Memory State:")
    memories = memory_manager.get_all_memories("example_user")
    for i, memory in enumerate(memories, 1):
        print(f"{i}. {memory['content']}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    use_sqlite = False
    model_name = "auto"
    command = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i].lower()
        
        if arg == "example":
            command = "example"
        elif arg == "sqlite":
            use_sqlite = True
        elif arg.startswith("--model="):
            model_name = arg.split("=", 1)[1]
        elif arg == "--model" and i + 1 < len(sys.argv):
            model_name = sys.argv[i + 1]
            i += 1
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)
        i += 1
    
    # Display usage information
    print("🚀 Web Design Agent with LangSmith Tracing")
    print("=" * 50)
    print()
    
    if command == "example":
        run_example(model_name)
    else:
        print("💡 Available models:")
        print("   auto                       - Auto-select based on available API keys (prefers Claude Sonnet 4)")
        print("   claude-sonnet-4-20250514   - Claude Sonnet 4 (latest)")
        print("   claude-3-5-sonnet-20241022 - Claude 3.5 Sonnet") 
        print("   claude-3-5-haiku-20241022  - Claude 3.5 Haiku (fastest)")
        print("   gpt-4o-mini               - GPT-4o Mini")
        print("   gpt-4o                    - GPT-4o")
        print("   gpt-4-turbo              - GPT-4 Turbo")
        print()
        print("💻 Usage examples:")
        print("   python main.py                              # Use auto-selected model")
        print("   python main.py --model=claude-sonnet-4-20250514   # Use Claude Sonnet 4")
        print("   python main.py --model=gpt-4o-mini         # Use GPT-4o Mini")
        print("   python main.py sqlite                      # Use SQLite persistence")
        print("   python main.py example --model=claude-sonnet-4-20250514  # Run examples with Claude Sonnet 4")
        print()
        
        run_conversation(use_sqlite, model_name)