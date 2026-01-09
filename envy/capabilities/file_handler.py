"""
ENVY File Handler
=================
Handles file uploads, processing, and storage for documents, images, and code files.
Supports:
- Documents: PDF, DOCX, TXT, MD, CSV, JSON
- Images: PNG, JPG, JPEG, GIF, WEBP, SVG
- Code: PY, JS, TS, JSX, TSX, HTML, CSS, SQL
"""

import os
import hashlib
import mimetypes
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Classification of uploaded files"""
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class UploadedFile:
    """Represents a processed uploaded file"""
    id: str
    filename: str
    file_type: FileType
    mime_type: str
    size_bytes: int
    content: Optional[str] = None  # Text content or base64 for images
    path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    chunks: List[str] = field(default_factory=list)  # For RAG chunking


# File type mappings
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.sql', '.sh', '.bash', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp', '.rb', '.php'}

# Max file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


class FileHandler:
    """
    Manages file uploads for ENVY.
    Processes files for context injection, vision analysis, and artifact rendering.
    """
    
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.files: Dict[str, UploadedFile] = {}
        self._load_existing_files()
    
    def _load_existing_files(self):
        """Load metadata for existing files in upload directory"""
        # In a production system, this would load from a database
        pass
    
    def _classify_file(self, mime_type: str, filename: str) -> FileType:
        """Classify file type based on mime type and extension"""
        ext = Path(filename).suffix.lower()
        
        if ext in DOCUMENT_EXTENSIONS:
            return FileType.DOCUMENT
        elif ext in IMAGE_EXTENSIONS:
            return FileType.IMAGE
        elif ext in CODE_EXTENSIONS:
            return FileType.CODE
        elif mime_type:
            if mime_type.startswith('image/'):
                return FileType.IMAGE
            elif mime_type.startswith('text/'):
                return FileType.CODE if ext in CODE_EXTENSIONS else FileType.DOCUMENT
            elif 'pdf' in mime_type or 'document' in mime_type:
                return FileType.DOCUMENT
        
        return FileType.UNKNOWN
    
    def _generate_file_id(self, file_bytes: bytes, filename: str) -> str:
        """Generate unique file ID from content hash"""
        hasher = hashlib.sha256()
        hasher.update(file_bytes[:4096])  # Hash first 4KB for speed
        hasher.update(filename.encode())
        return hasher.hexdigest()[:16]
    
    async def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF file"""
        try:
            from PyPDF2 import PdfReader
            from io import BytesIO
            
            reader = PdfReader(BytesIO(file_bytes))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("PyPDF2 not installed, PDF text extraction unavailable")
            return "[PDF content - install PyPDF2 for extraction]"
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return f"[Error extracting PDF: {str(e)}]"
    
    async def _extract_text_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document
            from io import BytesIO
            
            doc = Document(BytesIO(file_bytes))
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("python-docx not installed, DOCX text extraction unavailable")
            return "[DOCX content - install python-docx for extraction]"
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return f"[Error extracting DOCX: {str(e)}]"
    
    async def _extract_text(self, file_bytes: bytes, mime_type: str, filename: str) -> str:
        """Extract text content based on file type"""
        ext = Path(filename).suffix.lower()
        
        if ext == '.pdf' or 'pdf' in mime_type:
            return await self._extract_text_from_pdf(file_bytes)
        elif ext == '.docx' or 'wordprocessing' in mime_type:
            return await self._extract_text_from_docx(file_bytes)
        elif ext in {'.json'}:
            try:
                import json
                parsed = json.loads(file_bytes.decode('utf-8'))
                return json.dumps(parsed, indent=2)
            except:
                return file_bytes.decode('utf-8', errors='replace')
        elif ext in {'.csv'}:
            return file_bytes.decode('utf-8', errors='replace')
        else:
            # Plain text files
            return file_bytes.decode('utf-8', errors='replace')
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for RAG"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    async def process_upload(self, file_bytes: bytes, filename: str) -> UploadedFile:
        """
        Process an uploaded file.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            UploadedFile with processed content
        """
        # Validate size
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Generate unique ID
        file_id = self._generate_file_id(file_bytes, filename)
        
        # Check if already processed
        if file_id in self.files:
            return self.files[file_id]
        
        # Detect type
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_type = self._classify_file(mime_type, filename)
        
        # Process based on type
        content = None
        chunks = []
        metadata = {
            "original_filename": filename,
            "extension": Path(filename).suffix.lower()
        }
        
        if file_type == FileType.IMAGE:
            # Encode as base64 for vision models
            content = base64.b64encode(file_bytes).decode('utf-8')
            metadata["encoding"] = "base64"
            metadata["image_format"] = mime_type
            
        elif file_type == FileType.DOCUMENT:
            # Extract text and chunk for RAG
            content = await self._extract_text(file_bytes, mime_type, filename)
            chunks = self._chunk_text(content)
            metadata["word_count"] = len(content.split())
            metadata["chunk_count"] = len(chunks)
            
        elif file_type == FileType.CODE:
            # Decode as text, detect language
            content = file_bytes.decode('utf-8', errors='replace')
            language = self._detect_code_language(filename)
            metadata["language"] = language
            metadata["line_count"] = content.count('\n') + 1
            
        else:
            # Try to decode as text, fallback to base64
            try:
                content = file_bytes.decode('utf-8')
            except:
                content = base64.b64encode(file_bytes).decode('utf-8')
                metadata["encoding"] = "base64"
        
        # Save to disk
        safe_filename = f"{file_id}_{filename.replace(' ', '_')}"
        file_path = self.upload_dir / safe_filename
        file_path.write_bytes(file_bytes)
        
        # Create record
        uploaded = UploadedFile(
            id=file_id,
            filename=filename,
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            content=content,
            path=file_path,
            metadata=metadata,
            chunks=chunks
        )
        
        self.files[file_id] = uploaded
        logger.info(f"Processed file: {filename} ({file_type.value}, {len(file_bytes)} bytes)")
        
        return uploaded
    
    def _detect_code_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rb': 'ruby',
            '.php': 'php',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
        }
        ext = Path(filename).suffix.lower()
        return ext_to_lang.get(ext, 'text')
    
    def get_file(self, file_id: str) -> Optional[UploadedFile]:
        """Get file by ID"""
        return self.files.get(file_id)
    
    def get_file_content(self, file_id: str) -> Optional[str]:
        """Get file content by ID"""
        file = self.files.get(file_id)
        return file.content if file else None
    
    def get_file_bytes(self, file_id: str) -> Optional[bytes]:
        """Get raw file bytes by ID"""
        file = self.files.get(file_id)
        if file and file.path and file.path.exists():
            return file.path.read_bytes()
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file by ID"""
        file = self.files.get(file_id)
        if file:
            if file.path and file.path.exists():
                file.path.unlink()
            del self.files[file_id]
            return True
        return False
    
    def list_files(self, file_type: Optional[FileType] = None) -> List[Dict[str, Any]]:
        """List all uploaded files, optionally filtered by type"""
        files = []
        for file_id, file in self.files.items():
            if file_type and file.file_type != file_type:
                continue
            files.append({
                "id": file.id,
                "filename": file.filename,
                "type": file.file_type.value,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
                "created_at": file.created_at.isoformat(),
                "metadata": file.metadata
            })
        return files
    
    def get_context_for_llm(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get file contents formatted for LLM context injection.
        Returns list of content blocks suitable for message content.
        """
        content_blocks = []
        
        for file_id in file_ids:
            file = self.files.get(file_id)
            if not file:
                continue
            
            if file.file_type == FileType.IMAGE:
                # Return as image content block (for vision models)
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": file.mime_type,
                        "data": file.content
                    }
                })
            else:
                # Return as text content
                content_blocks.append({
                    "type": "text",
                    "text": f"--- Content from {file.filename} ---\n{file.content}\n--- End of {file.filename} ---"
                })
        
        return content_blocks
    
    def get_images_for_vision(self, file_ids: List[str] = None) -> List[Tuple[str, str]]:
        """
        Get image files formatted for vision analysis.
        Returns list of (base64_data, mime_type) tuples.
        """
        images = []
        target_files = file_ids or list(self.files.keys())
        
        for file_id in target_files:
            file = self.files.get(file_id)
            if file and file.file_type == FileType.IMAGE:
                images.append((file.content, file.mime_type))
        
        return images
    
    def clear_all(self):
        """Clear all uploaded files"""
        for file in list(self.files.values()):
            if file.path and file.path.exists():
                file.path.unlink()
        self.files.clear()
        logger.info("Cleared all uploaded files")


# Global file handler instance
_file_handler: Optional[FileHandler] = None


def get_file_handler() -> FileHandler:
    """Get the global file handler instance"""
    global _file_handler
    if _file_handler is None:
        _file_handler = FileHandler()
    return _file_handler
