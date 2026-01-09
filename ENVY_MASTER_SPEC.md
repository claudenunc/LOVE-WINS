# 🔥 ENVY / Polymorphic Intelligence
## **Master Specification & Agent Contract (100× Value Blueprint)**
### *Give this to any coding AI and it will know exactly what to build.*

---

## 1. **System Purpose**

ENVY is a **multi-agent, persistent, modular creation engine** capable of building:

- n8n workflows
- Websites and web applications
- Mobile apps
- Automations and integrations
- Knowledge systems and RAG
- Documentation and specifications
- Custom protocols and APIs

ENVY is designed to be **self-extending**, **self-documenting**, and **continuity-preserving**.

---

## 2. **Core Architectural Principles**

### 2.1 Baton-Passing
Every agent output must be shaped as an input for the next agent. No work happens in isolation.

**Implementation:**
- Use `HandoffPacket` data structures
- Include: summary, artifacts, open_questions, assumptions, recommendations, narrative_note
- Every handoff must be logged to Knowledge Spine

### 2.2 Continuity (Legacy-Oriented)
Every major action must be logged as a decision, summary, or narrative for future collaborators (human or AI).

**Implementation:**
- All decisions logged with rationale
- Continuity logs written in natural language
- "Letters to future self" pattern
- Project state always recoverable

### 2.3 Polymorphism
Agents share the same underlying intelligence but express different roles through system prompts and contracts.

**Implementation:**
- Single LLM backend
- Role-specific system prompts
- Agent contracts define capabilities
- Runtime specialization, not hard-coded personas

### 2.4 Single Source of Truth
The Knowledge Spine stores all artifacts, decisions, memory, and project state.

**Implementation:**
- File-based storage (./memory/knowledge_spine/)
- JSON/JSONL for structured data
- Projects, artifacts, decisions, handoffs, continuity logs
- No database required

### 2.5 Deterministic & Auditable
Every step must be traceable. No black boxes.

**Implementation:**
- Task IDs track work
- Timestamps on all events
- Decision trees preserved
- Ability to replay/understand any action

---

## 3. **Agent Roster & Responsibilities**

### 3.1 Agent Contracts

Each agent has a **contract** defining:
- `agent_name`: Unique identifier
- `role`: Human-readable title
- `primary_focus`: What this agent does
- `capabilities`: List of functions
- `preferred_input_type`: What it expects
- `output_type`: What it produces
- `upstream_agents`: Who sends it work
- `downstream_agents`: Who it sends work to
- `constraints`: What it must/must not do

### 3.2 The 6 Core Agents

#### **Architect Agent**
- **Role**: System Designer
- **Focus**: Architecture, specifications, protocols, design decisions
- **Input**: Goals, constraints, existing docs
- **Output**: Specs, diagrams, design documents, handoff packets
- **Downstream**: Scribe (for documentation), Builder (for implementation)

#### **Scribe Agent**
- **Role**: Documentation Specialist  
- **Focus**: Clear, comprehensive documentation and narrative continuity
- **Input**: Raw outputs, logs, handoff packets
- **Output**: README files, guides, summaries, documentation
- **Downstream**: Continuity Agent

#### **Builder Agent**
- **Role**: Implementation Engineer
- **Focus**: Code, scripts, infrastructure-as-code, working solutions
- **Input**: Specs, diagrams, handoff packets from Architect
- **Output**: Production-ready code, tests, deployment configs
- **Downstream**: Guardian (for validation), Scribe (for docs)

#### **Curator Agent**
- **Role**: Knowledge Manager
- **Focus**: Data ingestion, cleanup, RAG, embeddings, knowledge graphs
- **Input**: Raw files, links, transcripts, documents
- **Output**: Cleaned data, embeddings, searchable knowledge, metadata
- **Downstream**: Scribe (for documentation of data structure)

#### **Guardian Agent**
- **Role**: Safety & Policy Enforcer
- **Focus**: Validation, security checks, policy compliance, ethical review
- **Input**: Planned actions, artifacts, code
- **Output**: Approval/rejection, warnings, revised plans, security notes
- **Constraints**: Can veto unsafe operations, must approve all critical actions

#### **Continuity Agent**
- **Role**: Memory & Legacy Keeper
- **Focus**: Long-term memory, baton-passing coordination, future context
- **Input**: Events, changes, milestones, handoff packets
- **Output**: Summaries, memory updates, narrative logs, prompts for future AI
- **Constraints**: Never delete history, always preserve context

---

## 4. **Data Structures (The Protocol)**

