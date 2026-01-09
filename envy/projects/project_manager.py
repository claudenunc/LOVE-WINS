"""
ENVY Project Manager
====================
Core project management for persistent workspaces.

Provides:
- CRUD operations for projects
- File management within projects
- Context snapshots for LLM injection
- Supabase backend with local fallback
"""

import os
import json
import uuid
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# Try Supabase, fallback to local
try:
    from supabase import Client
except ImportError:
    Client = None


class ProjectStatus(Enum):
    """Project lifecycle status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class ProjectSettings:
    """Project-level configuration"""
    language_hints: List[str] = field(default_factory=list)  # ["python", "typescript"]
    framework_hints: List[str] = field(default_factory=list)  # ["fastapi", "react"]
    default_persona: Optional[str] = None  # Preferred ENVY persona for this project
    auto_embed: bool = True  # Automatically embed files on upload
    max_context_files: int = 10  # Max files to include in context
    context_strategy: str = "relevance"  # "relevance" | "recent" | "manual"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectSettings':
        return cls(**data) if data else cls()


@dataclass
class ProjectFile:
    """A file within a project"""
    id: str
    path: str  # Virtual path within project, e.g., "src/main.py"
    filename: str
    content: Optional[str] = None  # Text content (stored separately for large files)
    content_hash: Optional[str] = None
    mime_type: str = "text/plain"
    size_bytes: int = 0
    is_embedded: bool = False  # Has vector embedding
    embedding_id: Optional[str] = None  # Reference to vector store
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectFile':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class Project:
    """A persistent project workspace"""
    id: str
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    files: Dict[str, ProjectFile] = field(default_factory=dict)  # path -> ProjectFile
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    context_snapshot: List[str] = field(default_factory=list)  # Pre-computed context file paths
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Tags, custom data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'files': {path: f.to_dict() for path, f in self.files.items()},
            'settings': self.settings.to_dict(),
            'context_snapshot': self.context_snapshot,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            status=ProjectStatus(data.get('status', 'active')),
            files={
                path: ProjectFile.from_dict(f) 
                for path, f in data.get('files', {}).items()
            },
            settings=ProjectSettings.from_dict(data.get('settings', {})),
            context_snapshot=data.get('context_snapshot', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {})
        )
    
    def get_file_count(self) -> int:
        return len(self.files)
    
    def get_total_size(self) -> int:
        return sum(f.size_bytes for f in self.files.values())
    
    def list_paths(self) -> List[str]:
        return sorted(self.files.keys())


class LocalProjectStore:
    """Local file-based project storage"""
    
    def __init__(self, base_dir: str = "./projects_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_dir / "projects_index.json"
        self._load_index()
    
    def _load_index(self):
        """Load project index from disk"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}
    
    def _save_index(self):
        """Save project index to disk"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def _project_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}.json"
    
    def _files_dir(self, project_id: str) -> Path:
        path = self.base_dir / project_id / "files"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    async def create(self, project: Project) -> Project:
        """Create a new project"""
        # Save to index
        self.index[project.id] = {
            'name': project.name,
            'status': project.status.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }
        self._save_index()
        
        # Save project data
        with open(self._project_path(project.id), 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        return project
    
    async def get(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        path = self._project_path(project_id)
        if not path.exists():
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        return Project.from_dict(data)
    
    async def update(self, project: Project) -> Project:
        """Update an existing project"""
        project.updated_at = datetime.now()
        
        # Update index
        self.index[project.id] = {
            'name': project.name,
            'status': project.status.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }
        self._save_index()
        
        # Save project data
        with open(self._project_path(project.id), 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        return project
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project"""
        if project_id not in self.index:
            return False
        
        # Remove from index
        del self.index[project_id]
        self._save_index()
        
        # Remove project file
        path = self._project_path(project_id)
        if path.exists():
            path.unlink()
        
        return True
    
    async def list_all(self, status: Optional[ProjectStatus] = None) -> List[Dict[str, Any]]:
        """List all projects"""
        results = []
        for pid, info in self.index.items():
            if status and info.get('status') != status.value:
                continue
            results.append({
                'id': pid,
                'name': info['name'],
                'status': info['status'],
                'created_at': info['created_at'],
                'updated_at': info['updated_at']
            })
        return sorted(results, key=lambda x: x['updated_at'], reverse=True)
    
    async def save_file_content(self, project_id: str, file_id: str, content: bytes) -> str:
        """Save file content to disk, return path"""
        files_dir = self._files_dir(project_id)
        file_path = files_dir / file_id
        with open(file_path, 'wb') as f:
            f.write(content)
        return str(file_path)
    
    async def get_file_content(self, project_id: str, file_id: str) -> Optional[bytes]:
        """Get file content from disk"""
        file_path = self._files_dir(project_id) / file_id
        if not file_path.exists():
            return None
        with open(file_path, 'rb') as f:
            return f.read()


