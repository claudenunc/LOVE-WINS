"""
ENVY Projects Module
====================
Persistent project management for Claude.ai-like workspace continuity.

Features:
- Create, save, load projects across sessions
- Multi-file directory structure
- Project-level context and settings
- Integration with vector store for semantic search
"""

from .project_manager import (
    ProjectManager,
    Project,
    ProjectFile,
    ProjectSettings,
    get_project_manager
)
from .file_tree import FileTree, FileNode

__all__ = [
    'ProjectManager',
    'Project', 
    'ProjectFile',
    'ProjectSettings',
    'FileTree',
    'FileNode',
    'get_project_manager'
]