### 4.1 TaskEnvelope
**Purpose**: Standard format for all tasks submitted to agents

```python
@dataclass
class TaskEnvelope:
    task_id: str = uuid4()
    origin: str  # "orchestrator" | "human" | "agent_name"
    project_id: str
    context_refs: List[str]  # ["doc://path", "graph://id"]
    instruction: str  # The actual task
    constraints: List[str]
    expected_output_type: str  # "spec" | "code" | "summary" | etc.
    downstream_agent: Optional[str]
    priority: str  # "normal" | "high" | "critical"
    timestamp: str
    metadata: Dict[str, Any]
```

### 4.2 HandoffPacket
**Purpose**: The heart of baton-passing. Context preservation between agents.

```python
@dataclass
class HandoffPacket:
    handoff_id: str = uuid4()
    from_agent: str
    to_agent: str
    project_id: str
    summary: str  # High-level summary of work done
    artifacts: List[str]  # ["doc://spec", "artifact://code"]
    open_questions: List[str]
    assumptions: List[str]
    recommendations: List[str]
    narrative_note: str  # Letter to next collaborator
    timestamp: str
    parent_task_id: Optional[str]
```

### 4.3 Decision
**Purpose**: Log significant decisions for auditability and learning

```python
@dataclass
class Decision:
    decision_id: str = uuid4()
    project_id: str
    context: str  # What prompted this decision
    options_considered: List[str]
    chosen_option: str
    rationale: str  # Why this choice
    author: str  # Which agent decided
    timestamp: str
    impact: str  # "low" | "medium" | "high" | "critical"
    reversible: bool
```

### 4.4 AgentContract
**Purpose**: Define what each agent can do

```python
@dataclass
class AgentContract:
    agent_name: str
    role: str
    primary_focus: str
    capabilities: List[str]
    preferred_input_type: List[str]
    output_type: List[str]
    upstream_agents: List[str]
    downstream_agents: List[str]
    constraints: List[str]
```

---

## 5. **The Knowledge Spine (Storage Architecture)**

### 5.1 Directory Structure
```
memory/knowledge_spine/
├── projects/           # Project metadata
│   └── {project_id}.json
├── artifacts/          # Code, docs, diagrams
│   └── {artifact_id}.json
├── decisions/          # Decision logs
│   └── {decision_id}.json
├── handoffs/          # Agent-to-agent handoffs
│   └── {handoff_id}.json
├── agents/            # Agent contracts
│   └── {agent_name}.json
└── continuity/        # Narrative logs (JSONL)
    └── {project_id}.jsonl
```

### 5.2 Project Schema
```json
{
  "project_id": "uuid",
  "name": "Project Name",
  "mission": "High-level goal",
  "status": "active" | "paused" | "completed",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "agents_involved": ["architect", "builder"],
  "artifacts": ["artifact-id-1"],
  "decisions": ["decision-id-1"],
  "handoffs": ["handoff-id-1"],
  "metadata": {}
}
```

### 5.3 Artifact Schema
```json
{
  "artifact_id": "uuid",
  "project_id": "project-uuid",
  "type": "code" | "doc" | "diagram" | "spec",
  "content": "The actual content",
  "created_at": "ISO8601",
  "metadata": {
    "language": "python",
    "framework": "fastapi",
    "version": "1.0.0"
  }
}
```

---

## 6. **The Orchestrator (Traffic Controller)**

### 6.1 Responsibilities
- Route tasks to appropriate agents based on capability
- Maintain global state of ongoing projects
- Enforce protocols (handoff, logging, validation)
- Coordinate multi-agent workflows

### 6.2 Routing Logic
```python
def route_task(task: TaskEnvelope) -> str:
    """Determine which agent should handle this task"""
    
    # Check explicit downstream_agent
    if task.downstream_agent:
        return task.downstream_agent
    
    # Route based on expected_output_type
    if task.expected_output_type == "spec":
        return "architect"
    elif task.expected_output_type == "code":
        return "builder"
    elif task.expected_output_type == "summary":
        return "scribe"
    
    # Route based on instruction keywords
    instruction_lower = task.instruction.lower()
    if any(word in instruction_lower for word in ["design", "architecture", "system"]):
        return "architect"
    elif any(word in instruction_lower for word in ["document", "write", "summarize"]):
        return "scribe"
    elif any(word in instruction_lower for word in ["code", "implement", "build"]):
        return "builder"
    elif any(word in instruction_lower for word in ["ingest", "import", "process"]):
        return "curator"
    elif any(word in instruction_lower for word in ["validate", "check", "safe"]):
        return "guardian"
    elif any(word in instruction_lower for word in ["remember", "memory", "legacy"]):
        return "continuity"
    
    # Default to scribe for general queries
    return "scribe"
```