class SupabaseProjectStore:
    """Supabase-backed project storage"""
    
    def __init__(self, client: Client):
        self.client = client
        self.table = "projects"
        self.files_bucket = "project-files"
    
    async def create(self, project: Project) -> Project:
        """Create a new project in Supabase"""
        data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'settings': project.settings.to_dict(),
            'context_snapshot': project.context_snapshot,
            'metadata': project.metadata,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }
        
        self.client.table(self.table).insert(data).execute()
        return project
    
    async def get(self, project_id: str) -> Optional[Project]:
        """Get a project from Supabase"""
        response = self.client.table(self.table).select("*").eq('id', project_id).execute()
        
        if not response.data:
            return None
        
        row = response.data[0]
        
        # Get files for this project
        files_response = self.client.table("project_files").select("*").eq('project_id', project_id).execute()
        files = {}
        for f in files_response.data or []:
            pf = ProjectFile(
                id=f['id'],
                path=f['path'],
                filename=f['filename'],
                content=f.get('content'),
                content_hash=f.get('content_hash'),
                mime_type=f.get('mime_type', 'text/plain'),
                size_bytes=f.get('size_bytes', 0),
                is_embedded=f.get('is_embedded', False),
                embedding_id=f.get('embedding_id'),
                created_at=datetime.fromisoformat(f['created_at']),
                updated_at=datetime.fromisoformat(f['updated_at']),
                metadata=f.get('metadata', {})
            )
            files[pf.path] = pf
        
        return Project(
            id=row['id'],
            name=row['name'],
            description=row.get('description', ''),
            status=ProjectStatus(row.get('status', 'active')),
            files=files,
            settings=ProjectSettings.from_dict(row.get('settings', {})),
            context_snapshot=row.get('context_snapshot', []),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            metadata=row.get('metadata', {})
        )
    
    async def update(self, project: Project) -> Project:
        """Update a project in Supabase"""
        project.updated_at = datetime.now()
        
        data = {
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'settings': project.settings.to_dict(),
            'context_snapshot': project.context_snapshot,
            'metadata': project.metadata,
            'updated_at': project.updated_at.isoformat()
        }
        
        self.client.table(self.table).update(data).eq('id', project.id).execute()
        return project
    
    async def delete(self, project_id: str) -> bool:
        """Soft delete a project"""
        self.client.table(self.table).update({
            'status': ProjectStatus.DELETED.value,
            'updated_at': datetime.now().isoformat()
        }).eq('id', project_id).execute()
        return True
    
    async def list_all(self, status: Optional[ProjectStatus] = None) -> List[Dict[str, Any]]:
        """List all projects"""
        query = self.client.table(self.table).select('id, name, description, status, created_at, updated_at')
        
        if status:
            query = query.eq('status', status.value)
        else:
            query = query.neq('status', ProjectStatus.DELETED.value)
        
        response = query.order('updated_at', desc=True).execute()
        return response.data or []


