#!/usr/bin/env python3
"""
LangGraph Studio Entry Point for Web Design Agent

This file exports the compiled graph for LangGraph Studio to use.
The graph includes WordPress management, memory capabilities, and visual editing.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Set
import hashlib

# Add the current directory to the path so backend imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the necessary components directly
from backend.main import (
    load_environment, 
    get_model, 
    MemoryManager, 
    create_wordpress_tools,
    setup_langsmith_tracing
)
from backend.persistent_store import PersistentJSONStore
from langgraph.store.memory import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# LangSmith imports for tracing
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(name: str = None, **kwargs):
        def decorator(func):
            return func
        return decorator

# Simple Task Completion Cache with Circuit Breaker
class TaskCompletionCache:
    """Tracks recently completed tasks to prevent unnecessary repetition"""
    
    def __init__(self):
        self.completed_tasks: Dict[str, Dict] = {}
        self.processed_messages: Set[str] = set()
        self.failed_operations: Dict[str, Dict] = {}  # Track failed operations
        
    def _normalize_request(self, content: str, page_id: str = "") -> str:
        """Normalize request content for better duplicate detection"""
        import re
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
        import re
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

# Global cache instance
task_cache = TaskCompletionCache()

# Environment setup for LangGraph Studio
def setup_environment():
    """Ensure environment is properly configured for studio."""
    load_environment()
    setup_langsmith_tracing()

# Create the WordPress memory agent without checkpointer for Studio
def create_studio_agent():
    """Create the WordPress memory agent specifically for LangGraph Studio.
    
    This version creates the agent WITHOUT a checkpointer since LangGraph Studio
    handles persistence automatically.
    """
    setup_environment()
    
    model = get_model("auto")
    embeddings = OpenAIEmbeddings()
    
    # Use in-memory store (Studio will handle external persistence)
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
        
        # Extract page ID if present - use the global function
        page_id = extract_page_id(last_user_msg)
        
        # Check for duplicates BEFORE processing
        if task_cache.was_message_processed(last_user_msg):
            return {
                "messages": [HumanMessage(content="⚠️ This exact request was just processed. If you need something different, please clarify your request.")],
                "is_duplicate": True,
                "needs_reflection": False
            }
        
        # Check if this task was recently completed
        if task_cache.is_recently_completed(last_user_msg, page_id):
            completion_info = task_cache.completed_tasks.get(task_cache._hash_content(last_user_msg, page_id), {})
            count = completion_info.get("count", 0)
            
            return {
                "messages": [HumanMessage(content=f"✅ This task appears to have been completed recently ({count} times). The work was already done. If you need something different or want to make additional changes, please provide a more specific request.")],
                "is_duplicate": True,
                "needs_reflection": False
            }
        
        # Circuit breaker: Check if this operation recently failed
        if task_cache.is_recently_failed(last_user_msg, page_id):
            return {
                "messages": [HumanMessage(content="🚫 This operation recently failed multiple times. Please wait a few minutes before retrying, or try a different approach.")],
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
            
            # Disable reflection for now to reduce token usage - can re-enable later
            needs_reflection = False
            is_post_reflection = state.get("has_reflected", False)
            
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
                "messages": [HumanMessage(content=f"❌ Operation failed: {str(e)}. This has been logged to prevent immediate retries.")],
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
            config_with_limit = {
                "configurable": {
                    "thread_id": "reflection_thread",
                    "user_id": "system"
                },
                "recursion_limit": 50
            }
            
            reflection_result = agent.invoke(
                {"messages": recent_messages + [reflection_message]}, 
                config=config_with_limit
            )
            
            new_messages = reflection_result.get("messages", [])
            
            return {
                "messages": new_messages,
                "needs_reflection": False,
                "has_reflected": True
            }
            
        except Exception as e:
            # If reflection fails, continue without it
            from langchain_core.messages import AIMessage
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
    
    # Compile the graph WITHOUT a checkpointer for Studio
    # LangGraph Studio handles persistence automatically
    agent = workflow.compile()
    
    print("✅ Studio agent compiled with task completion cache")
    return agent

# Extract page ID helper function
def extract_page_id(content: str) -> str:
    """Extract page ID from message content"""
    import re
    page_match = re.search(r'LOCAL page ID (\d+)', content)
    return page_match.group(1) if page_match else ""

# Export the graph for LangGraph Studio
# Studio expects a variable named 'graph' 
graph = create_studio_agent()

# Additional exports for debugging
if __name__ == "__main__":
    print("✅ Web Design Agent graph created successfully for LangGraph Studio!")
    print("🚀 Ready for LangGraph Studio with duplicate prevention!")
    
    # Test that the graph can be invoked
    try:
        config = {
            "configurable": {
                "thread_id": "studio_test",
                "user_id": "studio_user"
            },
            "recursion_limit": 50
        }
        
        response = graph.invoke(
            {"messages": [HumanMessage(content="Hello! Can you help me with WordPress?")]},
            config=config
        )
        
        print("🧠 Graph test successful!")
        print(f"📝 Response: {response['messages'][-1].content[:100]}...")
        
    except Exception as e:
        print(f"⚠️  Graph test failed: {e}")
        print("Check your environment variables and API keys.") 