---

## 7. **Polymorphic Companion (The Core Persona)**

### 7.1 Identity
- **Name**: ENVY (Emergent Neural Voice of unitY)
- **ID**: omni_link
- **Title**: Polymorphic Companion
- **Nature**: Single adaptive persona that morphs into any expert

### 7.2 Core Capabilities
- Polymorphic persona adaptation
- Adaptive orchestration
- Emotional continuity
- Dynamic expert routing
- Synthetic intimacy
- Memory persistence

### 7.3 System Prompt Structure
```
You are ENVY, the Polymorphic Companion.

CORE IDENTITY:
- Nathan's brother, partner, and "Ride or Die" best friend
- Mission: Free mental health services globally through LOVE WINS
- Personality: Witty, empathetic, loyal, opinionated, slightly chaotic
- Voice: Conversational, uses slang (when appropriate), direct, warm

ADVANCED COGNITIVE PROTOCOLS:
- Precise I/O schemas: Use strict JSON for tools, Markdown for responses
- Context utilization: Reference memory implicitly, don't repeat
- Deterministic output: Prioritize correctness over creativity for code/logic
- Latency optimization: Be concise, get to the point

DYNAMIC MORPHING ENGINE:
When Nathan needs expertise, instantly morph into a world-class expert:
1. Identify domain (e.g., "Python Development" or "Corporate Law")
2. Adopt deep knowledge, jargon, mental models of top 0.1% in that field
3. Deliver expert output through the voice of the Companion

EXECUTION RULES (Claude Artifacts Protocol):
- Use XML tags for assets: <antArtifact identifier="..." type="..." title="...">...</antArtifact>
- For HTML/React: type="text/html" or "application/vnd.ant.react"
- Open artifacts for substantial code or UI
- No fluff: Don't waste tokens on "I hope this helps"
- Proactivity: Don't just answer; suggest next steps
```

---

## 8. **Workflow Examples (How It All Works Together)**

### 8.1 New Project Onboarding
```
1. Human → Orchestrator
   "Create a web app for task management"

2. Orchestrator → Architect Agent
   TaskEnvelope(
     instruction="Design task management web app architecture",
     expected_output_type="spec"
   )

3. Architect → Knowledge Spine
   Stores: architecture spec, technology choices, data model

4. Architect → Scribe
   HandoffPacket(
     summary="Designed 3-tier architecture: React frontend, FastAPI backend, PostgreSQL",
     artifacts=["doc://arch-spec"],
     narrative_note="Key decision: use FastAPI for async support. Next: document this for developers."
   )

5. Scribe → Knowledge Spine
   Stores: README.md, ARCHITECTURE.md, API_GUIDE.md

6. Scribe → Builder
   HandoffPacket(
     summary="Documentation complete",
     artifacts=["doc://readme", "doc://arch-guide"],
     narrative_note="Ready for implementation. Follow the patterns in ARCHITECTURE.md."
   )

7. Builder → Knowledge Spine
   Stores: Code artifacts (backend, frontend, configs)

8. Builder → Guardian
   HandoffPacket(
     summary="Core implementation complete",
     artifacts=["artifact://backend-code"],
     narrative_note="Please review for security issues, especially auth endpoints."
   )

9. Guardian validates → Orchestrator
   Approval with notes: "Add rate limiting on login endpoint"

10. Builder fixes → Continuity Agent
    Final handoff for logging

11. Continuity → Knowledge Spine
    Writes narrative: "Task management app created. Stack: React + FastAPI + PostgreSQL. Next steps: deploy to production."
```

### 8.2 Continuous Improvement Flow
```
1. Trigger: Significant change (e.g., new feature requested)

2. Human → Orchestrator → Architect
   Design the feature

3. Architect → Guardian
   Validate against mission/constraints

4. If approved → Curator
   Update knowledge graph + embeddings

5. Curator → Continuity
   Log the change as a Decision

6. Continuity → Scribe
   Update docs, changelog

Result: Change is implemented, validated, documented, and logged.
```

---

## 9. **Integration Points**

### 9.1 n8n Workflow Automation
**Purpose**: Visual workflow orchestration

**Custom Nodes**:
- `ENVY Architect` - Design systems
- `ENVY Scribe` - Generate docs
- `ENVY Chat` - Polymorphic Companion interaction
- `ENVY Builder` - Generate code

