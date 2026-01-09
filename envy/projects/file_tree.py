"""
ENVY File Tree
==============
Hierarchical file structure management for projects.

Provides:
- Tree representation of project files
- Directory operations
- Path utilities
- Tree traversal and search
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Type of tree node"""
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class FileNode:
    """
    A node in the file tree.
    Can be either a file or a directory.
    """
    name: str
    node_type: NodeType
    path: str  # Full virtual path
    children: Dict[str, 'FileNode'] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # File-specific attributes
    file_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: int = 0
    is_embedded: bool = False
    
    def is_file(self) -> bool:
        return self.node_type == NodeType.FILE
    
    def is_directory(self) -> bool:
        return self.node_type == NodeType.DIRECTORY
    
    def add_child(self, node: 'FileNode'):
        """Add a child node"""
        self.children[node.name] = node
    
    def get_child(self, name: str) -> Optional['FileNode']:
        """Get a child node by name"""
        return self.children.get(name)
    
    def remove_child(self, name: str) -> bool:
        """Remove a child node"""
        if name in self.children:
            del self.children[name]
            return True
        return False
    
    def list_children(self) -> List['FileNode']:
        """Get all children sorted alphabetically, directories first"""
        dirs = []
        files = []
        for child in self.children.values():
            if child.is_directory():
                dirs.append(child)
            else:
                files.append(child)
        return sorted(dirs, key=lambda n: n.name.lower()) + sorted(files, key=lambda n: n.name.lower())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            'name': self.name,
            'type': self.node_type.value,
            'path': self.path
        }
        
        if self.is_file():
            result.update({
                'file_id': self.file_id,
                'mime_type': self.mime_type,
                'size_bytes': self.size_bytes,
                'is_embedded': self.is_embedded
            })
        
        if self.is_directory() and self.children:
            result['children'] = [child.to_dict() for child in self.list_children()]
        
        return result
    
    def flatten(self, include_dirs: bool = False) -> List['FileNode']:
        """
        Flatten the tree into a list of nodes.
        
        Args:
            include_dirs: If True, include directory nodes
        
        Returns:
            List of all nodes in depth-first order
        """
        result = []
        
        if include_dirs or self.is_file():
            result.append(self)
        
        for child in self.list_children():
            result.extend(child.flatten(include_dirs))
        
        return result


