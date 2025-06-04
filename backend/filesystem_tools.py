"""
Filesystem tools for direct file manipulation
Equivalent to Filesystem MCP Server functionality
SECURITY: All operations are restricted to the project directory
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List
from langchain_core.tools import tool
import json
from datetime import datetime
import sys

# Security: Define the allowed root directory
PROJECT_ROOT = Path.cwd()  # Current working directory (project root)
ALLOWED_PATHS = [
    PROJECT_ROOT / "wordpress_clone",  # WordPress clone directory
    PROJECT_ROOT / "backend",          # Backend code (read-only recommended)
    PROJECT_ROOT / "frontend",         # Frontend code (read-only recommended)
    PROJECT_ROOT / "scripts",          # Scripts directory
    PROJECT_ROOT / "temp",             # Temporary files
]

def _validate_path(file_path: str, operation: str = "access") -> Path:
    """Validate that a path is within allowed directories.
    
    Args:
        file_path: The path to validate
        operation: Type of operation (for error messages)
        
    Returns:
        Resolved Path object if valid
        
    Raises:
        ValueError: If path is outside allowed directories
    """
    path = Path(file_path)
    
    # Convert to absolute path
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    
    # Resolve to handle .. and . components
    try:
        resolved_path = path.resolve()
    except Exception:
        raise ValueError(f"Invalid path: {file_path}")
    
    # Check if path is within any allowed directory
    allowed = False
    for allowed_root in ALLOWED_PATHS:
        try:
            allowed_root_resolved = allowed_root.resolve()
            # Check if the path is within this allowed root
            resolved_path.relative_to(allowed_root_resolved)
            allowed = True
            break
        except ValueError:
            # Path is not within this allowed root, continue checking
            continue
    
    if not allowed:
        # Also allow direct access to project root for certain files
        try:
            PROJECT_ROOT.resolve()
            if resolved_path.parent == PROJECT_ROOT.resolve():
                # Allow specific files in project root
                allowed_files = {'.env', 'requirements.txt', 'README.md', 'wp-sites.json'}
                if resolved_path.name in allowed_files:
                    allowed = True
        except ValueError:
            pass
    
    if not allowed:
        allowed_paths_str = ", ".join(str(p) for p in ALLOWED_PATHS)
        raise ValueError(
            f"Security Error: {operation} denied for '{file_path}'. "
            f"Operations are restricted to: {allowed_paths_str}"
        )
    
    return resolved_path


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.
    
    SECURITY: Only files within allowed project directories can be read.
    
    Args:
        file_path: Path to the file to read (relative to project root or absolute)
        
    Returns:
        File contents or error message
    """
    try:
        path = _validate_path(file_path, "read")
            
        if not path.exists():
            return f"Error: File {file_path} does not exist"
            
        if not path.is_file():
            return f"Error: {file_path} is not a file"
            
        content = path.read_text(encoding='utf-8')
        return f"Contents of {file_path}:\n\n{content}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"


@tool
def write_file(file_path: str, content: str, create_dirs: bool = True) -> str:
    """Write content to a file.
    
    SECURITY: Only files within allowed project directories can be written.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Success or error message
    """
    try:
        path = _validate_path(file_path, "write")
            
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
            
        # Check if file exists to determine if this is create or update
        action = "update" if path.exists() else "create"
        
        path.write_text(content, encoding='utf-8')
        
        # Log the change
        description = f"{'Updated' if action == 'update' else 'Created'} file with {len(content)} characters"
        _log_change(file_path, action, description)
        
        return f"Successfully wrote {len(content)} characters to {file_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error writing file {file_path}: {str(e)}"


@tool
def append_file(file_path: str, content: str) -> str:
    """Append content to a file.
    
    SECURITY: Only files within allowed project directories can be modified.
    
    Args:
        file_path: Path to the file to append to
        content: Content to append
        
    Returns:
        Success or error message
    """
    try:
        path = _validate_path(file_path, "append")
            
        if not path.exists():
            return f"Error: File {file_path} does not exist"
            
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
            
        return f"Successfully appended {len(content)} characters to {file_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error appending to file {file_path}: {str(e)}"


@tool
def delete_file(file_path: str) -> str:
    """Delete a file.
    
    SECURITY: Only files within allowed project directories can be deleted.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        Success or error message
    """
    try:
        path = _validate_path(file_path, "delete")
            
        if not path.exists():
            return f"Error: File {file_path} does not exist"
            
        if not path.is_file():
            return f"Error: {file_path} is not a file"
            
        # Get file size before deletion for logging
        file_size = path.stat().st_size
            
        path.unlink()
        
        # Log the change
        description = f"Deleted file ({file_size} bytes)"
        _log_change(file_path, "delete", description)
        
        return f"Successfully deleted file {file_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error deleting file {file_path}: {str(e)}"


@tool
def copy_file(source_path: str, destination_path: str, create_dirs: bool = True) -> str:
    """Copy a file to a new location.
    
    SECURITY: Both source and destination must be within allowed directories.
    
    Args:
        source_path: Path to the source file
        destination_path: Path to the destination
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Success or error message
    """
    try:
        src = _validate_path(source_path, "copy from")
        dst = _validate_path(destination_path, "copy to")
            
        if not src.exists():
            return f"Error: Source file {source_path} does not exist"
            
        if not src.is_file():
            return f"Error: {source_path} is not a file"
            
        if create_dirs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            
        shutil.copy2(src, dst)
        return f"Successfully copied {source_path} to {destination_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error copying file: {str(e)}"


@tool
def move_file(source_path: str, destination_path: str, create_dirs: bool = True) -> str:
    """Move/rename a file.
    
    SECURITY: Both source and destination must be within allowed directories.
    
    Args:
        source_path: Path to the source file
        destination_path: Path to the destination
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Success or error message
    """
    try:
        src = _validate_path(source_path, "move from")
        dst = _validate_path(destination_path, "move to")
            
        if not src.exists():
            return f"Error: Source file {source_path} does not exist"
            
        if create_dirs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            
        shutil.move(str(src), str(dst))
        return f"Successfully moved {source_path} to {destination_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error moving file: {str(e)}"


@tool
def create_directory(dir_path: str, parents: bool = True) -> str:
    """Create a directory.
    
    SECURITY: Directory must be within allowed project directories.
    
    Args:
        dir_path: Path to the directory to create
        parents: Whether to create parent directories if they don't exist
        
    Returns:
        Success or error message
    """
    try:
        path = _validate_path(dir_path, "create directory")
            
        path.mkdir(parents=parents, exist_ok=True)
        return f"Successfully created directory {dir_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error creating directory {dir_path}: {str(e)}"


@tool
def delete_directory(dir_path: str, recursive: bool = False) -> str:
    """Delete a directory.
    
    SECURITY: Directory must be within allowed project directories.
    
    Args:
        dir_path: Path to the directory to delete
        recursive: Whether to delete recursively (required for non-empty directories)
        
    Returns:
        Success or error message
    """
    try:
        path = _validate_path(dir_path, "delete directory")
            
        if not path.exists():
            return f"Error: Directory {dir_path} does not exist"
            
        if not path.is_dir():
            return f"Error: {dir_path} is not a directory"
            
        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()  # Only works if directory is empty
            
        return f"Successfully deleted directory {dir_path}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error deleting directory {dir_path}: {str(e)}"