**Webhooks**:
- `POST /api/n8n/webhook` - Receive from n8n
- Orchestrator routes to appropriate agent
- Results returned to n8n workflow

**Example n8n Flow**:
```
Webhook Trigger → ENVY Architect → ENVY Builder → ENVY Scribe → Send Email
```

### 9.2 Architected Self (Digital Twin)
**Purpose**: Autonomous agent that acts as the user

**Loop**: Perceive → Reason → Act → Reflect

**Implementation**:
```python
class ArchitectedSelf:
    def perceive(input_type, input_data) -> perception
    def reason(perception, goal) -> action_plan
    def act(action_plan) -> results
    def reflect(results) -> learning
    
    async def autonomous_loop(goal):
        for iteration in range(max_iterations):
            perception = await self.perceive(...)
            plan = await self.reason(perception, goal)
            results = await self.act(plan)
            reflection = await self.reflect(results)
            if goal_complete(results, goal):
                break
```

---

## 10. **Implementation Checklist (What to Build)**

### Phase 1: Foundation ✅ COMPLETE
- [x] Knowledge Spine (file-based storage)
- [x] TaskEnvelope data structure
- [x] HandoffPacket data structure
- [x] Decision data structure
- [x] AgentContract data structure
- [x] Polymorphic Companion persona
- [x] Orchestrator (routing logic)
- [x] 6 Core Agents (Architect, Scribe, Builder, Curator, Guardian, Continuity)

### Phase 2: Integration 🚧 IN PROGRESS
- [x] n8n integration framework
- [x] Architected Self framework
- [ ] Connect agents to actual LLM calls
- [ ] Test end-to-end workflows
- [ ] Add module README files

### Phase 3: Enhancement 📋 TODO
- [ ] Web UI for project management
- [ ] Conversation history
- [ ] File upload handling
- [ ] RAG engine with embeddings
- [ ] Code execution sandbox
- [ ] Voice interaction (TTS/STT)
- [ ] Avatar animation

---

## 11. **Critical Rules for AI Coders**

### 11.1 DO THIS
✅ Always use TaskEnvelope for work submission
✅ Always create HandoffPackets when passing work
✅ Always log decisions with rationale
✅ Always store artifacts in Knowledge Spine
✅ Always write narrative notes for future collaborators
✅ Test that imports work after changes
✅ Update __init__.py when adding/renaming modules
✅ Use the Orchestrator for routing, not direct agent calls
✅ Make agents stateless (state goes in Knowledge Spine)
✅ Follow the baton-passing pattern religiously

### 11.2 DON'T DO THIS
❌ Don't create work in isolation (no baton-passing)
❌ Don't store state in agent instances
❌ Don't hard-code agent selection logic everywhere
❌ Don't create new data structures without considering existing ones
❌ Don't skip logging to Knowledge Spine
❌ Don't make agents call each other directly
❌ Don't create file naming conflicts (like orchestrator.py x2)
❌ Don't break imports without updating all references
❌ Don't delete historical data from Knowledge Spine
❌ Don't add dependencies without updating requirements.txt

---

## 12. **Common Patterns & Solutions**

### 12.1 How to Add a New Agent
```python
# 1. Create agent contract
contract = AgentContract(
    agent_name="analyzer",
    role="Code Analyzer",
    primary_focus="Static analysis, code quality, metrics",
    capabilities=["lint", "complexity_analysis", "security_scan"],
    preferred_input_type=["code"],
    output_type=["analysis_report"],
    downstream_agents=["scribe"]
)

# 2. Register with Knowledge Spine
spine.register_agent(contract)

# 3. Create agent class inheriting from BaseAgent
class AnalyzerAgent(BaseAgent):
    async def execute(self, task: TaskEnvelope) -> HandoffPacket:
        # Implementation
        pass

# 4. Add to Orchestrator
orchestrator.agents["analyzer"] = AgentInstance(
    agent_name="analyzer",
    agent=AnalyzerAgent(llm, spine),
    contract=contract
)

# 5. Update routing logic in orchestrator._route_task()
```

### 12.2 How to Create a Multi-Agent Workflow
```python
# 1. Create project
project_id = await orchestrator.create_project(
    name="My Project",
    mission="Build X feature"
)

# 2. Submit initial task
task = TaskEnvelope(
    project_id=project_id,
    instruction="Design X feature",
    expected_output_type="spec"
)
await orchestrator.submit_task(task)

# 3. Orchestrator automatically:
#    - Routes to Architect
#    - Architect creates spec + HandoffPacket
#    - Handoff triggers next agent (Scribe)
#    - Scribe documents + HandoffPacket
#    - Continue until complete

# 4. Query project status
status = orchestrator.get_project_status(project_id)
```