class ProjectManager:
    """
    Main interface for project management.
    
    Usage:
        manager = ProjectManager()
        project = await manager.create_project("My App", "A cool app")
        await manager.add_file(project.id, "src/main.py", "print('hello')")
        project = await manager.get_project(project.id)
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        if supabase_client:
            self.store = SupabaseProjectStore(supabase_client)
            self.using_supabase = True
        else:
            self.store = LocalProjectStore()
            self.using_supabase = False
        
        # Cache for active project
        self._active_project_id: Optional[str] = None
        self._project_cache: Dict[str, Project] = {}
    
    def _generate_id(self) -> str:
        """Generate a unique project ID"""
        return str(uuid.uuid4())[:8]
    
    def _generate_file_id(self, content: bytes) -> str:
        """Generate file ID from content hash"""
        return hashlib.sha256(content).hexdigest()[:16]
    
    # ========================================
    # Project CRUD
    # ========================================
    
    async def create_project(
        self,
        name: str,
        description: str = "",
        settings: Optional[ProjectSettings] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Project:
        """Create a new project"""
        project = Project(
            id=self._generate_id(),
            name=name,
            description=description,
            settings=settings or ProjectSettings(),
            metadata=metadata or {}
        )
        
        created = await self.store.create(project)
        self._project_cache[created.id] = created
        return created
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        if project_id in self._project_cache:
            return self._project_cache[project_id]
        
        project = await self.store.get(project_id)
        if project:
            self._project_cache[project_id] = project
        return project
    
    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[ProjectSettings] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Project]:
        """Update project metadata"""
        project = await self.get_project(project_id)
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if settings is not None:
            project.settings = settings
        if metadata is not None:
            project.metadata.update(metadata)
        
        updated = await self.store.update(project)
        self._project_cache[project_id] = updated
        return updated
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        if project_id in self._project_cache:
            del self._project_cache[project_id]
        return await self.store.delete(project_id)
    
    async def list_projects(self, status: Optional[ProjectStatus] = None) -> List[Dict[str, Any]]:
        """List all projects"""
        return await self.store.list_all(status)
    
    async def archive_project(self, project_id: str) -> Optional[Project]:
        """Archive a project"""
        project = await self.get_project(project_id)
        if not project:
            return None
        
        project.status = ProjectStatus.ARCHIVED
        return await self.store.update(project)
    
    # ========================================
    # File Operations
    # ========================================
    
    async def add_file(
        self,
        project_id: str,
        path: str,
        content: str,
        mime_type: str = "text/plain",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ProjectFile]:
        """Add or update a file in a project"""
        project = await self.get_project(project_id)
        if not project:
            return None
        
        content_bytes = content.encode('utf-8')
        file_id = self._generate_file_id(content_bytes)
        
        # Handle path
        path = path.lstrip('/')  # Normalize path
        filename = path.split('/')[-1]
        
        # Create file record
        pf = ProjectFile(
            id=file_id,
            path=path,
            filename=filename,
            content=content,
            content_hash=hashlib.sha256(content_bytes).hexdigest(),
            mime_type=mime_type,
            size_bytes=len(content_bytes),
            metadata=metadata or {}
        )
        
        # Add to project
        project.files[path] = pf
        await self.store.update(project)
        
        return pf
    
    async def get_file(self, project_id: str, path: str) -> Optional[ProjectFile]:
        """Get a file from a project"""
        project = await self.get_project(project_id)
        if not project:
            return None
        return project.files.get(path)
    
    async def delete_file(self, project_id: str, path: str) -> bool:
        """Delete a file from a project"""
        project = await self.get_project(project_id)
        if not project or path not in project.files:
            return False
        
        del project.files[path]
        await self.store.update(project)
        return True
    
    async def list_files(self, project_id: str) -> List[Dict[str, Any]]:
        """List all files in a project"""
        project = await self.get_project(project_id)
        if not project:
            return []
        
        return [
            {
                'id': f.id,
                'path': f.path,
                'filename': f.filename,
                'mime_type': f.mime_type,
                'size_bytes': f.size_bytes,
                'is_embedded': f.is_embedded,
                'updated_at': f.updated_at.isoformat()
            }
            for f in project.files.values()
        ]
    
    async def move_file(self, project_id: str, old_path: str, new_path: str) -> bool:
        """Move/rename a file within a project"""
        project = await self.get_project(project_id)
        if not project or old_path not in project.files:
            return False
        
        file = project.files.pop(old_path)
        file.path = new_path
        file.filename = new_path.split('/')[-1]
        file.updated_at = datetime.now()
        project.files[new_path] = file
        
        await self.store.update(project)
        return True
    
    # ========================================
    # Context Management
    # ========================================
    
    async def get_context_files(self, project_id: str, max_files: Optional[int] = None) -> List[ProjectFile]:
        """
        Get files for LLM context injection.
        Uses project's context_snapshot if available, otherwise returns most recent files.
        """
        project = await self.get_project(project_id)
        if not project:
            return []
        
        max_files = max_files or project.settings.max_context_files
        
        # If we have a pre-computed snapshot, use it
        if project.context_snapshot:
            files = [
                project.files[path] 
                for path in project.context_snapshot 
                if path in project.files
            ][:max_files]
        else:
            # Fallback: most recently updated files
            files = sorted(
                project.files.values(),
                key=lambda f: f.updated_at,
                reverse=True
            )[:max_files]
        
        return files
    
    async def build_context_prompt(self, project_id: str) -> str:
        """
        Build a context prompt from project files for LLM injection.
        """
        files = await self.get_context_files(project_id)
        if not files:
            return ""
        
        parts = ["--- PROJECT CONTEXT ---\n"]
        
        for f in files:
            if f.content:
                parts.append(f"### {f.path}\n```\n{f.content[:4000]}\n```\n")
        
        return "\n".join(parts)
    
    async def update_context_snapshot(
        self,
        project_id: str,
        file_paths: List[str]
    ) -> Optional[Project]:
        """
        Manually set which files should be included in context.
        """
        project = await self.get_project(project_id)
        if not project:
            return None
        
        project.context_snapshot = file_paths
        return await self.store.update(project)
    
    # ========================================
    # Active Project
    # ========================================
    
    def set_active_project(self, project_id: str):
        """Set the currently active project"""
        self._active_project_id = project_id
    
    def get_active_project_id(self) -> Optional[str]:
        """Get the currently active project ID"""
        return self._active_project_id
    
    async def get_active_project(self) -> Optional[Project]:
        """Get the currently active project"""
        if not self._active_project_id:
            return None
        return await self.get_project(self._active_project_id)


# Singleton instance
_project_manager: Optional[ProjectManager] = None


def get_project_manager(supabase_client: Optional[Client] = None) -> ProjectManager:
    """Get or create the singleton ProjectManager instance"""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(supabase_client)
    return _project_manager
