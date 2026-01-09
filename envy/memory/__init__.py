"""
ENVY Memory System
==================
Three-tier memory architecture based on Letta/MemGPT.

Tier 1: Working Memory (in-context)
Tier 2: Short-Term Memory (Supabase + vector search)
Tier 3: Long-Term Memory (Supabase archival)

Plus RAG (Retrieval Augmented Generation) for project context.
"""

from .supabase_memory import SupabaseMemory, LocalMemory
from .memory_manager import MemoryManager
from .vector_store import (
    VectorStore,
    DocumentChunk,
    SearchResult,
    Chunker,
    Embedder,
    EmbeddingModel,
    get_vector_store
)
from .rag_pipeline import RAGPipeline, RAGContext, get_rag_pipeline, rag_query
from .user_profile import (
    UserProfile,
    UserProfileManager,
    UserPreferences,
    StyleProfile,
    Learning,
    Tone,
    get_profile_manager
)

__all__ = [
    # Memory Manager
    "SupabaseMemory",
    "LocalMemory",
    "MemoryManager",
    # Vector Store
    "VectorStore",
    "DocumentChunk",
    "SearchResult",
    "Chunker",
    "Embedder",
    "EmbeddingModel",
    "get_vector_store",
    # RAG Pipeline
    "RAGPipeline",
    "RAGContext",
    "get_rag_pipeline",
    "rag_query",
    # User Profile
    "UserProfile",
    "UserProfileManager",
    "UserPreferences",
    "StyleProfile",
    "Learning",
    "Tone",
    "get_profile_manager"
]