class FileTree:
    """
    Hierarchical file tree management for a project.
    
    Builds a tree structure from flat file paths and provides
    tree operations for the frontend file browser.
    
    Usage:
        tree = FileTree()
        tree.add_file("src/main.py", file_id="abc123", size_bytes=1024)
        tree.add_file("src/utils/helpers.py", file_id="def456")
        
        # Get tree for rendering
        tree_data = tree.to_dict()
        
        # Find files
        files = tree.find("*.py")
    """
    
    def __init__(self):
        self.root = FileNode(
            name="",
            node_type=NodeType.DIRECTORY,
            path=""
        )
    
    def _split_path(self, path: str) -> List[str]:
        """Split a path into components"""
        path = path.strip('/')
        if not path:
            return []
        return path.split('/')
    
    def _ensure_directory(self, path: str) -> FileNode:
        """
        Ensure all directories in the path exist.
        Returns the final directory node.
        """
        parts = self._split_path(path)
        current = self.root
        current_path = ""
        
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else part
            
            if part not in current.children:
                # Create directory
                new_dir = FileNode(
                    name=part,
                    node_type=NodeType.DIRECTORY,
                    path=current_path
                )
                current.add_child(new_dir)
            
            current = current.children[part]
        
        return current
    
    def add_file(
        self,
        path: str,
        file_id: str,
        mime_type: str = "text/plain",
        size_bytes: int = 0,
        is_embedded: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileNode:
        """
        Add a file to the tree at the given path.
        Creates intermediate directories as needed.
        """
        parts = self._split_path(path)
        if not parts:
            raise ValueError("Empty path")
        
        # Ensure parent directories exist
        filename = parts[-1]
        if len(parts) > 1:
            dir_path = '/'.join(parts[:-1])
            parent = self._ensure_directory(dir_path)
        else:
            parent = self.root
        
        # Create file node
        file_node = FileNode(
            name=filename,
            node_type=NodeType.FILE,
            path=path.strip('/'),
            file_id=file_id,
            mime_type=mime_type,
            size_bytes=size_bytes,
            is_embedded=is_embedded,
            metadata=metadata or {}
        )
        
        parent.add_child(file_node)
        return file_node
    
    def remove_file(self, path: str) -> bool:
        """Remove a file from the tree"""
        parts = self._split_path(path)
        if not parts:
            return False
        
        # Navigate to parent
        current = self.root
        for part in parts[:-1]:
            if part not in current.children:
                return False
            current = current.children[part]
        
        # Remove file
        filename = parts[-1]
        return current.remove_child(filename)
    
    def get_file(self, path: str) -> Optional[FileNode]:
        """Get a file node by path"""
        parts = self._split_path(path)
        current = self.root
        
        for part in parts:
            if part not in current.children:
                return None
            current = current.children[part]
        
        return current if current.is_file() else None
    
    def get_directory(self, path: str) -> Optional[FileNode]:
        """Get a directory node by path"""
        if not path or path == '/':
            return self.root
        
        parts = self._split_path(path)
        current = self.root
        
        for part in parts:
            if part not in current.children:
                return None
            current = current.children[part]
        
        return current if current.is_directory() else None
    
    def move(self, old_path: str, new_path: str) -> bool:
        """Move a file or directory to a new path"""
        # Get the node
        node = self.get_file(old_path) or self.get_directory(old_path)
        if not node:
            return False
        
        # Remove from old location
        old_parts = self._split_path(old_path)
        old_parent = self.root
        for part in old_parts[:-1]:
            old_parent = old_parent.children[part]
        old_parent.remove_child(old_parts[-1])
        
        # Add to new location
        new_parts = self._split_path(new_path)
        if len(new_parts) > 1:
            new_dir_path = '/'.join(new_parts[:-1])
            new_parent = self._ensure_directory(new_dir_path)
        else:
            new_parent = self.root
        
        # Update node
        node.name = new_parts[-1]
        node.path = new_path.strip('/')
        new_parent.add_child(node)
        
        return True
    
    def find(self, pattern: str, include_dirs: bool = False) -> List[FileNode]:
        """
        Find files matching a glob pattern.
        
        Supports:
        - * for any characters
        - *.py for extension matching
        - folder/* for all files in folder
        """
        import fnmatch
        
        results = []
        all_nodes = self.root.flatten(include_dirs=include_dirs)
        
        for node in all_nodes:
            if fnmatch.fnmatch(node.path, pattern) or fnmatch.fnmatch(node.name, pattern):
                results.append(node)
        
        return results
    
    def walk(self, callback: Callable[[FileNode, int], None], include_dirs: bool = True):
        """
        Walk the tree, calling callback for each node.
        
        Args:
            callback: Function(node, depth) called for each node
            include_dirs: Whether to include directories
        """
        def _walk(node: FileNode, depth: int):
            if include_dirs or node.is_file():
                callback(node, depth)
            for child in node.list_children():
                _walk(child, depth + 1)
        
        _walk(self.root, 0)
    
    def get_file_paths(self) -> List[str]:
        """Get all file paths in the tree"""
        return [node.path for node in self.root.flatten()]
    
    def get_directory_paths(self) -> List[str]:
        """Get all directory paths in the tree"""
        dirs = self.root.flatten(include_dirs=True)
        return [node.path for node in dirs if node.is_directory() and node.path]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire tree to dictionary for JSON serialization"""
        return self.root.to_dict()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics"""
        all_files = self.root.flatten()
        all_dirs = [n for n in self.root.flatten(include_dirs=True) if n.is_directory()]
        
        return {
            'total_files': len(all_files),
            'total_directories': len(all_dirs),
            'total_size_bytes': sum(f.size_bytes for f in all_files),
            'embedded_files': sum(1 for f in all_files if f.is_embedded),
            'extensions': self._count_extensions(all_files)
        }
    
    def _count_extensions(self, files: List[FileNode]) -> Dict[str, int]:
        """Count files by extension"""
        counts: Dict[str, int] = {}
        for f in files:
            ext = f.name.rsplit('.', 1)[-1] if '.' in f.name else 'no extension'
            counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
    
    def print_tree(self, indent: str = "  ") -> str:
        """Generate a text representation of the tree"""
        lines = []
        
        def _print(node: FileNode, prefix: str, is_last: bool):
            connector = "└── " if is_last else "├── "
            if node.path:  # Skip root
                icon = "📄" if node.is_file() else "📁"
                lines.append(f"{prefix}{connector}{icon} {node.name}")
            
            children = node.list_children()
            for i, child in enumerate(children):
                is_child_last = (i == len(children) - 1)
                new_prefix = prefix + ("    " if is_last else "│   ") if node.path else ""
                _print(child, new_prefix, is_child_last)
        
        _print(self.root, "", True)
        return "\n".join(lines) or "(empty)"
    
    @classmethod
    def from_project_files(cls, files: Dict[str, Any]) -> 'FileTree':
        """
        Build a FileTree from a project's files dictionary.
        
        Args:
            files: Dict mapping path -> ProjectFile or dict with file info
        """
        tree = cls()
        
        for path, file_info in files.items():
            if hasattr(file_info, 'id'):
                # ProjectFile object
                tree.add_file(
                    path=path,
                    file_id=file_info.id,
                    mime_type=file_info.mime_type,
                    size_bytes=file_info.size_bytes,
                    is_embedded=file_info.is_embedded,
                    metadata=file_info.metadata
                )
            else:
                # Dictionary
                tree.add_file(
                    path=path,
                    file_id=file_info.get('id', ''),
                    mime_type=file_info.get('mime_type', 'text/plain'),
                    size_bytes=file_info.get('size_bytes', 0),
                    is_embedded=file_info.get('is_embedded', False),
                    metadata=file_info.get('metadata', {})
                )
        
        return tree
