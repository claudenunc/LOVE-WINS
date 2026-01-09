import os
from pathlib import Path
from typing import List, Optional, Union

class FileManager:
    """
    Manages file system operations for ENVY.
    """
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve path relative to root, or absolute."""
        # Check if it's an absolute path
        path = Path(file_path)
        if path.is_absolute():
            return path
        return (self.root_dir / path).resolve()

    def read_file(self, file_path: str) -> str:
        """Read content of a file."""
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File '{file_path}' not found."
            if not path.is_file():
                return f"Error: '{file_path}' is not a file."
            
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file. Creates directories if needed."""
        try:
            path = self._resolve_path(file_path)
            
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to '{file_path}'."
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def delete_file(self, file_path: str) -> str:
        """Delete a file."""
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File '{file_path}' not found."
            
            os.remove(path)
            return f"Successfully deleted '{file_path}'."
        except Exception as e:
            return f"Error deleting file: {str(e)}"

    def list_files(self, dir_path: str = ".") -> str:
        """List files in a directory."""
        try:
            path = self._resolve_path(dir_path)
            if not path.exists():
                return f"Error: Directory '{dir_path}' not found."
            if not path.is_dir():
                return f"Error: '{dir_path}' is not a directory."
            
            files = []
            for item in path.iterdir():
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                files.append(f"{prefix} {item.name}")
            
            return "\n".join(files) if files else "Directory is empty."
        except Exception as e:
            return f"Error listing files: {str(e)}"