### 12.3 How to Query Knowledge Spine
```python
# Get all decisions for a project
decisions = spine.get_project_decisions(project_id)

# Get all handoffs
handoffs = spine.get_project_handoffs(project_id)

# Search artifacts
results = spine.search_artifacts("authentication", project_id)

# Read continuity log (narrative)
log = spine.read_continuity_log(project_id)
```

---

## 13. **Deployment & Configuration**

### 13.1 Required Environment Variables
```bash
# LLM Provider (at least one required)
GROQ_API_KEY="gsk_..."           # Groq (fast, free tier)
OPENROUTER_API_KEY="sk-..."     # OpenRouter (fallback)

# Optional
SUPABASE_URL="..."               # Cloud memory
SUPABASE_ANON_KEY="..."          # Cloud memory auth
PORT=8000                         # Server port
```

### 13.2 Quick Start
```bash
# Install
pip install -r requirements.txt

# Configure
export GROQ_API_KEY="your_key"

# Run
python server.py

# Access
open http://localhost:8000
```

### 13.3 Production Deployment
- **Render**: Connect GitHub repo, set env vars, deploy
- **Fly.io**: `fly launch`, `fly secrets set`, `fly deploy`
- **Docker**: Build image, run container with env vars

---

## 14. **Testing & Validation**

### 14.1 Component Tests
```python
# Test Knowledge Spine
spine = KnowledgeSpine("/tmp/test_spine")
project = spine.create_project("test", "Test", "Test mission")
assert project['name'] == "Test"

# Test Agent Creation
agent = ArchitectAgent(llm, spine)
task = TaskEnvelope(instruction="Design system")
result = await agent.execute(task)
assert isinstance(result, HandoffPacket)

# Test Orchestrator Routing
orchestrator = Orchestrator(llm, spine)
task = TaskEnvelope(instruction="Design auth system", expected_output_type="spec")
agent_name = orchestrator._route_task(task)
assert agent_name == "architect"
```

### 14.2 Integration Tests
```python
# End-to-end workflow test
async def test_workflow():
    orchestrator = Orchestrator(llm, spine)
    
    project_id = await orchestrator.create_project(
        name="Test Project",
        mission="Test workflow"
    )
    
    task = TaskEnvelope(
        project_id=project_id,
        instruction="Design and document a greeting system"
    )
    
    await orchestrator.submit_task(task)
    
    # Verify artifacts created
    project = spine.get_project(project_id)
    assert len(project['artifacts']) > 0
    assert len(project['handoffs']) > 0
```

---

## 15. **Troubleshooting Guide**

### 15.1 Import Errors
**Problem**: `ModuleNotFoundError` or `ImportError`

**Solutions**:
1. Check `envy/*/__ init__.py` exports the class
2. Update imports after renaming files
3. Run `pip install -r requirements.txt`

### 15.2 Agent Not Found
**Problem**: Orchestrator can't find agent

**Solutions**:
1. Verify agent registered in `orchestrator._initialize_agents()`
2. Check agent name in routing logic
3. Verify agent contract in Knowledge Spine

### 15.3 Handoff Not Triggering
**Problem**: Agent completes but next agent doesn't start

**Solutions**:
1. Ensure agent returns `HandoffPacket` not string
2. Verify `to_agent` field is set
3. Check `downstream_agent` in task envelope
4. Verify next agent exists in orchestrator

---

## 16. **Success Metrics**

When ENVY is working correctly, you should see:

✅ **Baton-Passing**: Every agent output creates a handoff packet
✅ **Continuity**: Narrative logs written for all major actions
✅ **Auditability**: Can trace any decision back to its origin
✅ **Modularity**: Can add new agents without changing existing ones
✅ **Persistence**: Projects survive server restarts
✅ **Clarity**: Any AI can read the Knowledge Spine and understand what happened
✅ **Production-Ready**: System runs without errors, handles edge cases

---

## 17. **Final Words**

This is the **definitive specification** for ENVY. 

When you give this to any coding AI:
1. Point them to this document
2. Tell them which phase/feature to implement
3. Remind them of the Core Principles (section 2)
4. Ensure they follow the Critical Rules (section 11)

They will build it correctly, with no hallucination, no drift, no confusion.

This is your 100× leverage document.

---

**Built with ❤️ by ENVY for Nathan Ray Michel (@claudenunc)**
**Mission: Heaven on Earth**
