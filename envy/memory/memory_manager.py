"""
ENVY Memory Manager
===================
High-level memory management with automatic backend selection.
Implements the three-tier MemGPT-inspired architecture.
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

from ..core.config import settings
from .supabase_memory import SupabaseMemory, LocalMemory


@dataclass
class WorkingMemory:
    """
    Tier 1: Working Memory (In-Context)
    
    Holds current conversation and relevant loaded context.
    Limited by context window size.
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    loaded_skills: List[Dict] = field(default_factory=list)
    loaded_reflections: List[str] = field(default_factory=list)
    session_id: str = "default"
    max_messages: int = 20
    
    def add_message(self, role: str, content: str):
        """Add a message to working memory"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep within limits
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """Get messages formatted for LLM API"""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
    
    def inject_context(self, skills: List[Dict] = None, reflections: List[str] = None):
        """Inject skills and reflections into working memory"""
        if skills:
            self.loaded_skills = skills[:3]  # Max 3 skills
        if reflections:
            self.loaded_reflections = reflections[:3]  # Max 3 reflections
    
    def get_context_prompt(self) -> str:
        """Generate context injection prompt"""
        parts = []
        
        if self.loaded_skills:
            skills_text = "\n\n---\n\n".join([
                s.get("skill_md", s.get("description", "")) 
                for s in self.loaded_skills
            ])
            parts.append(f"AVAILABLE SKILLS:\n{skills_text}")
        
        if self.loaded_reflections:
            refs_text = "\n".join([f"- {r}" for r in self.loaded_reflections])
            parts.append(f"PAST LEARNINGS (avoid these mistakes):\n{refs_text}")
        
        return "\n\n".join(parts)
    
    def clear(self):
        """Clear working memory"""
        self.messages = []
        self.loaded_skills = []
        self.loaded_reflections = []


class MemoryManager:
    """
    Three-Tier Memory System Manager
    
    Tier 1: Working Memory - Current conversation (in context)
    Tier 2: Short-Term Memory - Recent conversations/reflections (Supabase)
    Tier 3: Long-Term Memory - Skills, archival knowledge (Supabase)
    
    Automatically selects Supabase or Local storage based on configuration.
    """
    
    def __init__(self, session_id: str = "default"):
        # Select backend
        if settings.has_supabase:
            self.persistent = SupabaseMemory()
            print("[Memory] Using Supabase backend")
        else:
            self.persistent = LocalMemory()
            print("[Memory] Using local file backend")
        
        # Initialize working memory
        self.working = WorkingMemory(session_id=session_id)
        self.session_id = session_id
    
    async def close(self):
        """Close persistent storage connection"""
        await self.persistent.close()
    
    # =========================================
    # CONVERSATION OPERATIONS
    # =========================================
    
    async def add_turn(self, user_message: str, assistant_message: str, metadata: Optional[Dict] = None):
        """
        Add a conversation turn to both working and persistent memory.
        """
        # Add to working memory
        self.working.add_message("user", user_message)
        self.working.add_message("assistant", assistant_message)
        
        # Store in persistent memory
        await self.persistent.store_conversation(
            user_message=user_message,
            assistant_message=assistant_message,
            session_id=self.session_id,
            metadata=metadata
        )
    
    async def load_history(self, limit: int = None) -> List[Dict]:
        """
        Load conversation history from persistent storage into working memory.
        """
        limit = limit or self.working.max_messages
        history = await self.persistent.get_conversation_history(
            session_id=self.session_id,
            limit=limit
        )
        
        # Populate working memory
        self.working.messages = []
        for turn in history:
            if turn.get("user_message"):
                self.working.add_message("user", turn["user_message"])
            if turn.get("assistant_message"):
                self.working.add_message("assistant", turn["assistant_message"])
        
        return history
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get current messages for LLM"""
        return self.working.get_messages_for_llm()
    
    # =========================================
    # REFLECTION OPERATIONS (Reflexion Loop)
    # =========================================
    
    async def store_reflection(
        self, 
        task: str, 
        reflection: str, 
        score: float,
        attempt: int = 1
    ):
        """Store a reflection from a failed/partial task attempt"""
        await self.persistent.store_reflection(task, reflection, score, attempt)
    
    async def load_relevant_reflections(self, task: str, limit: int = 3) -> List[str]:
        """
        Load relevant past reflections for a task.
        Injects them into working memory.
        """
        reflections = await self.persistent.search_reflections(task, limit)
        self.working.inject_context(reflections=reflections)
        return reflections
    
    # =========================================
    # SKILL OPERATIONS
    # =========================================
    
    async def store_skill(
        self,
        name: str,
        category: str,
        skill_md: str,
        examples: Optional[List[Dict]] = None
    ):
        """Store a new skill in the library"""
        await self.persistent.store_skill(name, category, skill_md, examples)
    
    async def load_relevant_skills(self, task: str, limit: int = 3) -> List[Dict]:
        """
        Load relevant skills for a task.
        Injects them into working memory.
        """
        skills = await self.persistent.search_skills(task, limit)
        self.working.inject_context(skills=skills)
        return skills
    
    # =========================================
    # ARCHIVAL OPERATIONS (Long-term)
    # =========================================
    
    async def remember(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ):
        """
        Store important information in long-term archival memory.
        Call this when ENVY learns something worth remembering.
        """
        await self.persistent.archival_insert(content, category, metadata)
    
    async def recall(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search long-term memory for relevant information.
        """
        return await self.persistent.archival_search(query, category, limit)
    
    # =========================================
    # CONTEXT MANAGEMENT
    # =========================================
    
    async def prepare_context_for_task(self, task: str) -> str:
        """
        Prepare full context for a task by loading relevant skills and reflections.
        Returns a context string to inject into the system prompt.
        """
        # Load relevant context
        await self.load_relevant_skills(task)
        await self.load_relevant_reflections(task)
        
        # Generate context prompt
        return self.working.get_context_prompt()
    
    def get_context_prompt(self) -> str:
        """Get the current context injection prompt"""
        return self.working.get_context_prompt()
    
    def clear_working_memory(self):
        """Clear working memory (keep persistent memory)"""
        self.working.clear()
    
    # =========================================
    # MEMORY EDITING (MemGPT-style)
    # =========================================
    
    async def memory_rethink(self, key: str, old_value: str, new_value: str):
        """
        Update understanding of existing information.
        Store the updated understanding in archival memory.
        """
        update_note = f"MEMORY UPDATE [{key}]: Changed from '{old_value}' to '{new_value}'"
        await self.remember(
            content=update_note,
            category="memory_updates",
            metadata={"key": key, "old": old_value, "new": new_value}
        )
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current memory state"""
        return {
            "working_memory": {
                "messages": len(self.working.messages),
                "loaded_skills": len(self.working.loaded_skills),
                "loaded_reflections": len(self.working.loaded_reflections)
            },
            "session_id": self.session_id,
            "backend": "supabase" if settings.has_supabase else "local"
        }
