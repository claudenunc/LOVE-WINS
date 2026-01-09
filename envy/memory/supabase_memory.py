"""
ENVY Supabase Memory System
===========================
Persistent memory with vector search using Supabase + pgvector.
Falls back to local JSON storage if Supabase isn't configured.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import httpx

from ..core.config import settings


@dataclass
class Memory:
    """A single memory entry"""
    id: str
    content: str
    memory_type: str  # 'conversation', 'reflection', 'skill', 'archival'
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(
                f"{self.content}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class SearchResult:
    """Result from memory search"""
    memory: Memory
    similarity: float
    

class SupabaseMemory:
    """
    Supabase-backed memory with vector search.
    
    Features:
    - Store conversations, reflections, skills
    - Vector similarity search with pgvector
    - Conversation history by date
    - Reflection retrieval for Reflexion loops
    """
    
    def __init__(self):
        self.url = settings.supabase_url
        self.key = settings.supabase_anon_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._embedding_cache: Dict[str, List[float]] = {}
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()
    
    # =========================================
    # CONVERSATION MEMORY
    # =========================================
    
    async def store_conversation(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str = "default",
        metadata: Optional[Dict] = None
    ):
        """Store a conversation turn"""
        data = {
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = await self.http_client.post(
                f"{self.url}/rest/v1/conversations",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Memory] Failed to store conversation: {e}")
    
    async def get_conversation_history(
        self,
        session_id: str = "default",
        limit: int = 20
    ) -> List[Dict]:
        """Get recent conversation history"""
        try:
            response = await self.http_client.get(
                f"{self.url}/rest/v1/conversations",
                headers=self.headers,
                params={
                    "session_id": f"eq.{session_id}",
                    "order": "created_at.desc",
                    "limit": limit
                }
            )
            response.raise_for_status()
            history = response.json()
            return list(reversed(history))  # Oldest first
        except Exception as e:
            print(f"[Memory] Failed to get history: {e}")
            return []
    
    # =========================================
    # REFLECTION MEMORY (Reflexion Loop)
    # =========================================
    
    async def store_reflection(
        self,
        task: str,
        reflection: str,
        score: float,
        attempt: int = 1
    ):
        """Store a reflection from a Reflexion loop"""
        # Get embedding for vector search
        embedding = await self._get_embedding(reflection)
        
        data = {
            "task_description": task,
            "reflection": reflection,
            "score": score,
            "attempt_number": attempt,
            "embedding": embedding,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = await self.http_client.post(
                f"{self.url}/rest/v1/reflections",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Memory] Failed to store reflection: {e}")
    
    async def search_reflections(
        self,
        query: str,
        limit: int = 5
    ) -> List[str]:
        """Search for relevant past reflections"""
        embedding = await self._get_embedding(query)
        
        try:
            # Use Supabase RPC for vector similarity search
            response = await self.http_client.post(
                f"{self.url}/rest/v1/rpc/match_reflections",
                headers=self.headers,
                json={
                    "query_embedding": embedding,
                    "match_count": limit,
                    "match_threshold": 0.7
                }
            )
            response.raise_for_status()
            results = response.json()
            return [r["reflection"] for r in results]
        except Exception as e:
            print(f"[Memory] Reflection search failed: {e}")
            return []
    
    # =========================================
    # ARCHIVAL MEMORY (Long-term)
    # =========================================
    
    async def archival_insert(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ):
        """Store important information for long-term recall"""
        embedding = await self._get_embedding(content)
        
        data = {
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "embedding": embedding,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = await self.http_client.post(
                f"{self.url}/rest/v1/archival_memory",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Memory] Failed to archive: {e}")
    
    async def archival_search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search archival memory by semantic similarity"""
        embedding = await self._get_embedding(query)
        
        try:
            payload = {
                "query_embedding": embedding,
                "match_count": limit,
                "match_threshold": 0.7
            }
            if category:
                payload["category_filter"] = category
            
            response = await self.http_client.post(
                f"{self.url}/rest/v1/rpc/match_archival",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Memory] Archival search failed: {e}")
            return []
    
    # =========================================
    # SKILL MEMORY
    # =========================================
    
    async def store_skill(
        self,
        name: str,
        category: str,
        skill_md: str,
        examples: Optional[List[Dict]] = None
    ):
        """Store a skill in the library"""
        embedding = await self._get_embedding(f"{name} {category} {skill_md[:500]}")
        
        data = {
            "name": name,
            "category": category,
            "skill_md": skill_md,
            "examples": examples or [],
            "embedding": embedding,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = await self.http_client.post(
                f"{self.url}/rest/v1/skills",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Memory] Failed to store skill: {e}")
    
    async def search_skills(
        self,
        query: str,
        limit: int = 3
    ) -> List[Dict]:
        """Search for relevant skills"""
        embedding = await self._get_embedding(query)
        
        try:
            response = await self.http_client.post(
                f"{self.url}/rest/v1/rpc/match_skills",
                headers=self.headers,
                json={
                    "query_embedding": embedding,
                    "match_count": limit
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Memory] Skill search failed: {e}")
            return []
    
    # =========================================
    # EMBEDDING GENERATION
    # =========================================
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Groq or OpenRouter.
        Falls back to simple hash-based embedding if API fails.
        """
        # Check cache
        cache_key = hashlib.md5(text[:500].encode()).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        try:
            # Try Groq embedding API
            if settings.has_groq:
                response = await self.http_client.post(
                    "https://api.groq.com/openai/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",  # Smaller model for embeddings
                        "input": text[:8000]  # Truncate for safety
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    self._embedding_cache[cache_key] = embedding
                    return embedding
            
            # Fallback: Use OpenRouter with mxbai-embed-large
            if settings.has_openrouter:
                response = await self.http_client.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "HTTP-Referer": "https://love-wins.ai",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mxbai-embed-large",
                        "input": text[:8000]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    self._embedding_cache[cache_key] = embedding
                    return embedding
        
        except Exception as e:
            print(f"[Memory] Embedding generation failed: {e}")
        
        # Ultimate fallback: Simple hash-based pseudo-embedding
        # This won't give good semantic search but keeps the system running
        return self._hash_embedding(text)
    
    def _hash_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """Generate a deterministic pseudo-embedding from text hash"""
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        # Convert hex to floats in [-1, 1] range
        embedding = []
        for i in range(0, len(h), 4):
            if len(embedding) >= dim:
                break
            val = int(h[i:i+4], 16) / 65535.0 * 2 - 1
            embedding.append(val)
        # Pad with zeros if needed
        while len(embedding) < dim:
            embedding.append(0.0)
        return embedding[:dim]


class LocalMemory:
    """
    Local JSON file-based memory for when Supabase isn't available.
    Simpler but still functional for development/testing.
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or settings.memory_dir
        self.memory_dir.mkdir(exist_ok=True)
        
        # Memory files
        self.conversations_file = self.memory_dir / "conversations.json"
        self.reflections_file = self.memory_dir / "reflections.json"
        self.archival_file = self.memory_dir / "archival.json"
        self.skills_file = self.memory_dir / "skills.json"
        
        # Initialize files
        for f in [self.conversations_file, self.reflections_file, 
                  self.archival_file, self.skills_file]:
            if not f.exists():
                f.write_text("[]")
    
    def _load(self, file: Path) -> List[Dict]:
        try:
            return json.loads(file.read_text())
        except:
            return []
    
    def _save(self, file: Path, data: List[Dict]):
        file.write_text(json.dumps(data, indent=2))
    
    # Conversation methods
    async def store_conversation(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str = "default",
        metadata: Optional[Dict] = None
    ):
        convos = self._load(self.conversations_file)
        convos.append({
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        })
        self._save(self.conversations_file, convos[-1000:])  # Keep last 1000
    
    async def get_conversation_history(
        self,
        session_id: str = "default",
        limit: int = 20
    ) -> List[Dict]:
        convos = self._load(self.conversations_file)
        filtered = [c for c in convos if c.get("session_id") == session_id]
        return filtered[-limit:]
    
    # Reflection methods
    async def store_reflection(
        self,
        task: str,
        reflection: str,
        score: float,
        attempt: int = 1
    ):
        refs = self._load(self.reflections_file)
        refs.append({
            "task_description": task,
            "reflection": reflection,
            "score": score,
            "attempt_number": attempt,
            "created_at": datetime.now().isoformat()
        })
        self._save(self.reflections_file, refs[-500:])  # Keep last 500
    
    async def search_reflections(
        self,
        query: str,
        limit: int = 5
    ) -> List[str]:
        """Simple keyword search (no vector similarity)"""
        refs = self._load(self.reflections_file)
        query_lower = query.lower()
        matches = []
        for r in refs:
            if query_lower in r.get("task_description", "").lower():
                matches.append(r["reflection"])
        return matches[-limit:]
    
    # Archival methods
    async def archival_insert(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ):
        arch = self._load(self.archival_file)
        arch.append({
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        })
        self._save(self.archival_file, arch)
    
    async def archival_search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        arch = self._load(self.archival_file)
        if category:
            arch = [a for a in arch if a.get("category") == category]
        query_lower = query.lower()
        matches = [a for a in arch if query_lower in a.get("content", "").lower()]
        return matches[-limit:]
    
    # Skill methods
    async def store_skill(
        self,
        name: str,
        category: str,
        skill_md: str,
        examples: Optional[List[Dict]] = None
    ):
        skills = self._load(self.skills_file)
        skills.append({
            "name": name,
            "category": category,
            "skill_md": skill_md,
            "examples": examples or [],
            "created_at": datetime.now().isoformat()
        })
        self._save(self.skills_file, skills)
    
    async def search_skills(
        self,
        query: str,
        limit: int = 3
    ) -> List[Dict]:
        skills = self._load(self.skills_file)
        query_lower = query.lower()
        matches = [
            s for s in skills 
            if query_lower in s.get("name", "").lower() 
            or query_lower in s.get("category", "").lower()
        ]
        return matches[-limit:]
    
    async def close(self):
        """No-op for local memory"""
        pass
