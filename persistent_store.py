"""
Persistent store implementation for long-term memory
"""
import json
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from langgraph.store.base import BaseStore
from langchain_core.documents import Document

class PersistentJSONStore(BaseStore):
    """A simple JSON-based persistent store for long-term memory."""
    
    def __init__(self, filename: str = "memories.json"):
        self.filename = filename
        self.data = self._load_data()
    
    async def abatch(self, items):
        """Async batch operations - not implemented for this simple store."""
        raise NotImplementedError("Async operations not supported")
    
    def batch(self, items):
        """Batch operations - not implemented for this simple store."""
        raise NotImplementedError("Batch operations not supported")
    
    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """Load data from JSON file."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_data(self):
        """Save data to JSON file."""
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _get_namespace_key(self, namespace: Tuple[str, ...]) -> str:
        """Convert namespace tuple to string key."""
        return "::".join(namespace)
    
    def put(self, namespace: Tuple[str, ...], key: str, value: Dict[str, Any]) -> None:
        """Store a value."""
        ns_key = self._get_namespace_key(namespace)
        if ns_key not in self.data:
            self.data[ns_key] = {}
        self.data[ns_key][key] = value
        self._save_data()
    
    def get(self, namespace: Tuple[str, ...], key: str) -> Optional[Dict[str, Any]]:
        """Get a value."""
        ns_key = self._get_namespace_key(namespace)
        if ns_key in self.data and key in self.data[ns_key]:
            return self.data[ns_key][key]
        return None
    
    def delete(self, namespace: Tuple[str, ...], key: str) -> None:
        """Delete a value."""
        ns_key = self._get_namespace_key(namespace)
        if ns_key in self.data and key in self.data[ns_key]:
            del self.data[ns_key][key]
            if not self.data[ns_key]:  # Remove empty namespace
                del self.data[ns_key]
            self._save_data()
    
    def search(self, namespace: Tuple[str, ...], query: str = "", limit: int = 10) -> List[Document]:
        """Search for values in a namespace."""
        ns_key = self._get_namespace_key(namespace)
        results = []
        
        if ns_key in self.data:
            # Simple text search - in production, you'd want vector search
            for key, value in self.data[ns_key].items():
                if not query or query.lower() in str(value).lower():
                    results.append(Document(
                        page_content=str(value),
                        metadata={"key": key, "namespace": namespace}
                    ))
                    # Create a simple object with key and value attributes
                    class Result:
                        def __init__(self, key, value):
                            self.key = key
                            self.value = value
                    
                    results[-1] = Result(key, value)
                    
        return results[:limit]