#!/usr/bin/env python3
"""
Cleanup script to move non-essential files to old/ folder
Organizes files by category for better organization
"""

import os
import shutil
from pathlib import Path

def ensure_dir(path):
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def move_file(src, dst):
    """Safely move file with logging"""
    try:
        if os.path.exists(src):
            ensure_dir(os.path.dirname(dst))
            print(f"Moving: {src} -> {dst}")
            shutil.move(src, dst)
            return True
        else:
            print(f"Skipped (not found): {src}")
            return False
    except Exception as e:
        print(f"Error moving {src}: {e}")
        return False

def move_directory(src, dst):
    """Safely move entire directory with logging"""
    try:
        if os.path.exists(src):
            ensure_dir(os.path.dirname(dst))
            print(f"Moving directory: {src} -> {dst}")
            shutil.move(src, dst)
            return True
        else:
            print(f"Skipped directory (not found): {src}")
            return False
    except Exception as e:
        print(f"Error moving directory {src}: {e}")
        return False

def main():
    print("🧹 Starting cleanup of non-essential files...")
    print("=" * 50)
    
    # Ensure old/ directory structure
    ensure_dir("old/wordpress_legacy")
    ensure_dir("old/backend_wordpress")
    ensure_dir("old/documentation")
    ensure_dir("old/temp_files")
    ensure_dir("old/test_files")
    ensure_dir("old/screenshots")
    ensure_dir("old/venv_backup")
    
    moved_count = 0
    
    # 1. WordPress Legacy Files
    print("\n📁 Moving WordPress Legacy Files...")
    wordpress_files = [
        ("wp-sites.json", "old/wordpress_legacy/wp-sites.json"),
        ("wp_endpoint.txt", "old/wordpress_legacy/wp_endpoint.txt"),
    ]
    
    for src, dst in wordpress_files:
        if move_file(src, dst):
            moved_count += 1
    
    # WordPress clone directories
    wordpress_dirs = [
        ("wordpress_clone/clones", "old/wordpress_legacy/clones"),
        ("wordpress_clone/old", "old/wordpress_legacy/wordpress_clone_old"),
        ("wordpress_clone/css", "old/wordpress_legacy/css"),
    ]
    
    for src, dst in wordpress_dirs:
        if move_directory(src, dst):
            moved_count += 1
    
    # 2. Backend WordPress Files
    print("\n🔧 Moving Backend WordPress Files...")
    backend_wp_files = [
        ("backend/wordpress_sync_v2.py", "old/backend_wordpress/wordpress_sync_v2.py"),
        ("backend/wordpress_push.py", "old/backend_wordpress/wordpress_push.py"),
        ("backend/wordpress_tools.py", "old/backend_wordpress/wordpress_tools.py"),
        ("backend/wordpress_clone.py", "old/backend_wordpress/wordpress_clone.py"),
        ("backend/disable_coming_soon_tool.py", "old/backend_wordpress/disable_coming_soon_tool.py"),
        ("backend/test_wordpress_connection.py", "old/backend_wordpress/test_wordpress_connection.py"),
    ]
    
    for src, dst in backend_wp_files:
        if move_file(src, dst):
            moved_count += 1
    
    # 3. Documentation Files
    print("\n📚 Moving Documentation Files...")
    doc_files = [
        ("README.md", "old/documentation/README.md"),
        ("claude.md", "old/documentation/claude.md"),
        ("VERSION_INFO.md", "old/documentation/VERSION_INFO.md"),
        ("SQLITE_PERSISTENCE.md", "old/documentation/SQLITE_PERSISTENCE.md"),
    ]
    
    for src, dst in doc_files:
        if move_file(src, dst):
            moved_count += 1
    
    # 4. Temporary and Test Files
    print("\n🗂️ Moving Temporary and Test Files...")
    temp_test_files = [
        ("agent_test.db", "old/test_files/agent_test.db"),
        ("agent_test2.db", "old/test_files/agent_test2.db"),
    ]
    
    for src, dst in temp_test_files:
        if move_file(src, dst):
            moved_count += 1
    
    # Move entire directories
    temp_dirs = [
        ("research", "old/temp_files/research"),
        ("temp", "old/temp_files/temp"),
    ]
    
    for src, dst in temp_dirs:
        if move_directory(src, dst):
            moved_count += 1
    
    # 5. Screenshots
    print("\n📸 Moving Screenshots...")
    screenshot_files = [
        ("print screen streaming.tiff", "old/screenshots/print screen streaming.tiff"),
        ("print screen streamlit.png", "old/screenshots/print screen streamlit.png"),
    ]
    
    for src, dst in screenshot_files:
        if move_file(src, dst):
            moved_count += 1
    
    # 6. Virtual Environment (optional - takes up a lot of space)
    print("\n🐍 Moving Virtual Environment...")
    print("Note: You can recreate venv with: python -m venv venv && pip install -r requirements.txt")
    if move_directory("venv", "old/venv_backup/venv"):
        moved_count += 1
    
    print("\n" + "=" * 50)
    print(f"✅ Cleanup complete! Moved {moved_count} items to old/ folder")
    print("\n📋 Essential files remaining for agent operation:")
    print("- studio_app.py (LangGraph Studio)")
    print("- langgraph.json (LangGraph config)")
    print("- requirements.txt (Dependencies)")
    print("- .env (Environment variables)")
    print("- frontend/ (Streamlit UI)")
    print("- backend/ (Core agent files only)")
    print("- deploy/ (Netlify deployment)")
    print("- wordpress_clone/pages/ (Website content)")
    print("- memory_agent.db* (Agent memory)")
    
    print("\n🔄 Next steps:")
    print("1. Test the agent to ensure it still works")
    print("2. Recreate venv: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
    print("3. Test Netlify deployment")

if __name__ == "__main__":
    main() 