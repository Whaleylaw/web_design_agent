#!/usr/bin/env python3
"""
LangGraph Memory Agent Template

An advanced agent with sophisticated memory capabilities including both short-term
conversation memory and long-term semantic memory for persistent knowledge.
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import json
import requests
from requests.auth import HTTPBasicAuth

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver  
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from persistent_store import PersistentJSONStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Environment setup
def load_environment():
    """Load environment variables and validate required keys."""
    # Load environment variables from .env file
    load_dotenv()
    
    required_vars = ["OPENAI_API_KEY"]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

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
    from wordpress_tools import get_all_wordpress_tools
    
    # Import visual editing tools
    from visual_editor_tools import (
        wp_add_custom_css_to_page,
        wp_add_content_block_to_page,
        wp_get_page_structure,
        wp_update_page_section
    )
    
    # Import navigation tools
    from navigation_tools import (
        wp_navigate_to_page,
        wp_create_blank_page,
        wp_list_all_pages,
        wp_add_page_to_menu
    )
    
    # Import coming soon tool
    from disable_coming_soon_tool import wp_disable_coming_soon_mode
    
    # Import local editing tools
    from local_editing_tools import (
        read_local_page_html,
        edit_local_page_content,
        add_local_page_css,
        analyze_local_page_structure,
        list_local_pages,
        clone_wordpress_site,
        push_local_changes
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
    local_tools = [
        read_local_page_html,
        edit_local_page_content,
        add_local_page_css,
        analyze_local_page_structure,
        list_local_pages,
        clone_wordpress_site,
        push_local_changes
    ]
    
    utility_tools = [wp_disable_coming_soon_mode]
    
    return wordpress_tools + visual_tools + navigation_tools + local_tools + utility_tools

def create_memory_agent_system(use_sqlite: bool = False):
    """Create and configure the memory agent system."""
    load_environment()
    
    # Initialize components
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    embeddings = OpenAIEmbeddings()
    
    # Set up persistence
    if use_sqlite:
        checkpointer = SqliteSaver.from_conn_string("memory_agent.db")
        print("✅ Using SQLite persistence")
    else:
        checkpointer = MemorySaver()
        print("✅ Using in-memory persistence")
    
    # Set up long-term memory store
    store = InMemoryStore()
    memory_manager = MemoryManager(store, embeddings)
    
    # Create memory tools
    memory_tools = create_memory_tools(memory_manager)
    
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
    
    # Compile with memory capabilities
    agent = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    return agent, memory_manager

def create_wordpress_memory_agent(use_sqlite: bool = False):
    """Create a unified WordPress and memory agent with all features."""
    load_environment()
    
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    embeddings = OpenAIEmbeddings()
    
    # Use persistent store when SQLite is enabled
    if use_sqlite:
        store = PersistentJSONStore("memories.json")
    else:
        store = InMemoryStore()
    
    memory_manager = MemoryManager(store, embeddings)
    
    # Set up persistence
    if use_sqlite:
        # Create SQLite connection with thread safety
        import sqlite3
        conn = sqlite3.connect("memory_agent.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        print("✅ Using SQLite persistence (memory_agent.db)")
    else:
        checkpointer = MemorySaver()
        print("✅ Using in-memory persistence")
    
    # Enhanced memory tools with actual implementation
    @tool
    def remember_info(information: str, memory_type: str = "general") -> str:
        """Store information in long-term memory."""
        # Get user_id from context (simplified for demo)
        user_id = "demo_user"
        memory_id = memory_manager.create_memory(user_id, information, memory_type)
        return f"✅ Remembered: {information}"
    
    @tool
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
    
    system_prompt = """You are an AI assistant with memory and comprehensive WordPress management capabilities, including visual editing.

When the user mentions they are viewing a specific page (indicated by [User is viewing page ID X]), you have enhanced context awareness and can:
- Make visual changes using CSS (background colors, fonts, spacing, etc.)
- Add new content blocks (text, images, buttons, etc.)
- Update existing text content
- Analyze page structure to make targeted edits

For visual changes:
- Use wp_add_custom_css_to_page for style changes (colors, fonts, spacing)
- Use wp_add_content_block_to_page to add new sections
- Use wp_update_page_section to change specific text
- Use wp_get_page_structure to understand the page layout first

For navigation:
- Use wp_navigate_to_page when user wants to view a different page
- Use wp_create_blank_page to create new pages
- Use wp_list_all_pages to show available pages
- The visual editor will update to show the page after navigation

For local editing (when user mentions LOCAL or cloned files):
- Use read_local_page_html to see the ACTUAL HTML structure
- Use edit_local_page_content to modify page content locally
- Use add_local_page_css to add styling locally
- Use analyze_local_page_structure to understand the page layout
- Use clone_wordpress_site to download all pages locally
- Use push_local_changes to sync changes back to WordPress
- Local editing allows you to SEE the full HTML and make precise changes

Memory tools:
- remember_info: Store information
- search_memory: Search past conversations  
- list_all_memories: List all memories

WordPress Content Management:
- wp_create_post, wp_update_post, wp_delete_post, wp_get_posts: Manage posts
- wp_create_page, wp_update_page, wp_get_pages: Manage pages
- wp_get_media, wp_update_media_metadata: Manage media library
- wp_create_category, wp_create_tag, wp_get_categories, wp_get_tags: Manage taxonomies
- wp_create_block, wp_get_blocks: Manage reusable blocks

WordPress Site Management:
- wp_get_site_info, wp_update_site_settings: Site configuration
- wp_get_comments, wp_moderate_comment: Comment moderation
- wp_get_users, wp_get_current_user: User management
- wp_get_menus, wp_get_menu_items: Navigation menus
- wp_get_themes, wp_get_plugins: Theme and plugin info
- wp_search: Search across all content

WordPress API:
- wp_api_request: Make custom API requests for any endpoint

Be helpful, proactive, and transparent about what you remember and what actions you're taking."""

    # Create tool-based agent with chosen persistence
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
        checkpointer=checkpointer
    )
    
    return agent, memory_manager

def run_conversation(use_sqlite: bool = False):
    """Run an interactive conversation with the WordPress memory agent."""
    # Always use the tool-based agent with WordPress capabilities
    agent, memory_manager = create_wordpress_memory_agent(use_sqlite)
    
    print("🧠 WordPress Memory Agent initialized!")
    print()
    print("💾 Memory capabilities:")
    print("   - Remembers information across conversations")
    print("   - Can search through past memories")
    print("   - Learns your preferences over time")
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
        }
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

def run_example():
    """Run predefined examples to demonstrate WordPress and memory capabilities."""
    agent, memory_manager = create_wordpress_memory_agent()
    
    print("🧠 Running WordPress Memory Agent Examples...")
    print("=" * 50)
    
    config = {
        "configurable": {
            "thread_id": "memory_example",
            "user_id": "example_user"
        }
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
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "example":
            run_example()
        elif command == "sqlite":
            run_conversation(use_sqlite=True)
        else:
            print("Usage: python main.py [example|sqlite]")
            print()
            print("Options:")
            print("  (no args)  - Run with in-memory persistence")
            print("  sqlite     - Run with SQLite persistence") 
            print("  example    - Run example demonstrations")
    else:
        run_conversation()