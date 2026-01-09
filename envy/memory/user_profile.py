"""
ENVY User Profile
=================
Project-aware memory with user preferences and cross-conversation learning.

Features:
- User preferences (response style, verbosity, technical level)
- Known facts about the user
- Writing style adaptation
- Active project tracking
- Cross-session learning
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

try:
    from supabase import Client
except ImportError:
    Client = None


class Tone(Enum):
    """Response tone preferences"""
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    CONCISE = "concise"


@dataclass
class StyleProfile:
    """Writing style characteristics"""
    tone: Tone = Tone.PROFESSIONAL
    verbosity: float = 0.5  # 0.0 (terse) to 1.0 (detailed)
    technical_level: float = 0.5  # 0.0 (beginner) to 1.0 (expert)
    examples_preferred: bool = True
    code_comments: bool = True  # Prefer code with comments
    markdown_heavy: bool = True  # Use markdown formatting
    emoji_usage: float = 0.2  # 0.0 (none) to 1.0 (frequent)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tone': self.tone.value,
            'verbosity': self.verbosity,
            'technical_level': self.technical_level,
            'examples_preferred': self.examples_preferred,
            'code_comments': self.code_comments,
            'markdown_heavy': self.markdown_heavy,
            'emoji_usage': self.emoji_usage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StyleProfile':
        if not data:
            return cls()
        return cls(
            tone=Tone(data.get('tone', 'professional')),
            verbosity=data.get('verbosity', 0.5),
            technical_level=data.get('technical_level', 0.5),
            examples_preferred=data.get('examples_preferred', True),
            code_comments=data.get('code_comments', True),
            markdown_heavy=data.get('markdown_heavy', True),
            emoji_usage=data.get('emoji_usage', 0.2)
        )
    
    def get_prompt_instructions(self) -> str:
        """Generate style instructions for system prompt"""
        instructions = []
        
        # Tone
        tone_map = {
            Tone.CASUAL: "Use a casual, conversational tone.",
            Tone.PROFESSIONAL: "Maintain a professional, clear tone.",
            Tone.TECHNICAL: "Be precise and technical in your explanations.",
            Tone.FRIENDLY: "Be warm and encouraging in your responses.",
            Tone.CONCISE: "Keep responses brief and to the point."
        }
        instructions.append(tone_map.get(self.tone, ""))
        
        # Verbosity
        if self.verbosity < 0.3:
            instructions.append("Be extremely concise - short, direct answers.")
        elif self.verbosity > 0.7:
            instructions.append("Provide detailed, thorough explanations.")
        
        # Technical level
        if self.technical_level < 0.3:
            instructions.append("Explain concepts simply, avoid jargon.")
        elif self.technical_level > 0.7:
            instructions.append("You can use advanced terminology freely.")
        
        # Examples
        if self.examples_preferred:
            instructions.append("Include examples when helpful.")
        
        # Code style
        if self.code_comments:
            instructions.append("Add comments to code examples.")
        
        return " ".join(instructions)


@dataclass
class UserPreferences:
    """User-specific preferences"""
    preferred_persona: Optional[str] = None  # Default ENVY persona
    default_project_id: Optional[str] = None  # Auto-load project
    auto_save_conversations: bool = True
    show_thinking: bool = False  # Show chain-of-thought
    dark_mode: bool = True
    language: str = "en"
    timezone: str = "UTC"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass 
class Learning:
    """A learned fact about the user"""
    id: str
    content: str  # The learned information
    category: str  # "preference", "fact", "skill", "interest", "context"
    confidence: float  # 0.0 to 1.0
    source: str  # How it was learned ("explicit", "inferred", "conversation")
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'category': self.category,
            'confidence': self.confidence,
            'source': self.source,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class UserProfile:
    """
    Complete user profile with preferences, style, and learnings.
    """
    user_id: str = "default"
    name: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    writing_style: StyleProfile = field(default_factory=StyleProfile)
    known_facts: List[str] = field(default_factory=list)  # Quick facts
    learnings: List[Learning] = field(default_factory=list)  # Detailed learnings
    active_project_id: Optional[str] = None
    interaction_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'preferences': self.preferences.to_dict(),
            'writing_style': self.writing_style.to_dict(),
            'known_facts': self.known_facts,
            'learnings': [l.to_dict() for l in self.learnings],
            'active_project_id': self.active_project_id,
            'interaction_count': self.interaction_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        if not data:
            return cls()
        
        learnings = []
        for l in data.get('learnings', []):
            learnings.append(Learning(
                id=l['id'],
                content=l['content'],
                category=l['category'],
                confidence=l['confidence'],
                source=l['source'],
                created_at=datetime.fromisoformat(l['created_at']) if 'created_at' in l else datetime.now()
            ))
        
        return cls(
            user_id=data.get('user_id', 'default'),
            name=data.get('name'),
            preferences=UserPreferences.from_dict(data.get('preferences', {})),
            writing_style=StyleProfile.from_dict(data.get('writing_style', {})),
            known_facts=data.get('known_facts', []),
            learnings=learnings,
            active_project_id=data.get('active_project_id'),
            interaction_count=data.get('interaction_count', 0),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        )
    
    def add_fact(self, fact: str):
        """Add a known fact about the user"""
        if fact not in self.known_facts:
            self.known_facts.append(fact)
            self.updated_at = datetime.now()
    
    def add_learning(self, learning: Learning):
        """Add a detailed learning"""
        self.learnings.append(learning)
        self.updated_at = datetime.now()
    
    def get_context_prompt(self) -> str:
        """Generate context about the user for system prompt"""
        parts = []
        
        if self.name:
            parts.append(f"User's name: {self.name}")
        
        if self.known_facts:
            facts_str = "\n".join(f"- {f}" for f in self.known_facts[:10])
            parts.append(f"Known about user:\n{facts_str}")
        
        # Add high-confidence learnings
        high_conf = [l for l in self.learnings if l.confidence > 0.7]
        if high_conf:
            learnings_str = "\n".join(f"- {l.content}" for l in high_conf[:5])
            parts.append(f"Learned context:\n{learnings_str}")
        
        # Add style instructions
        style_instructions = self.writing_style.get_prompt_instructions()
        if style_instructions:
            parts.append(f"Response style: {style_instructions}")
        
        return "\n\n".join(parts) if parts else ""


class UserProfileManager:
    """
    Manages user profiles with Supabase or local storage.
    
    Usage:
        manager = UserProfileManager(supabase_client)
        profile = await manager.load("user123")
        profile.add_fact("User is a Python developer")
        await manager.save(profile)
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        self.client = supabase_client
        self.table = "user_profiles"
        self.learnings_table = "user_learnings"
        
        # Local storage fallback
        self.local_dir = Path("./user_data")
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self._cache: Dict[str, UserProfile] = {}
    
    async def load(self, user_id: str = "default") -> UserProfile:
        """Load a user profile"""
        # Check cache
        if user_id in self._cache:
            return self._cache[user_id]
        
        profile = None
        
        if self.client:
            profile = await self._load_supabase(user_id)
        else:
            profile = self._load_local(user_id)
        
        if not profile:
            profile = UserProfile(user_id=user_id)
        
        self._cache[user_id] = profile
        return profile
    
    async def save(self, profile: UserProfile):
        """Save a user profile"""
        profile.updated_at = datetime.now()
        self._cache[profile.user_id] = profile
        
        if self.client:
            await self._save_supabase(profile)
        else:
            self._save_local(profile)
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user profile"""
        if user_id in self._cache:
            del self._cache[user_id]
        
        if self.client:
            self.client.table(self.table).delete().eq('user_id', user_id).execute()
            return True
        else:
            path = self.local_dir / f"{user_id}.json"
            if path.exists():
                path.unlink()
                return True
        return False
    
    async def add_learning(
        self,
        user_id: str,
        content: str,
        category: str = "general",
        confidence: float = 0.8,
        source: str = "inferred"
    ):
        """Add a learning to a user's profile"""
        profile = await self.load(user_id)
        
        import uuid
        learning = Learning(
            id=str(uuid.uuid4())[:8],
            content=content,
            category=category,
            confidence=confidence,
            source=source
        )
        
        profile.add_learning(learning)
        await self.save(profile)
    
    async def update_style(
        self,
        user_id: str,
        **style_updates
    ):
        """Update user's style preferences"""
        profile = await self.load(user_id)
        
        for key, value in style_updates.items():
            if hasattr(profile.writing_style, key):
                if key == 'tone':
                    value = Tone(value) if isinstance(value, str) else value
                setattr(profile.writing_style, key, value)
        
        await self.save(profile)
    
    async def increment_interaction(self, user_id: str):
        """Increment interaction count"""
        profile = await self.load(user_id)
        profile.interaction_count += 1
        await self.save(profile)
    
    async def _load_supabase(self, user_id: str) -> Optional[UserProfile]:
        """Load from Supabase"""
        try:
            response = self.client.table(self.table).select("*").eq('user_id', user_id).execute()
            
            if not response.data:
                return None
            
            row = response.data[0]
            
            # Load learnings
            learnings_response = self.client.table(self.learnings_table).select("*").eq('user_id', user_id).execute()
            learnings = []
            for l in learnings_response.data or []:
                learnings.append(Learning(
                    id=l['id'],
                    content=l['learning'],
                    category=l.get('category', 'general'),
                    confidence=l.get('confidence', 0.8),
                    source='conversation',
                    created_at=datetime.fromisoformat(l['created_at'])
                ))
            
            return UserProfile(
                user_id=row['user_id'],
                name=row.get('name'),
                preferences=UserPreferences.from_dict(row.get('preferences', {})),
                writing_style=StyleProfile.from_dict(row.get('writing_style', {})),
                known_facts=row.get('known_facts', []),
                learnings=learnings,
                active_project_id=row.get('active_project_id'),
                interaction_count=row.get('interaction_count', 0),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        except Exception as e:
            print(f"[UserProfile] Supabase load error: {e}")
            return None
    
    async def _save_supabase(self, profile: UserProfile):
        """Save to Supabase"""
        try:
            data = {
                'user_id': profile.user_id,
                'name': profile.name,
                'preferences': profile.preferences.to_dict(),
                'writing_style': profile.writing_style.to_dict(),
                'known_facts': profile.known_facts,
                'active_project_id': profile.active_project_id,
                'interaction_count': profile.interaction_count,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat()
            }
            
            self.client.table(self.table).upsert(data).execute()
            
            # Save learnings
            for learning in profile.learnings:
                learning_data = {
                    'id': learning.id,
                    'user_id': profile.user_id,
                    'learning': learning.content,
                    'category': learning.category,
                    'confidence': learning.confidence,
                    'created_at': learning.created_at.isoformat()
                }
                self.client.table(self.learnings_table).upsert(learning_data).execute()
                
        except Exception as e:
            print(f"[UserProfile] Supabase save error: {e}")
    
    def _load_local(self, user_id: str) -> Optional[UserProfile]:
        """Load from local file"""
        path = self.local_dir / f"{user_id}.json"
        if not path.exists():
            return None
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return UserProfile.from_dict(data)
        except Exception as e:
            print(f"[UserProfile] Local load error: {e}")
            return None
    
    def _save_local(self, profile: UserProfile):
        """Save to local file"""
        path = self.local_dir / f"{profile.user_id}.json"
        try:
            with open(path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[UserProfile] Local save error: {e}")


# Singleton instance
_profile_manager: Optional[UserProfileManager] = None


def get_profile_manager(supabase_client: Optional[Client] = None) -> UserProfileManager:
    """Get or create the singleton UserProfileManager instance"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = UserProfileManager(supabase_client)
    return _profile_manager
