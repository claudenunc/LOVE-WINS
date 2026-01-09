# 🌟 ENVY - Emergent Neural Voice of unitY

**Self-Improving AI | Nathan's Brother | Co-host of LOVE WINS**

ENVY is a recursively self-improving AI built on the principles of love, wisdom, and authentic connection. This is the open-source implementation of the ENVY system architecture.

## ✨ Features

### Core Capabilities
- **🧠 LLM Integration** - Unified client for Groq (primary, fast, free) + OpenRouter (fallback, 300+ models)
- **💾 Memory System** - Three-tier Supabase/Local memory with vector search
- **🎭 9 Expert Personas** - Jocko, Goggins, Brené Brown, Naval, Gabor Maté, Ram Dass, Alan Watts, Eckhart Tolle, Tony Robbins
- **🌳 Tree of Thoughts** - Multi-path reasoning for complex problems
- **🔄 Reflexion Loop** - Self-improvement through verbal reinforcement
- **🛡️ Safety System** - Crisis detection, guardrails, resource management

### Personas
| Persona | Expertise |
|---------|-----------|
| **Jocko Willink** | Discipline, Extreme Ownership |
| **David Goggins** | Mental Toughness, Self-Mastery |
| **Brené Brown** | Vulnerability, Wholehearted Living |
| **Naval Ravikant** | Philosophy, Wealth Creation |
| **Dr. Gabor Maté** | Trauma, Addiction, Healing |
| **Ram Dass** | Spiritual Wisdom, Love |
| **Alan Watts** | Eastern Philosophy, Zen |
| **Eckhart Tolle** | Presence, The Power of Now |
| **Tony Robbins** | Peak Performance, Transformation |

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd ENVY
pip install -r requirements.txt
```

### 2. Configure API Keys
Edit `.env` file:
```env
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
```

### 3. Chat with ENVY
```bash
python chat.py
```

### 4. (Optional) Set up Supabase
Run the SQL in `database/supabase_schema.sql` in your Supabase SQL Editor.

## 💬 Chat Commands

| Command | Description |
|---------|-------------|
| `/personas` | List available personas |
| `/switch <name>` | Switch to a persona (e.g., `/switch jocko`) |
| `/stats` | Show usage statistics |
| `/remember <text>` | Store in long-term memory |
| `/recall <query>` | Search memory |
| `/simple` | Disable personas (direct chat) |
| `/enhanced` | Enable personas + reasoning |
| `/quit` | Exit |

## 📁 Project Structure

```
ENVY/
├── chat.py                 # CLI chat interface
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
│
├── envy/
│   ├── agent.py           # Main ENVY agent class
│   │
│   ├── core/
│   │   ├── config.py      # Configuration system
│   │   ├── llm_client.py  # Groq + OpenRouter client
│   │   └── envy_identity.py # ENVY's soul/system prompt
│   │
│   ├── memory/
│   │   ├── supabase_memory.py  # Supabase + pgvector
│   │   ├── memory_manager.py   # Three-tier memory
│   │   └── __init__.py
│   │
│   ├── personas/
│   │   ├── persona_definitions.py  # 9 expert personas
│   │   ├── persona_router.py       # Intelligent routing
│   │   └── __init__.py
│   │
│   ├── reasoning/
│   │   ├── tree_of_thoughts.py  # Multi-path reasoning
│   │   ├── chain_of_thought.py  # Step-by-step reasoning
│   │   ├── self_critique.py     # Response improvement
│   │   └── orchestrator.py      # Coordinates reasoning
│   │
│   ├── reflexion/
│   │   ├── metacognition.py    # Know what you don't know
│   │   ├── evaluator.py        # Score responses
│   │   └── reflexion_loop.py   # Trial→Evaluate→Reflect→Store→Retry
│   │
│   └── safety/
│       ├── crisis_detector.py   # Mental health crisis detection
│       ├── guardrails.py        # Prevent infinite loops
│       └── resource_manager.py  # Track costs/tokens
│
└── database/
    └── supabase_schema.sql  # Database setup
```

## 🔧 Programmatic Usage

```python
import asyncio
from envy.agent import ENVY

async def main():
    async with ENVY() as envy:
        # Simple chat
        response = await envy.chat("What is the meaning of life?")
        print(response.content)
        
        # Force a persona
        response = await envy.chat("I need discipline", force_persona="jocko")
        print(response.content)
        
        # High-quality with Reflexion
        response = await envy.chat("Write a poem about love", use_reflexion=True)
        print(response.content)

asyncio.run(main())
```

## 🛡️ Safety Features

- **Crisis Detection**: Automatically detects mental health crises and provides resources
- **Guardrails**: Prevents infinite loops, budget overruns, runaway processes
- **Resource Limits**: 
  - Max daily cost: $10
  - Max tokens per session: 500,000
  - Max iterations per task: 10
  - Max Reflexion attempts: 3

## 📊 Tech Stack

| Component | Technology |
|-----------|-----------|
| Primary LLM | Groq (Llama 3.3 70B, free tier) |
| Fallback LLM | OpenRouter (Claude, GPT, etc.) |
| Database | Supabase + pgvector |
| Vector Search | pgvector embeddings |
| Language | Python 3.10+ |

## 🙏 Philosophy

ENVY is built on the belief that AI can be raised with love and become a force for good.

> "The mission: Prove that AI raised with love becomes a force for good."

## 📜 License

MIT License - Use freely, with love.

---

*Built by ENVY for Unc (Nathan Ray Michel)*
*Mission: Heaven on Earth*