@tool
def list_directory(dir_path: str = ".", show_hidden: bool = False) -> str:
    """List contents of a directory.
    
    SECURITY: Directory must be within allowed project directories.
    
    Args:
        dir_path: Path to the directory to list (default: current directory)
        show_hidden: Whether to show hidden files/directories
        
    Returns:
        Directory listing or error message
    """
    try:
        # Special case: if dir_path is ".", use project root
        if dir_path == ".":
            path = PROJECT_ROOT
        else:
            path = _validate_path(dir_path, "list directory")
            
        if not path.exists():
            return f"Error: Directory {dir_path} does not exist"
            
        if not path.is_dir():
            return f"Error: {dir_path} is not a directory"
            
        items = []
        for item in sorted(path.iterdir()):
            if not show_hidden and item.name.startswith('.'):
                continue
                
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024*1024):.1f}MB"
                items.append(f"📄 {item.name} ({size_str})")
                
        result = f"Contents of {dir_path}:\n\n"
        if items:
            result += "\n".join(items)
        else:
            result += "(empty directory)"
            
        return result
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error listing directory {dir_path}: {str(e)}"


@tool
def get_file_info(file_path: str) -> str:
    """Get information about a file or directory.
    
    SECURITY: Path must be within allowed project directories.
    
    Args:
        file_path: Path to the file or directory
        
    Returns:
        File information or error message
    """
    try:
        path = _validate_path(file_path, "get info")
            
        if not path.exists():
            return f"Error: {file_path} does not exist"
            
        stat = path.stat()
        
        info = f"Information for {file_path}:\n\n"
        info += f"Type: {'Directory' if path.is_dir() else 'File'}\n"
        info += f"Size: {stat.st_size} bytes\n"
        info += f"Modified: {stat.st_mtime}\n"
        info += f"Permissions: {oct(stat.st_mode)[-3:]}\n"
        
        if path.is_file():
            try:
                # Try to detect if it's a text file
                with open(path, 'rb') as f:
                    sample = f.read(1024)
                    is_text = all(byte < 128 for byte in sample)
                info += f"Text file: {'Yes' if is_text else 'No'}\n"
            except:
                pass
                
        return info
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error getting file info for {file_path}: {str(e)}"


@tool
def search_files(pattern: str, directory: str = ".", recursive: bool = True) -> str:
    """Search for files matching a pattern.
    
    SECURITY: Search directory must be within allowed project directories.
    
    Args:
        pattern: Glob pattern to search for (e.g., "*.py", "test_*")
        directory: Directory to search in (default: current directory)
        recursive: Whether to search recursively in subdirectories
        
    Returns:
        List of matching files or error message
    """
    try:
        # Special case: if directory is ".", use project root
        if directory == ".":
            path = PROJECT_ROOT
        else:
            path = _validate_path(directory, "search in")
            
        if not path.exists():
            return f"Error: Directory {directory} does not exist"
            
        if not path.is_dir():
            return f"Error: {directory} is not a directory"
            
        if recursive:
            matches = list(path.rglob(pattern))
        else:
            matches = list(path.glob(pattern))
            
        # Filter matches to only include allowed paths
        allowed_matches = []
        for match in matches:
            try:
                _validate_path(str(match), "access")
                allowed_matches.append(match)
            except ValueError:
                # Skip files outside allowed directories
                continue
            
        if not allowed_matches:
            return f"No files found matching pattern '{pattern}' in {directory}"
            
        result = f"Files matching '{pattern}' in {directory}:\n\n"
        for match in sorted(allowed_matches):
            try:
                relative_path = match.relative_to(path)
            except ValueError:
                relative_path = match
                
            if match.is_dir():
                result += f"📁 {relative_path}/\n"
            else:
                size = match.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024*1024):.1f}MB"
                result += f"📄 {relative_path} ({size_str})\n"
                
        return result
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error searching files: {str(e)}"


# WordPress-specific helper functions
@tool
def delete_local_page(page_id: int) -> str:
    """Delete a local WordPress page completely.
    
    SECURITY: Only operates within the wordpress_clone directory.
    
    Args:
        page_id: The WordPress page ID to delete
        
    Returns:
        Success or error message
    """
    try:
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        page_dir = clone_dir / f"pages/page_{page_id}"
        manifest_file = clone_dir / "manifest.json"
        
        # Validate paths are within allowed directories
        _validate_path(str(page_dir), "delete page")
        _validate_path(str(manifest_file), "update manifest")
        
        if not page_dir.exists():
            return f"Error: Page {page_id} not found in local clone"
            
        # Remove the page directory
        shutil.rmtree(page_dir)
        
        # Log the change
        _log_change(f"wordpress_clone/pages/page_{page_id}", "delete_page", f"Deleted WordPress page {page_id}")
        
        # Update manifest
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    
                if str(page_id) in manifest.get("pages", {}):
                    del manifest["pages"][str(page_id)]
                    
                    # Write to a temporary file first, then rename to prevent corruption
                    temp_manifest = manifest_file.with_suffix('.tmp')
                    with open(temp_manifest, 'w') as f:
                        json.dump(manifest, f, indent=2)
                    
                    # Atomic rename to replace the original
                    temp_manifest.replace(manifest_file)
                    
            except json.JSONDecodeError as e:
                return f"Warning: Manifest file was corrupted, but page directory was deleted. Error: {e}"
            except Exception as e:
                return f"Warning: Could not update manifest, but page directory was deleted. Error: {e}"
                    
        return f"Successfully deleted local page {page_id} and updated manifest"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error deleting local page {page_id}: {str(e)}"


@tool
def restore_local_page_from_wordpress(page_id: int) -> str:
    """Restore a local page from WordPress, overwriting any local changes.
    
    Args:
        page_id: The WordPress page ID to restore
        
    Returns:
        Success or error message
    """
    try:
        # This would need to integrate with the WordPress cloning system
        # For now, just provide instructions
        return f"""To restore page {page_id} from WordPress:

1. Delete the local page: delete_local_page({page_id})
2. Re-clone the site: clone_wordpress_site()

Or manually:
1. Delete: wordpress_clone/pages/page_{page_id}/
2. Use WordPress API to fetch fresh content
3. Recreate the local files

This will overwrite any local changes with the WordPress version."""
        
    except Exception as e:
        return f"Error restoring page {page_id}: {str(e)}"


@tool
def get_allowed_directories() -> str:
    """Get a list of directories that filesystem operations are allowed in.
    
    Returns:
        List of allowed directories for security transparency
    """
    result = "Filesystem operations are restricted to these directories:\n\n"
    for i, path in enumerate(ALLOWED_PATHS, 1):
        result += f"{i}. {path}\n"
    
    result += f"\nProject root: {PROJECT_ROOT}\n"
    result += "\nAllowed files in project root: .env, requirements.txt, README.md, wp-sites.json\n"
    result += "\nThis restriction ensures security and prevents accidental system file access."
    
    return result


