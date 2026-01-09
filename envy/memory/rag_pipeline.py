"""
ENVY RAG Pipeline
=================
Retrieval Augmented Generation pipeline for context-aware responses.

Features:
- Automatic document indexing on upload
- Hybrid retrieval (vector + keyword)
- Context assembly for LLM injection
- Project-scoped RAG
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .vector_store import VectorStore, SearchResult, get_vector_store
from ..core.config import settings

try:
    from supabase import Client
except ImportError:
    Client = None


@dataclass
class RAGContext:
    """Context retrieved for a query"""
    query: str
    chunks: List[SearchResult]
    total_tokens: int
    context_prompt: str
    metadata: Dict[str, Any]


class RAGPipeline:
    """
    Retrieval Augmented Generation Pipeline.
    
    Handles:
    1. Document ingestion and indexing
    2. Query-time retrieval
    3. Context assembly for LLM
    4. Re-ranking (optional)
    
    Usage:
        rag = RAGPipeline(supabase_client)
        
        # Index a document
        await rag.index_file(
            content="Document content...",
            file_path="docs/guide.md",
            project_id="abc123"
        )
        
        # Retrieve context for a query
        context = await rag.retrieve(
            query="How do I get started?",
            project_id="abc123"
        )
        
        # Use context in LLM call
        system_prompt = f"Use this context:\\n{context.context_prompt}"
    """
    
    def __init__(
        self,
        supabase_client: Optional[Client] = None,
        vector_store: Optional[VectorStore] = None
    ):
        self.vector_store = vector_store or get_vector_store(supabase_client)
        
        # Configuration
        self.max_context_tokens = 8000  # Max tokens to include in context
        self.top_k_default = 5  # Default number of chunks to retrieve
        self.similarity_threshold = 0.6  # Minimum similarity to include
    
    async def index_file(
        self,
        content: str,
        file_path: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index a file's content for RAG retrieval.
        
        Args:
            content: File text content
            file_path: Path within project
            project_id: Project scope
            metadata: Additional metadata (e.g., file type, author)
        
        Returns:
            Number of chunks created
        """
        # Remove existing chunks for this file
        await self.vector_store.delete_document(file_path, project_id)
        
        # Index new content
        chunks = await self.vector_store.index_document(
            content=content,
            file_path=file_path,
            project_id=project_id,
            metadata=metadata
        )
        
        return len(chunks)
    
    async def index_project_files(
        self,
        files: Dict[str, str],  # path -> content
        project_id: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """
        Index multiple files for a project.
        
        Returns dict of path -> chunk count.
        """
        results = {}
        total = len(files)
        
        for i, (path, content) in enumerate(files.items()):
            if content and isinstance(content, str):
                chunk_count = await self.index_file(
                    content=content,
                    file_path=path,
                    project_id=project_id
                )
                results[path] = chunk_count
            else:
                results[path] = 0
            
            if progress_callback:
                progress_callback(i + 1, total, path)
        
        return results
    
    async def retrieve(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        include_file_info: bool = True
    ) -> RAGContext:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User's question or prompt
            project_id: Scope to specific project
            top_k: Number of chunks to retrieve
            max_tokens: Max tokens in context
            include_file_info: Add file path headers
        
        Returns:
            RAGContext with retrieved chunks and formatted prompt
        """
        top_k = top_k or self.top_k_default
        max_tokens = max_tokens or self.max_context_tokens
        
        # Search for relevant chunks
        results = await self.vector_store.search(
            query=query,
            project_id=project_id,
            top_k=top_k,
            threshold=self.similarity_threshold
        )
        
        # Build context prompt with token limit
        context_parts = []
        total_tokens = 0
        included_chunks = []
        
        # Group by file for better organization
        by_file: Dict[str, List[SearchResult]] = {}
        for result in results:
            if result.file_path not in by_file:
                by_file[result.file_path] = []
            by_file[result.file_path].append(result)
        
        # Sort each file's chunks by index
        for file_path in by_file:
            by_file[file_path].sort(key=lambda x: x.chunk_index)
        
        # Build context
        for file_path, chunks in by_file.items():
            file_header = f"\n### {file_path}\n" if include_file_info else ""
            file_tokens = len(file_header) // 4
            
            if total_tokens + file_tokens > max_tokens:
                break
            
            context_parts.append(file_header)
            total_tokens += file_tokens
            
            for chunk in chunks:
                chunk_tokens = len(chunk.content) // 4
                
                if total_tokens + chunk_tokens > max_tokens:
                    break
                
                context_parts.append(chunk.content)
                context_parts.append("\n")
                total_tokens += chunk_tokens
                included_chunks.append(chunk)
        
        # Format final context
        context_prompt = self._format_context("".join(context_parts))
        
        return RAGContext(
            query=query,
            chunks=included_chunks,
            total_tokens=total_tokens,
            context_prompt=context_prompt,
            metadata={
                'project_id': project_id,
                'files_included': list(by_file.keys()),
                'total_chunks_retrieved': len(results),
                'chunks_included': len(included_chunks)
            }
        )
    
    def _format_context(self, raw_context: str) -> str:
        """Format retrieved context for LLM injection"""
        if not raw_context.strip():
            return ""
        
        return f"""--- RETRIEVED CONTEXT ---
The following information was retrieved from the knowledge base and may be relevant to the user's query:

{raw_context.strip()}

--- END CONTEXT ---

Use the above context to inform your response, but also rely on your general knowledge when appropriate."""
    
    async def retrieve_with_reranking(
        self,
        query: str,
        project_id: Optional[str] = None,
        initial_k: int = 20,
        final_k: int = 5
    ) -> RAGContext:
        """
        Retrieve with re-ranking for better results.
        
        Two-stage retrieval:
        1. Get initial_k candidates from vector search
        2. Re-rank using LLM scoring
        3. Return final_k best results
        """
        # Initial retrieval
        results = await self.vector_store.search(
            query=query,
            project_id=project_id,
            top_k=initial_k,
            threshold=self.similarity_threshold
        )
        
        if len(results) <= final_k:
            # Not enough results to rerank
            return await self.retrieve(query, project_id, top_k=final_k)
        
        # TODO: Implement LLM-based re-ranking
        # For now, just return top results by similarity
        results = results[:final_k]
        
        # Build context from reranked results
        context_parts = []
        for result in results:
            context_parts.append(f"### {result.file_path}\n{result.content}\n")
        
        context_prompt = self._format_context("\n".join(context_parts))
        
        return RAGContext(
            query=query,
            chunks=results,
            total_tokens=sum(len(r.content) // 4 for r in results),
            context_prompt=context_prompt,
            metadata={
                'project_id': project_id,
                'reranked': True,
                'initial_candidates': initial_k,
                'final_results': len(results)
            }
        )
    
    async def hybrid_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
        vector_weight: float = 0.7
    ) -> RAGContext:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Args:
            query: Search query
            project_id: Project scope
            top_k: Number of results
            vector_weight: Weight for vector results (0-1)
        
        Note: Full implementation requires keyword index in Supabase.
        Currently falls back to vector-only search.
        """
        # TODO: Implement keyword search via Supabase full-text search
        # For now, use vector search only
        return await self.retrieve(query, project_id, top_k=top_k)
    
    async def delete_file(self, file_path: str, project_id: Optional[str] = None):
        """Remove a file from the RAG index"""
        await self.vector_store.delete_document(file_path, project_id)
    
    async def delete_project(self, project_id: str):
        """Remove all files for a project from the RAG index"""
        await self.vector_store.delete_project_chunks(project_id)
    
    async def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get RAG statistics"""
        return await self.vector_store.get_stats(project_id)


# Singleton instance
_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(supabase_client: Optional[Client] = None) -> RAGPipeline:
    """Get or create the singleton RAGPipeline instance"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline(supabase_client)
    return _rag_pipeline


# Convenience function
async def rag_query(
    query: str,
    project_id: Optional[str] = None,
    supabase_client: Optional[Client] = None
) -> str:
    """
    Quick RAG query - returns just the context prompt.
    
    Usage:
        context = await rag_query("How do I authenticate?", project_id="abc123")
    """
    rag = get_rag_pipeline(supabase_client)
    result = await rag.retrieve(query, project_id)
    return result.context_prompt
