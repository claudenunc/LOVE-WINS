"""
ENVY Vector Store
=================
pgvector-backed semantic search for RAG (Retrieval Augmented Generation).

Features:
- Automatic document chunking
- Embedding via OpenAI or local models
- Similarity search with hybrid (vector + keyword) support
- Integration with Projects for project-scoped search
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

# Try importing embedding libraries
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from supabase import Client
except ImportError:
    Client = None

from ..core.config import settings


class EmbeddingModel(Enum):
    """Available embedding models"""
    OPENAI_SMALL = "text-embedding-3-small"  # 1536 dimensions, cheap
    OPENAI_LARGE = "text-embedding-3-large"  # 3072 dimensions, better
    OPENAI_ADA = "text-embedding-ada-002"  # Legacy, 1536 dimensions
    LOCAL_NOMIC = "nomic-embed-text"  # Local via Ollama


@dataclass
class DocumentChunk:
    """A chunk of a document with its embedding"""
    id: str
    project_id: Optional[str]
    file_path: str
    chunk_index: int
    content: str
    token_count: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'file_path': self.file_path,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'token_count': self.token_count,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class SearchResult:
    """Result from a vector search"""
    chunk_id: str
    file_path: str
    chunk_index: int
    content: str
    similarity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class Chunker:
    """
    Smart document chunking with configurable overlap.
    
    Uses a simple token-based approach that preserves sentence boundaries.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,  # ~1000 tokens
        chunk_overlap: int = 200,  # 200 token overlap
        min_chunk_size: int = 100  # Don't create tiny chunks
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token for English"""
        return len(text) // 4
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (simple heuristic)"""
        import re
        # Split on sentence-ending punctuation followed by space or newline
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk(self, text: str, file_path: str) -> List[DocumentChunk]:
        """
        Chunk a document into overlapping segments.
        
        Args:
            text: Full document text
            file_path: Path for metadata
        
        Returns:
            List of DocumentChunk objects
        """
        if not text or not text.strip():
            return []
        
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(file_path, chunk_index, chunk_text)
                
                chunks.append(DocumentChunk(
                    id=chunk_id,
                    project_id=None,  # Set by caller
                    file_path=file_path,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    token_count=current_tokens,
                    metadata={'sentences': len(current_chunk)}
                ))
                
                chunk_index += 1
                
                # Keep overlap sentences for next chunk
                overlap_tokens = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    s_tokens = self._estimate_tokens(s)
                    if overlap_tokens + s_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Final chunk
        if current_chunk and current_tokens >= self.min_chunk_size:
            chunk_text = ' '.join(current_chunk)
            chunk_id = self._generate_chunk_id(file_path, chunk_index, chunk_text)
            
            chunks.append(DocumentChunk(
                id=chunk_id,
                project_id=None,
                file_path=file_path,
                chunk_index=chunk_index,
                content=chunk_text,
                token_count=current_tokens,
                metadata={'sentences': len(current_chunk)}
            ))
        
        return chunks
    
    def _generate_chunk_id(self, file_path: str, index: int, content: str) -> str:
        """Generate unique chunk ID"""
        data = f"{file_path}:{index}:{content[:100]}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class Embedder:
    """
    Generate embeddings for text using OpenAI or local models.
    """
    
    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL,
        batch_size: int = 100
    ):
        self.model = model
        self.batch_size = batch_size
        self._client = None
        
        # Initialize OpenAI client if using OpenAI models
        if model.value.startswith("text-embedding") and HAS_OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = openai.AsyncOpenAI(api_key=api_key)
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """Embed a single text string"""
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else None
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed a batch of texts.
        
        Returns list of embeddings (or None for failures).
        """
        if not texts:
            return []
        
        if self.model.value.startswith("text-embedding"):
            return await self._embed_openai(texts)
        elif self.model == EmbeddingModel.LOCAL_NOMIC:
            return await self._embed_local(texts)
        else:
            return [None] * len(texts)
    
    async def _embed_openai(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Embed using OpenAI API"""
        if not self._client:
            print("[Embedder] OpenAI client not initialized")
            return [None] * len(texts)
        
        results: List[Optional[List[float]]] = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                response = await self._client.embeddings.create(
                    input=batch,
                    model=self.model.value
                )
                
                for item in response.data:
                    results.append(item.embedding)
                    
            except Exception as e:
                print(f"[Embedder] OpenAI error: {e}")
                results.extend([None] * len(batch))
        
        return results
    
    async def _embed_local(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Embed using local Ollama with nomic-embed-text"""
        import aiohttp
        
        results: List[Optional[List[float]]] = []
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        for text in texts:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{ollama_url}/api/embeddings",
                        json={"model": "nomic-embed-text", "prompt": text}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results.append(data.get("embedding"))
                        else:
                            results.append(None)
            except Exception as e:
                print(f"[Embedder] Local embedding error: {e}")
                results.append(None)
        
        return results
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for current model"""
        dims = {
            EmbeddingModel.OPENAI_SMALL: 1536,
            EmbeddingModel.OPENAI_LARGE: 3072,
            EmbeddingModel.OPENAI_ADA: 1536,
            EmbeddingModel.LOCAL_NOMIC: 768
        }
        return dims.get(self.model, 1536)


class VectorStore:
    """
    pgvector-backed vector store for semantic search.
    
    Supports:
    - Storing document chunks with embeddings
    - Similarity search (cosine distance)
    - Project-scoped search
    - Hybrid search (vector + keyword)
    
    Usage:
        store = VectorStore(supabase_client)
        
        # Index a document
        chunks = await store.index_document(
            content="Long document text...",
            file_path="docs/readme.md",
            project_id="abc123"
        )
        
        # Search
        results = await store.search(
            query="How do I configure this?",
            project_id="abc123",
            top_k=5
        )
    """
    
    def __init__(
        self,
        supabase_client: Optional[Client] = None,
        chunker: Optional[Chunker] = None,
        embedder: Optional[Embedder] = None
    ):
        self.client = supabase_client
        self.chunker = chunker or Chunker()
        self.embedder = embedder or Embedder()
        self.table = "document_chunks"
        
        # Local storage fallback
        self._local_store: Dict[str, DocumentChunk] = {}
    
    async def index_document(
        self,
        content: str,
        file_path: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Index a document: chunk it, embed it, store it.
        
        Returns the created chunks.
        """
        # Chunk the document
        chunks = self.chunker.chunk(content, file_path)
        
        if not chunks:
            return []
        
        # Set project_id
        for chunk in chunks:
            chunk.project_id = project_id
            if metadata:
                chunk.metadata.update(metadata)
        
        # Embed all chunks
        texts = [c.content for c in chunks]
        embeddings = await self.embedder.embed_batch(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Store
        if self.client:
            await self._store_supabase(chunks)
        else:
            self._store_local(chunks)
        
        return chunks
    
    async def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for relevant chunks.
        
        Args:
            query: Search query
            project_id: Optional project scope
            top_k: Number of results
            threshold: Minimum similarity (0-1)
        
        Returns:
            List of SearchResult ordered by similarity
        """
        # Embed query
        query_embedding = await self.embedder.embed_text(query)
        
        if not query_embedding:
            return []
        
        if self.client:
            return await self._search_supabase(query_embedding, project_id, top_k, threshold)
        else:
            return self._search_local(query_embedding, project_id, top_k, threshold)
    
    async def delete_document(self, file_path: str, project_id: Optional[str] = None):
        """Delete all chunks for a document"""
        if self.client:
            query = self.client.table(self.table).delete().eq('file_path', file_path)
            if project_id:
                query = query.eq('project_id', project_id)
            query.execute()
        else:
            to_delete = [
                cid for cid, chunk in self._local_store.items()
                if chunk.file_path == file_path and 
                (project_id is None or chunk.project_id == project_id)
            ]
            for cid in to_delete:
                del self._local_store[cid]
    
    async def delete_project_chunks(self, project_id: str):
        """Delete all chunks for a project"""
        if self.client:
            self.client.table(self.table).delete().eq('project_id', project_id).execute()
        else:
            to_delete = [
                cid for cid, chunk in self._local_store.items()
                if chunk.project_id == project_id
            ]
            for cid in to_delete:
                del self._local_store[cid]
    
    async def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get vector store statistics"""
        if self.client:
            query = self.client.table(self.table).select('id, file_path, token_count', count='exact')
            if project_id:
                query = query.eq('project_id', project_id)
            response = query.execute()
            
            total_chunks = response.count or 0
            total_tokens = sum(r.get('token_count', 0) for r in response.data or [])
            unique_files = len(set(r.get('file_path') for r in response.data or []))
            
            return {
                'total_chunks': total_chunks,
                'total_tokens': total_tokens,
                'unique_files': unique_files,
                'storage': 'supabase'
            }
        else:
            chunks = list(self._local_store.values())
            if project_id:
                chunks = [c for c in chunks if c.project_id == project_id]
            
            return {
                'total_chunks': len(chunks),
                'total_tokens': sum(c.token_count for c in chunks),
                'unique_files': len(set(c.file_path for c in chunks)),
                'storage': 'local'
            }
    
    async def _store_supabase(self, chunks: List[DocumentChunk]):
        """Store chunks in Supabase"""
        for chunk in chunks:
            data = {
                'id': chunk.id,
                'project_id': chunk.project_id,
                'file_path': chunk.file_path,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'token_count': chunk.token_count,
                'metadata': chunk.metadata,
                'embedding': chunk.embedding
            }
            
            self.client.table(self.table).upsert(data).execute()
    
    def _store_local(self, chunks: List[DocumentChunk]):
        """Store chunks locally"""
        for chunk in chunks:
            key = f"{chunk.project_id}:{chunk.file_path}:{chunk.chunk_index}"
            self._local_store[key] = chunk
    
    async def _search_supabase(
        self,
        query_embedding: List[float],
        project_id: Optional[str],
        top_k: int,
        threshold: float
    ) -> List[SearchResult]:
        """Search using Supabase pgvector"""
        try:
            # Use the match_project_chunks function
            response = self.client.rpc(
                'match_project_chunks',
                {
                    'query_embedding': query_embedding,
                    'target_project_id': project_id,
                    'match_count': top_k,
                    'match_threshold': threshold
                }
            ).execute()
            
            results = []
            for row in response.data or []:
                results.append(SearchResult(
                    chunk_id=row['id'],
                    file_path=row['file_path'],
                    chunk_index=row['chunk_index'],
                    content=row['content'],
                    similarity=row['similarity']
                ))
            
            return results
            
        except Exception as e:
            print(f"[VectorStore] Supabase search error: {e}")
            return []
    
    def _search_local(
        self,
        query_embedding: List[float],
        project_id: Optional[str],
        top_k: int,
        threshold: float
    ) -> List[SearchResult]:
        """Search local store using cosine similarity"""
        import math
        
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        
        # Filter chunks
        chunks = list(self._local_store.values())
        if project_id:
            chunks = [c for c in chunks if c.project_id == project_id]
        
        # Calculate similarities
        scored = []
        for chunk in chunks:
            if chunk.embedding:
                sim = cosine_similarity(query_embedding, chunk.embedding)
                if sim >= threshold:
                    scored.append((chunk, sim))
        
        # Sort and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [
            SearchResult(
                chunk_id=chunk.id,
                file_path=chunk.file_path,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=sim
            )
            for chunk, sim in scored[:top_k]
        ]


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(supabase_client: Optional[Client] = None) -> VectorStore:
    """Get or create the singleton VectorStore instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(supabase_client)
    return _vector_store