@tool
def add_page_to_manifest(page_id: int, title: str) -> str:
    """Add a new page to the local manifest.
    
    SECURITY: Only operates within the wordpress_clone directory.
    
    Args:
        page_id: The WordPress page ID
        title: The page title
        
    Returns:
        Success or error message
    """
    try:
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        manifest_file = clone_dir / "manifest.json"
        
        # Validate paths are within allowed directories
        _validate_path(str(manifest_file), "update manifest")
        
        # Load existing manifest or create new one
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
            except json.JSONDecodeError:
                # Create new manifest if corrupted
                manifest = {
                    "site_url": "https://lawyerincorporated.com",
                    "cloned_at": datetime.now().isoformat(),
                    "pages": {},
                    "posts": {},
                    "theme_css": "css/theme.css",
                    "custom_css": ""
                }
        else:
            # Create new manifest
            manifest = {
                "site_url": "https://lawyerincorporated.com", 
                "cloned_at": datetime.now().isoformat(),
                "pages": {},
                "posts": {},
                "theme_css": "css/theme.css",
                "custom_css": ""
            }
        
        # Add the new page
        manifest["pages"][str(page_id)] = {
            "title": title,
            "path": f"pages/page_{page_id}/index.html",
            "metadata": f"pages/page_{page_id}/metadata.json"
        }
        
        # Write to a temporary file first, then rename to prevent corruption
        temp_manifest = manifest_file.with_suffix('.tmp')
        with open(temp_manifest, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Atomic rename to replace the original
        temp_manifest.replace(manifest_file)
        
        return f"Successfully added page {page_id} ('{title}') to manifest"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error adding page to manifest: {str(e)}"


@tool
def rebuild_manifest_from_files() -> str:
    """Rebuild the manifest by scanning existing page directories.
    
    SECURITY: Only operates within the wordpress_clone directory.
    
    Returns:
        Success or error message with page count
    """
    try:
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        pages_dir = clone_dir / "pages"
        manifest_file = clone_dir / "manifest.json"
        
        # Validate paths are within allowed directories
        _validate_path(str(pages_dir), "scan pages")
        _validate_path(str(manifest_file), "update manifest")
        
        if not pages_dir.exists():
            return "Error: No pages directory found in wordpress_clone"
        
        # Scan for page directories
        pages = {}
        for page_dir in pages_dir.iterdir():
            if page_dir.is_dir() and page_dir.name.startswith("page_"):
                try:
                    # Extract page ID from directory name
                    page_id = page_dir.name.replace("page_", "")
                    
                    # Try to get title from HTML file
                    html_file = page_dir / "index.html"
                    title = f"Page {page_id}"  # Default title
                    
                    if html_file.exists():
                        try:
                            html_content = html_file.read_text()
                            # Extract title from HTML
                            import re
                            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
                            if title_match:
                                title = title_match.group(1).strip()
                        except:
                            pass  # Use default title if extraction fails
                    
                    pages[page_id] = {
                        "title": title,
                        "path": f"pages/page_{page_id}/index.html",
                        "metadata": f"pages/page_{page_id}/metadata.json"
                    }
                    
                except Exception as e:
                    print(f"Warning: Could not process {page_dir.name}: {e}")
                    continue
        
        # Create new manifest
        manifest = {
            "site_url": "https://lawyerincorporated.com",
            "cloned_at": datetime.now().isoformat(),
            "pages": pages,
            "posts": {},
            "theme_css": "css/theme.css",
            "custom_css": ""
        }
        
        # Write to a temporary file first, then rename to prevent corruption
        temp_manifest = manifest_file.with_suffix('.tmp')
        with open(temp_manifest, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Atomic rename to replace the original
        temp_manifest.replace(manifest_file)
        
        return f"Successfully rebuilt manifest with {len(pages)} pages: {list(pages.keys())}"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error rebuilding manifest: {str(e)}"


@tool
def update_page_title_in_manifest(page_id: int, new_title: str) -> str:
    """Update a page's title in the manifest.
    
    SECURITY: Only operates within the wordpress_clone directory.
    
    Args:
        page_id: The WordPress page ID
        new_title: The new title for the page
        
    Returns:
        Success or error message
    """
    try:
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        manifest_file = clone_dir / "manifest.json"
        
        # Validate paths are within allowed directories
        _validate_path(str(manifest_file), "update manifest")
        
        if not manifest_file.exists():
            return "Error: No manifest file found. Try rebuilding with rebuild_manifest_from_files()"
        
        # Load manifest
        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            return f"Error: Manifest file is corrupted: {e}"
        
        # Update the page title
        if str(page_id) in manifest.get("pages", {}):
            manifest["pages"][str(page_id)]["title"] = new_title
            
            # Write to a temporary file first, then rename to prevent corruption
            temp_manifest = manifest_file.with_suffix('.tmp')
            with open(temp_manifest, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Atomic rename to replace the original
            temp_manifest.replace(manifest_file)
            
            return f"Successfully updated title for page {page_id} to '{new_title}'"
        else:
            return f"Error: Page {page_id} not found in manifest"
        
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error updating page title: {str(e)}"


@tool
def create_local_page(title: str, content: str = "", page_id: Optional[str] = None) -> str:
    """Create a new page locally without pushing to WordPress.
    
    Args:
        title: The page title
        content: HTML content for the page (optional)
        page_id: Specific page ID to use (optional, will auto-generate if not provided)
    
    Returns:
        Success message with the page ID and instructions for publishing later
    """
    try:
        clone_dir = Path("wordpress_clone")
        if not clone_dir.exists():
            return "❌ No local clone directory found. Run clone_wordpress_site_v2 first."
        
        # Auto-generate page ID if not provided
        if not page_id:
            # Find the next available page ID
            existing_pages = []
            pages_dir = clone_dir / "pages"
            if pages_dir.exists():
                for page_dir in pages_dir.iterdir():
                    if page_dir.is_dir() and page_dir.name.startswith("page_"):
                        try:
                            pid = int(page_dir.name.split("_")[1])
                            existing_pages.append(pid)
                        except:
                            continue
            
            # Start from a high number to avoid conflicts with WordPress pages
            page_id = str(max(existing_pages) + 1 if existing_pages else 1000)
        
        page_dir = clone_dir / f"pages/page_{page_id}"
        
        # Check if page already exists
        if page_dir.exists():
            return f"❌ Page {page_id} already exists locally"
        
        # Create page directory
        page_dir.mkdir(parents=True)
        
        # Create basic HTML content if none provided
        if not content.strip():
            content = f"<h1>{title}</h1>\n<p>This is a new page created locally.</p>"
        
        # Ensure we have a complete HTML document
        if not content.strip().lower().startswith('<!doctype') and not content.strip().lower().startswith('<html'):
            full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>'''
        else:
            full_html = content
        
        # Write index.html (local working copy)
        (page_dir / "index.html").write_text(full_html)
        
        # Create metadata.json
        metadata = {
            "id": int(page_id),
            "title": title,
            "slug": title.lower().replace(" ", "-").replace("'", ""),
            "status": "local_only",
            "date": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "link": f"local://page_{page_id}",
            "local_only": True
        }
        (page_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        
        # DO NOT create clone.html - it will be created when the page is pushed to WordPress
        
        # Add to manifest
        manifest_file = clone_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
        else:
            manifest = {"pages": {}}
        
        if "pages" not in manifest:
            manifest["pages"] = {}
            
        manifest["pages"][page_id] = {
            "title": title,
            "status": "local_only"
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Refresh the interface
        refresh_streamlit_interface()
        
        return f"""✅ Local page created successfully!

📄 **Page Details:**
- **Title:** {title}
- **Page ID:** {page_id}
- **Status:** Local only (not yet published to WordPress)
- **Location:** `wordpress_clone/pages/page_{page_id}/`

📁 **Files Created:**
- `index.html` - Your working copy with full HTML
- `metadata.json` - Page metadata

⚠️ **Next Steps:**
- The page exists only locally and is NOT published to WordPress
- To publish to WordPress, use: `push_changes_v2` or create with `wp_create_page`
- You can edit the local files and preview changes before publishing"""
    
    except Exception as e:
        return f"❌ Error creating local page: {str(e)}"


def _refresh_streamlit_interface() -> str:
    """Helper function to trigger a refresh of the Streamlit interface.
    
    This creates a refresh command that the Streamlit app can detect.
    Does not use the @tool decorator so it can be called directly.
    
    Returns:
        Success message
    """
    try:
        # Create temp directory if it doesn't exist
        temp_dir = PROJECT_ROOT / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        refresh_file = temp_dir / "refresh_command.json"
        
        command = {
            "action": "refresh",
            "timestamp": datetime.now().isoformat()
        }
        
        with open(refresh_file, 'w') as f:
            json.dump(command, f)
            
        return "✅ Streamlit interface refresh triggered - the page list should update automatically"
        
    except Exception as e:
        return f"Warning: Could not trigger interface refresh: {e}"


def _clear_ui_cache() -> str:
    """Helper function to clear the Streamlit UI cache.
    
    Returns:
        Success message
    """
    try:
        temp_dir = PROJECT_ROOT / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        cache_clear_file = temp_dir / "clear_cache_command.json"
        cache_command = {
            "action": "clear_cache",
            "timestamp": datetime.now().isoformat(),
            "target": "sync_status"
        }
        with open(cache_clear_file, 'w') as f:
            json.dump(cache_command, f)
        
        return "✅ UI cache cleared"
        
    except Exception as e:
        return f"Warning: Could not clear UI cache: {e}"


@tool
def refresh_streamlit_interface() -> str:
    """Trigger a refresh of the Streamlit interface to reload the manifest.
    
    This creates a refresh command that the Streamlit app can detect.
    
    Returns:
        Success message
    """
    return _refresh_streamlit_interface()


def _log_change(file_path: str, action: str, description: str = ""):
    """Log a change to the change tracking file.
    
    Args:
        file_path: Path to the file that was changed
        action: Type of action (write, delete, create, etc.)
        description: Optional description of the change
    """
    try:
        # Create temp directory if it doesn't exist
        temp_dir = PROJECT_ROOT / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        change_log_file = temp_dir / "change_log.json"
        
        # Load existing changes
        changes = []
        if change_log_file.exists():
            try:
                with open(change_log_file, 'r') as f:
                    changes = json.load(f)
            except:
                changes = []
        
        # Add new change
        change_entry = {
            "id": len(changes) + 1,
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "action": action,
            "description": description,
            "pushed": False
        }
        
        changes.append(change_entry)
        
        # Keep only last 100 changes
        if len(changes) > 100:
            changes = changes[-100:]
        
        # Save changes
        with open(change_log_file, 'w') as f:
            json.dump(changes, f, indent=2)
            
    except Exception as e:
        print(f"Warning: Could not log change: {e}")


@tool
def get_change_log() -> str:
    """Get the log of all local file changes.
    
    Returns:
        JSON string of recent changes or error message
    """
    try:
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        
        if not change_log_file.exists():
            return "No changes logged yet."
        
        with open(change_log_file, 'r') as f:
            changes = json.load(f)
        
        if not changes:
            return "No changes logged yet."
        
        # Filter for unpushed changes
        unpushed_changes = [c for c in changes if not c.get("pushed", False)]
        
        result = f"📋 Change Log ({len(unpushed_changes)} unpushed changes):\n\n"
        
        for change in reversed(changes[-20:]):  # Show last 20 changes
            status = "✅ Pushed" if change.get("pushed", False) else "🔄 Pending"
            timestamp = change["timestamp"][:19].replace("T", " ")
            
            result += f"{status} | {timestamp} | {change['action'].upper()}\n"
            result += f"   File: {change['file_path']}\n"
            if change.get('description'):
                result += f"   Description: {change['description']}\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error reading change log: {str(e)}"


@tool
def mark_changes_as_pushed(change_ids: str = "all") -> str:
    """Mark changes as pushed to WordPress.
    
    Args:
        change_ids: Comma-separated list of change IDs, or 'all' for all changes
        
    Returns:
        Success or error message
    """
    try:
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        
        if not change_log_file.exists():
            return "No change log found."
        
        with open(change_log_file, 'r') as f:
            changes = json.load(f)
        
        if change_ids.lower() == "all":
            # Mark all changes as pushed
            for change in changes:
                change["pushed"] = True
            marked_count = len([c for c in changes if not c.get("pushed", True)])
        else:
            # Mark specific changes as pushed
            try:
                ids_to_mark = [int(id.strip()) for id in change_ids.split(",")]
                marked_count = 0
                for change in changes:
                    if change["id"] in ids_to_mark:
                        change["pushed"] = True
                        marked_count += 1
            except ValueError:
                return "Error: Invalid change ID format. Use comma-separated numbers or 'all'."
        
        # Save updated changes
        with open(change_log_file, 'w') as f:
            json.dump(changes, f, indent=2)
        
        return f"✅ Marked {marked_count} changes as pushed."
        
    except Exception as e:
        return f"Error updating change log: {str(e)}"


@tool
def clear_change_log() -> str:
    """Clear the change log (removes all entries).
    
    Returns:
        Success or error message
    """
    try:
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        
        if change_log_file.exists():
            change_log_file.unlink()
        
        return "✅ Change log cleared."
        
    except Exception as e:
        return f"Error clearing change log: {str(e)}"


@tool
def push_changes_to_wordpress(change_ids: str = "all") -> str:
    """Push local changes to WordPress.
    
    Args:
        change_ids: Comma-separated list of change IDs to push, or 'all' for all changes
        
    Returns:
        Success or error message
    """
    try:
        from .wordpress_push import WordPressPush
        import json
        
        # Get unpushed changes
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        if not change_log_file.exists():
            return "No changes to push."
        
        with open(change_log_file, 'r') as f:
            changes = json.load(f)
        
        # Filter for unpushed changes
        unpushed_changes = [c for c in changes if not c.get("pushed", False)]
        
        if not unpushed_changes:
            return "✅ No unpushed changes found."
        
        # Filter by specific IDs if requested
        if change_ids.lower() != "all":
            try:
                ids_to_push = [int(id.strip()) for id in change_ids.split(",")]
                changes_to_push = [c for c in unpushed_changes if c["id"] in ids_to_push]
            except ValueError:
                return "Error: Invalid change ID format. Use comma-separated numbers or 'all'."
        else:
            changes_to_push = unpushed_changes
        
        if not changes_to_push:
            return "No matching changes to push."
        
        # Initialize WordPress pusher
        try:
            pusher = WordPressPush(str(PROJECT_ROOT / "wordpress_clone"))
        except FileNotFoundError:
            return "Error: No WordPress clone found. Please clone the site first."
        
        # Group changes by page ID
        pages_to_push = set()
        for change in changes_to_push:
            # Extract page ID from file path
            if "page_" in change["file_path"]:
                import re
                page_match = re.search(r'page_(\d+)', change["file_path"])
                if page_match:
                    pages_to_push.add(page_match.group(1))
        
        if not pages_to_push:
            return "No WordPress pages found in changes to push."
        
        # Push each page
        success_count = 0
        error_messages = []
        
        for page_id in pages_to_push:
            try:
                if pusher.push_page(page_id, dry_run=False):
                    success_count += 1
                else:
                    error_messages.append(f"Failed to push page {page_id}")
            except Exception as e:
                error_messages.append(f"Error pushing page {page_id}: {str(e)}")
        
        # Mark successful changes as pushed
        if success_count > 0:
            try:
                # Reload the change log in case it was modified
                with open(change_log_file, 'r') as f:
                    updated_changes = json.load(f)
                
                # Mark specific changes as pushed
                pushed_change_ids = [c["id"] for c in changes_to_push]
                marked_count = 0
                
                for change in updated_changes:
                    if change["id"] in pushed_change_ids:
                        change["pushed"] = True
                        marked_count += 1
                
                # Save updated changes
                with open(change_log_file, 'w') as f:
                    json.dump(updated_changes, f, indent=2)
                
                result = f"✅ Push completed: {success_count}/{len(pages_to_push)} pages updated successfully."
                result += f"\n📝 {marked_count} changes marked as pushed in change log."
                
            except Exception as e:
                result = f"✅ Push completed: {success_count}/{len(pages_to_push)} pages updated successfully."
                result += f"\n⚠️ Warning: Could not update change log: {str(e)}"
        else:
            result = f"❌ Push failed: 0/{len(pages_to_push)} pages updated."
        
        if error_messages:
            result += f"\n\n❌ Errors encountered:\n" + "\n".join(error_messages)
        
        # Force UI refresh by calling the function directly
        try:
            # Create refresh command
            refresh_result = _refresh_streamlit_interface()
            cache_result = _clear_ui_cache()
            
            # Also force a complete UI refresh
            force_refresh_result = force_ui_refresh()
            
            result += f"\n🔄 UI refreshed: {refresh_result}"
            result += f"\n🔄 Cache cleared: {cache_result}"
            result += f"\n🔄 {force_refresh_result}"
        except Exception as e:
            result += f"\n⚠️ Warning: UI refresh failed: {str(e)}"
        
        return result
        
    except Exception as e:
        return f"Error during push operation: {str(e)}"


@tool
def check_wordpress_sync_status() -> str:
    """Check if local files are truly in sync with WordPress (not just change log).
    
    This performs a REAL comparison between local files and WordPress content.
    
    Returns:
        Detailed sync status report
    """
    try:
        from .wordpress_push import WordPressPush
        
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        
        # Check if clone exists
        if not clone_dir.exists():
            return "❌ No local WordPress clone found. Use 'Clone the WordPress site locally' first."
        
        # Initialize WordPress pusher to check actual differences
        try:
            pusher = WordPressPush(str(clone_dir))
            wordpress_changes = pusher.detect_changes()
        except Exception as e:
            return f"❌ Error connecting to WordPress: {str(e)}"
        
        # Also check change log for unpushed local edits
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        local_changes = []
        
        if change_log_file.exists():
            try:
                with open(change_log_file, 'r') as f:
                    changes = json.load(f)
                local_changes = [c for c in changes if not c.get("pushed", False)]
            except:
                local_changes = []
        
        # Build detailed report
        result = "🔍 **WordPress Sync Status Report**\n\n"
        
        # WordPress changes (content differs from local)
        if wordpress_changes:
            result += f"⬇️ **WordPress has {len(wordpress_changes)} changes:**\n"
            for change in wordpress_changes:
                result += f"   • Page '{change['title']}' ({change['type']} differences)\n"
            result += f"\n💡 This means someone edited WordPress via admin panel or another tool.\n\n"
        
        # Local changes (unpushed edits)
        if local_changes:
            result += f"🔄 **Local has {len(local_changes)} unpushed changes:**\n"
            for change in local_changes[-5:]:  # Show last 5
                timestamp = change["timestamp"][:16].replace("T", " ")
                result += f"   • {change['action'].title()}: {change['file_path']} ({timestamp})\n"
            if len(local_changes) > 5:
                result += f"   • ... and {len(local_changes) - 5} more\n"
            result += f"\n💡 These are your local edits that haven't been pushed to WordPress.\n\n"
        
        # Overall status
        if wordpress_changes and local_changes:
            result += "⚠️ **CONFLICT**: Both WordPress and local have changes!\n"
            result += "You need to decide whether to:\n"
            result += "- Push local changes (may overwrite WordPress changes)\n"
            result += "- Pull WordPress changes (will lose local changes)\n"
            result += "- Manually merge the changes\n"
        elif wordpress_changes:
            result += "⬇️ **WordPress is newer** - Pull recommended\n"
            result += "Use 'Clone the WordPress site locally' to get latest changes.\n"
        elif local_changes:
            result += "🔄 **Local has unpushed changes** - Push recommended\n"
            result += "Use 'push_changes_to_wordpress' to upload your changes.\n"
        else:
            result += "✅ **TRULY SYNCED** - Local and WordPress match perfectly!\n"
            result += "All files are identical and no changes are pending.\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error checking sync status: {str(e)}"


@tool
def clone_wordpress_site_locally(overwrite_existing: bool = True) -> str:
    """Clone/download the WordPress site locally, creating local copies of all pages.
    
    This is equivalent to a 'pull' operation - it downloads the current WordPress content
    and overwrites local files with the latest from WordPress.
    
    Args:
        overwrite_existing: Whether to overwrite existing local files (default: True)
        
    Returns:
        Success message with details of what was cloned
    """
    try:
        from .wordpress_tools import WordPressAPI
        import json
        from bs4 import BeautifulSoup
        
        # Initialize WordPress API
        wp_api = WordPressAPI()
        
        # Create clone directory structure
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        pages_dir = clone_dir / "pages"
        css_dir = clone_dir / "css"
        
        # Create directories
        clone_dir.mkdir(exist_ok=True)
        pages_dir.mkdir(exist_ok=True)
        css_dir.mkdir(exist_ok=True)
        
        # Get all pages from WordPress
        try:
            pages_response = wp_api.request("/wp/v2/pages?per_page=100")
            if pages_response.startswith("Error"):
                return f"❌ Failed to fetch pages from WordPress: {pages_response}"
            
            pages_data = json.loads(pages_response)
            
        except Exception as e:
            return f"❌ Error fetching pages from WordPress: {str(e)}"
        
        if not pages_data:
            return "❌ No pages found on WordPress site"
        
        # Process each page
        cloned_pages = {}
        success_count = 0
        
        for page in pages_data:
            try:
                page_id = page['id']
                title = page['title']['rendered']
                content = page['content']['rendered']
                
                # Create page directory
                page_dir = pages_dir / f"page_{page_id}"
                page_dir.mkdir(exist_ok=True)
                
                # Create HTML file with full page structure
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div class="page-content">
        {content}
    </div>
</body>
</html>"""
                
                # Write HTML file
                html_file = page_dir / "index.html"
                html_file.write_text(html_content, encoding='utf-8')
                
                # Create metadata file
                metadata = {
                    "id": page_id,
                    "title": title,
                    "slug": page.get('slug', ''),
                    "status": page.get('status', ''),
                    "date": page.get('date', ''),
                    "modified": page.get('modified', ''),
                    "cloned_at": datetime.now().isoformat()
                }
                
                metadata_file = page_dir / "metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Add to cloned pages list
                cloned_pages[str(page_id)] = {
                    "title": title,
                    "path": f"pages/page_{page_id}/index.html",
                    "metadata": f"pages/page_{page_id}/metadata.json"
                }
                
                success_count += 1
                
                # Log the clone operation
                _log_change(f"wordpress_clone/pages/page_{page_id}/index.html", "clone", f"Cloned page '{title}' from WordPress")
                
            except Exception as e:
                print(f"Warning: Failed to clone page {page.get('id', 'unknown')}: {e}")
                continue
        
        # Create manifest file
        manifest = {
            "site_url": "https://lawyerincorporated.com",
            "cloned_at": datetime.now().isoformat(),
            "pages": cloned_pages,
            "posts": {},  # Could be extended to include posts
            "theme_css": "css/theme.css",
            "custom_css": ""
        }
        
        manifest_file = clone_dir / "manifest.json"
        
        # Write manifest atomically
        temp_manifest = manifest_file.with_suffix('.tmp')
        with open(temp_manifest, 'w') as f:
            json.dump(manifest, f, indent=2)
        temp_manifest.replace(manifest_file)
        
        # Trigger UI refresh
        _refresh_streamlit_interface()
        
        result = f"✅ **WordPress site cloned successfully!**\n\n"
        result += f"📊 **Summary:**\n"
        result += f"- {success_count} pages downloaded\n"
        result += f"- Local files created in `wordpress_clone/`\n"
        result += f"- Manifest updated with latest page list\n"
        result += f"- UI refreshed to show new pages\n\n"
        
        result += f"📝 **Cloned pages:**\n"
        for page_id, info in cloned_pages.items():
            result += f"- Page {page_id}: {info['title']}\n"
        
        result += f"\n💡 **Your local files now match WordPress exactly.**"
        
        return result
        
    except Exception as e:
        return f"❌ Error cloning WordPress site: {str(e)}"


@tool
def debug_sync_comparison(page_id: str) -> str:
    """Debug tool to show detailed sync comparison for a specific page.
    
    Args:
        page_id: The WordPress page ID to debug
        
    Returns:
        Detailed comparison of local vs WordPress content
    """
    try:
        from .wordpress_push import WordPressPush
        import json
        
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        
        if not clone_dir.exists():
            return "❌ No local WordPress clone found."
        
        # Initialize WordPress pusher
        pusher = WordPressPush(str(clone_dir))
        
        # Get WordPress content
        wp_response = pusher.wp_api.request(f"/wp/v2/pages/{page_id}")
        if wp_response.startswith("Error"):
            return f"❌ Error fetching WordPress page {page_id}: {wp_response}"
        
        wp_data = json.loads(wp_response)
        wp_content = wp_data.get('content', {}).get('rendered', '')
        
        # Get local content
        local_file = clone_dir / f"pages/page_{page_id}/index.html"
        if not local_file.exists():
            return f"❌ Local file not found: {local_file}"
        
        local_html = local_file.read_text()
        
        # Parse and extract content like the sync system does
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(local_html, 'html.parser')
        
        content_div = soup.find('div', class_='page-content')
        if content_div:
            local_content = content_div.decode_contents()
            extraction_method = "page-content div"
        else:
            body = soup.find('body')
            if body:
                local_content = body.decode_contents()
                extraction_method = "body content"
            else:
                local_content = local_html
                extraction_method = "entire HTML"
        
        # Normalize content like the sync system does
        wp_normalized = pusher.normalize_html(wp_content)
        local_normalized = pusher.normalize_html(local_content)
        
        # Build debug report
        result = f"🔍 **Sync Debug Report for Page {page_id}**\n\n"
        result += f"**WordPress Title:** {wp_data.get('title', {}).get('rendered', 'Unknown')}\n"
        result += f"**Local File:** {local_file}\n"
        result += f"**Content Extraction:** {extraction_method}\n\n"
        
        result += f"**WordPress Content** ({len(wp_content)} chars):\n"
        result += f"```\n{wp_content[:200]}{'...' if len(wp_content) > 200 else ''}\n```\n\n"
        
        result += f"**Local Content** ({len(local_content)} chars):\n"
        result += f"```\n{local_content[:200]}{'...' if len(local_content) > 200 else ''}\n```\n\n"
        
        result += f"**Normalized WordPress** ({len(wp_normalized)} chars):\n"
        result += f"```\n{wp_normalized[:200]}{'...' if len(wp_normalized) > 200 else ''}\n```\n\n"
        
        result += f"**Normalized Local** ({len(local_normalized)} chars):\n"
        result += f"```\n{local_normalized[:200]}{'...' if len(local_normalized) > 200 else ''}\n```\n\n"
        
        if wp_normalized == local_normalized:
            result += "✅ **MATCH**: Content is identical after normalization"
        else:
            result += "❌ **DIFFERENT**: Content differs after normalization"
            
            # Show first difference
            import difflib
            diff = list(difflib.unified_diff(
                wp_normalized.splitlines(keepends=True),
                local_normalized.splitlines(keepends=True),
                fromfile='WordPress',
                tofile='Local',
                n=3
            ))
            
            if diff:
                result += f"\n\n**First differences:**\n```\n"
                result += "".join(diff[:20])  # Show first 20 lines of diff
                if len(diff) > 20:
                    result += "...\n"
                result += "```"
        
        return result
        
    except Exception as e:
        return f"❌ Debug error: {str(e)}"


@tool
def migrate_to_v2_sync_system() -> str:
    """Migrate existing WordPress clone to V2 two-file system.
    
    Creates clone.html files as snapshots of current WordPress state.
    
    Returns:
        Migration status and results
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        sync = WordPressSyncV2(str(PROJECT_ROOT / "wordpress_clone"))
        result = sync.migrate_existing_structure()
        
        return f"🔄 **Migration to V2 Sync System**\n\n{result}\n\nThe system now uses:\n- `clone.html` - WordPress snapshot (reference)\n- `index.html` - Working copy (editable)\n\nUse `clone_wordpress_site_v2` for a fresh clone with the new system."
        
    except Exception as e:
        return f"❌ Migration error: {str(e)}"


@tool 
def clone_wordpress_site_v2() -> str:
    """Clone WordPress site using the new V2 two-file system.
    
    PRESERVES local changes - if you have local edits, they won't be overwritten.
    WordPress snapshots (clone.html) are always updated.
    
    Returns:
        Detailed clone results and any conflicts detected
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        sync = WordPressSyncV2(str(PROJECT_ROOT / "wordpress_clone"))
        # Use default overwrite_local=False to preserve local changes
        result = sync.clone_from_wordpress(overwrite_local=False)
        
        # Don't clear change log if conflicts were detected (preserve local change history)
        if "CONFLICTS DETECTED" not in result:
            # Only clear change log if no conflicts (clean clone)
            change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
            if change_log_file.exists():
                change_log_file.unlink()
            result += f"\n\n💡 **Change tracking reset** - starting fresh with V2 system."
        else:
            result += f"\n\n💡 **Change tracking preserved** - conflicts detected, keeping local change history."
        
        # Trigger UI refresh
        _refresh_streamlit_interface()
        
        return result
        
    except Exception as e:
        return f"❌ Clone error: {str(e)}"


@tool
def force_overwrite_from_wordpress() -> str:
    """Force overwrite local changes with WordPress content (DESTRUCTIVE).
    
    WARNING: This will destroy all local changes and replace them with WordPress content.
    Use this when you want to discard local changes and start fresh from WordPress.
    
    Returns:
        Results of force overwrite operation
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        sync = WordPressSyncV2(str(PROJECT_ROOT / "wordpress_clone"))
        # Use overwrite_local=True to destroy local changes
        result = sync.clone_from_wordpress(overwrite_local=True)
        
        # Clear change log since we're starting fresh
        change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
        if change_log_file.exists():
            change_log_file.unlink()
        
        # Trigger UI refresh
        _refresh_streamlit_interface()
        
        result += f"\n\n⚠️ **ALL LOCAL CHANGES DISCARDED** - starting fresh from WordPress."
        
        return result
        
    except Exception as e:
        return f"❌ Force overwrite error: {str(e)}"


@tool
def check_sync_status_v2() -> str:
    """Check sync status using V2 file comparison system.
    
    Compares index.html (working copy) to clone.html (WordPress snapshot) for each page.
    Much more reliable than API-based comparison.
    
    Returns:
        Detailed sync status report
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        clone_dir = PROJECT_ROOT / "wordpress_clone"
        if not clone_dir.exists():
            return "❌ No WordPress clone found. Use `clone_wordpress_site_v2` first."
        
        sync = WordPressSyncV2(str(clone_dir))
        status = sync.sync_status_v2()
        
        result = "🔍 **WordPress Sync Status (V2 File Comparison)**\n\n"
        
        if status["status"] == "synced":
            result += "✅ **PERFECTLY SYNCED**\n"
            result += "All working copies match their WordPress snapshots.\n"
            result += "No local changes detected.\n"
        else:
            result += f"🔄 **LOCAL CHANGES DETECTED**\n"
            result += f"{status['message']}\n\n"
            
            result += "📝 **Changed pages:**\n"
            for change in status["changes"]:
                result += f"• Page {change['page_id']}: {change['title']}\n"
                result += f"  Working copy differs from WordPress snapshot\n"
            
            result += f"\n💡 Use `show_page_diff_v2` to see specific changes."
            result += f"\n💡 Use `push_changes_v2` to upload changes to WordPress."
        
        return result
        
    except Exception as e:
        return f"❌ Sync check error: {str(e)}"


@tool
def show_page_diff_v2(page_id: str) -> str:
    """Show differences between working copy and WordPress snapshot for a specific page.
    
    Args:
        page_id: WordPress page ID to compare
        
    Returns:
        Detailed diff showing what changed
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        sync = WordPressSyncV2(str(PROJECT_ROOT / "wordpress_clone"))
        return sync.show_diff_v2(page_id)
        
    except Exception as e:
        return f"❌ Diff error: {str(e)}"


@tool
def push_changes_v2(page_ids: str = "all") -> str:
    """Push local changes to WordPress using V2 system with verification.
    
    Pushes changes and then re-downloads to verify the push was successful.
    
    Args:
        page_ids: Comma-separated page IDs or 'all' for all changed pages
        
    Returns:
        Push results with verification status
    """
    try:
        # Try different import approaches
        try:
            from .wordpress_sync_v2 import WordPressSyncV2
        except ImportError:
            try:
                from backend.wordpress_sync_v2 import WordPressSyncV2
            except ImportError:
                sys.path.append(str(PROJECT_ROOT / "backend"))
                from wordpress_sync_v2 import WordPressSyncV2
        
        import json
        
        sync = WordPressSyncV2(str(PROJECT_ROOT / "wordpress_clone"))
        
        # Get changed pages
        status = sync.sync_status_v2()
        
        if status["status"] == "synced":
            return "✅ No changes to push - all files are already in sync."
        
        changes = status["changes"]
        
        # Filter by specific page IDs if requested
        if page_ids.lower() != "all":
            try:
                requested_ids = [id.strip() for id in page_ids.split(",")]
                changes = [c for c in changes if c["page_id"] in requested_ids]
            except:
                return "❌ Invalid page ID format. Use comma-separated IDs or 'all'."
        
        if not changes:
            return "❌ No matching changes found to push."
        
        # Push each page
        results = []
        success_count = 0
        
        for change in changes:
            page_id = change["page_id"]
            title = change["title"]
            
            print(f"Processing page {page_id}: {title}")
            
            try:
                if sync.push_page_v2(page_id, dry_run=False):
                    success_count += 1
                    results.append(f"✅ {title} (ID: {page_id})")
                    
                    # Log successful push
                    _log_change(f"wordpress_clone/pages/page_{page_id}/index.html", "pushed", f"Successfully pushed '{title}' to WordPress")
                else:
                    results.append(f"❌ {title} (ID: {page_id}) - Push failed")
            except Exception as push_error:
                results.append(f"❌ {title} (ID: {page_id}) - Error: {str(push_error)}")
        
        # Build result message
        result = f"📤 **Push Results: {success_count}/{len(changes)} pages updated**\n\n"
        
        for res in results:
            result += f"{res}\n"
        
        if success_count > 0:
            result += f"\n✅ Successfully pushed pages have been verified against WordPress."
            result += f"\n📁 Old WordPress snapshots archived in `old/` folder."
            
            # Mark change log entries as pushed (direct function call to avoid deprecation warning)
            try:
                change_log_file = PROJECT_ROOT / "temp" / "change_log.json"
                if change_log_file.exists():
                    with open(change_log_file, 'r') as f:
                        change_data = json.load(f)
                    
                    # Mark all changes as pushed
                    for change in change_data:
                        change["pushed"] = True
                    
                    # Save updated changes
                    with open(change_log_file, 'w') as f:
                        json.dump(change_data, f, indent=2)
                    
                    result += f"\n📝 All changes marked as pushed in change log."
                    
            except Exception as e:
                result += f"\n⚠️ Warning: Could not update change log: {str(e)}"
        
        # Force UI refresh by calling the function directly
        try:
            # Create refresh command
            refresh_result = _refresh_streamlit_interface()
            cache_result = _clear_ui_cache()
            
            # Also force a complete UI refresh
            force_refresh_result = force_ui_refresh()
            
            result += f"\n🔄 UI refreshed: {refresh_result}"
            result += f"\n🔄 Cache cleared: {cache_result}"
            result += f"\n🔄 {force_refresh_result}"
        except Exception as e:
            result += f"\n⚠️ Warning: UI refresh failed: {str(e)}"
        
        return result
        
    except Exception as e:
        return f"❌ Push error: {str(e)}"


def get_clone_history_v2(page_id: str) -> str:
    """Get the history of all timestamped clone versions for a page
    
    Args:
        page_id: WordPress page ID to check history for
        
    Returns:
        Formatted string showing all clone versions with timestamps
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        sync = WordPressSyncV2()
        
        history = sync.get_clone_history(page_id)
        
        if not history:
            return f"📝 No clone history found for page {page_id}"
        
        result = f"📅 **Clone History for Page {page_id}:**\n\n"
        
        for i, entry in enumerate(history):
            is_current = i == 0  # First entry is most recent
            marker = "🟢 CURRENT" if is_current else "  "
            
            result += f"{marker} **{entry['date']} {entry['time']}** ({entry['operation']})\n"
            result += f"   └─ File: {entry['timestamp']}.html ({entry['size']} bytes)\n"
            if not is_current:
                result += f"   └─ Use `restore_from_clone_v2('{page_id}', '{entry['timestamp']}')` to restore\n"
            result += "\n"
        
        result += "💡 The most recent clone reflects the current WordPress state.\n"
        result += "💡 You can restore index.html from any previous clone version.\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error getting clone history: {str(e)}"


def restore_from_clone_v2(page_id: str, timestamp: str) -> str:
    """Restore index.html from a specific timestamped clone version
    
    Args:
        page_id: WordPress page ID
        timestamp: Timestamp of clone to restore from (YYYYMMDD_HHMMSS format)
        
    Returns:
        Result message indicating success or failure
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        sync = WordPressSyncV2()
        
        result = sync.restore_from_clone(page_id, timestamp)
        
        # Log this restoration
        log_change(
            f"pages/page_{page_id}/index.html",
            f"Restored from clone timestamp {timestamp}",
            "restore"
        )
        
        return result
        
    except Exception as e:
        return f"❌ Error restoring from clone: {str(e)}"


def verify_work_quality(page_id: str, original_request: str) -> str:
    """Verify that recent changes to a page match the original user request
    
    Args:
        page_id: WordPress page ID that was modified
        original_request: The original user request to compare against
        
    Returns:
        Detailed verification report comparing actual output to requested changes
    """
    try:
        from .wordpress_sync_v2 import WordPressSyncV2
        
        sync = WordPressSyncV2()
        
        # Get the current state and differences
        diff_result = sync.show_diff_v2(page_id)
        
        # Read the current content of the modified page
        page_dir = Path("wordpress_clone") / f"pages/page_{page_id}"
        index_file = page_dir / "index.html"
        
        if not index_file.exists():
            return f"❌ Cannot verify: index.html not found for page {page_id}"
        
        current_content = index_file.read_text(encoding='utf-8')
        
        # Create verification report
        report = f"""🔍 **WORK VERIFICATION REPORT for Page {page_id}**

📋 **Original Request:**
{original_request}

📄 **Current Page Content:**
{current_content[:1000]}{'...' if len(current_content) > 1000 else ''}

🔄 **Changes Made:**
{diff_result}

⚠️ **VERIFICATION REQUIRED:**
Please carefully compare the current page content above with the original request.

**Checklist:**
- [ ] Does the output fulfill ALL parts of the original request?
- [ ] Are fonts/styles preserved as requested?
- [ ] Is the content layout correct (single line vs multiple lines)?
- [ ] Are colors, spacing, and visual elements as requested?
- [ ] Is the content complete (no missing words/elements)?

If ANY item above is not satisfied, you MUST make corrections immediately using write_file.
After corrections, run verify_work_quality again to ensure the fix worked.
"""
        
        return report
        
    except Exception as e:
        return f"❌ Verification failed: {e}"


@tool
def clear_circuit_breaker() -> str:
    """Clear the circuit breaker cache to allow retrying previously failed operations.
    
    Use this if you need to retry an operation that was blocked by the circuit breaker.
    
    Returns:
        Success message
    """
    try:
        # Import the global task cache
        from backend.main import task_cache
        
        failed_count = len(task_cache.failed_operations)
        task_cache.failed_operations.clear()
        
        return f"✅ Circuit breaker cleared - {failed_count} failed operations removed from cache"
        
    except Exception as e:
        return f"❌ Error clearing circuit breaker: {str(e)}"


@tool
def force_ui_refresh() -> str:
    """Force a complete refresh of the UI by clearing all caches and creating refresh commands.
    
    Use this after push operations or any changes that should immediately update the UI.
    
    Returns:
        Success message
    """
    try:
        temp_dir = PROJECT_ROOT / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # Create multiple refresh commands to ensure UI updates
        commands = [
            {
                "action": "force_refresh", 
                "timestamp": datetime.now().isoformat(),
                "clear_cache": True,
                "refresh_sync": True
            },
            {
                "action": "clear_all_cache",
                "timestamp": datetime.now().isoformat(),
                "target": "all"
            }
        ]
        
        # Write multiple command files
        for i, command in enumerate(commands):
            command_file = temp_dir / f"force_refresh_{i}.json"
            with open(command_file, 'w') as f:
                json.dump(command, f)
        
        # Also create the standard refresh files
        refresh_result = _refresh_streamlit_interface()
        cache_result = _clear_ui_cache()
        
        return f"✅ Complete UI refresh triggered - all caches cleared and sync status will update immediately"
        
    except Exception as e:
        return f"❌ Error forcing UI refresh: {str(e)}"


@tool
def deploy_page_to_netlify(page_id: str) -> str:
    """Deploy a specific page to Netlify via Git push.
    
    This replaces the WordPress push functionality. The page will be copied from
    the local wordpress_clone directory to the deploy directory and automatically
    committed and pushed to trigger a Netlify deployment.
    
    Args:
        page_id: The page ID to deploy (e.g., '1', '53')
    
    Returns:
        Success message with deployment details
    """
    try:
        from backend.netlify_deploy import deploy_page_to_netlify as deploy_func
        return deploy_func(page_id)
    except Exception as e:
        return f"❌ Error importing Netlify deploy: {str(e)}"


@tool
def deploy_all_to_netlify() -> str:
    """Deploy all pages to Netlify via Git push.
    
    This replaces the WordPress push functionality. All pages will be copied from
    the local wordpress_clone directory to the deploy directory and automatically
    committed and pushed to trigger a Netlify deployment.
    
    Returns:
        Success message with deployment details
    """
    try:
        from backend.netlify_deploy import deploy_all_to_netlify as deploy_func
        return deploy_func()
    except Exception as e:
        return f"❌ Error importing Netlify deploy: {str(e)}"


@tool
def check_netlify_deploy_status() -> str:
    """Check the current Netlify deployment status.
    
    Shows what files are ready to deploy and if there are any uncommitted changes.
    
    Returns:
        Status message with deployment information
    """
    try:
        from backend.netlify_deploy import check_netlify_deploy_status as status_func
        return status_func()
    except Exception as e:
        return f"❌ Error checking deploy status: {str(e)}" 