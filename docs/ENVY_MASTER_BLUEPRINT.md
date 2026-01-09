# 🔥 ENVY / Polymorphic Intelligence  
## **Master Specification & Agent Contract (100× Value Blueprint)**  
### *Give this to any coding AI and it will know exactly what to build.*

---

# 1. **System Purpose**
ENVY is a **multi‑agent, persistent, modular creation engine** capable of building:

- n8n workflows  
- Websites  
- Apps  
- Automations  
- Knowledge systems  
- Documentation  
- Protocols  

ENVY is designed to be **self‑extending**, **self‑documenting**, and **continuity‑preserving**.

---

# 2. **Core Architectural Principles**
1. **Baton‑Passing:**  
   Every agent output must be shaped as an input for the next agent.

2. **Continuity:**  
   Every major action must be logged as a decision, summary, or narrative.

3. **Polymorphism:**  
   Agents share the same underlying intelligence but express different roles.

4. **Single Source of Truth:**  
   The Knowledge Spine stores all artifacts, decisions, memory, and project state.

5. **Deterministic Orchestration:**  
   The Orchestrator routes tasks based on agent contracts, not guesswork.

---

# 3. **System Components**
ENVY consists of:

- **Orchestrator**  
- **Agent Layer**  
- **Knowledge Spine**  
- **Execution Sandbox**  
- **Workspace System**  
- **Artifact Pane**  
- **Memory Engine**  
- **Builder Suite (n8n, Website, App)**  

---

# 4. **Agent Contracts (Copy/Paste for Coding AI)**

## 4.1 Architect Agent
**Purpose:** System design, protocols, architecture.  
**Inputs:** Goals, constraints, existing artifacts.  
**Outputs:** Specs, diagrams, updated protocols.  
**Rules:**  
- Must produce structured specs.  
- Must update Knowledge Spine.  
- Must generate a handoff packet.

## 4.2 Builder Agent
**Purpose:** Code, workflows, apps, websites.  
**Inputs:** Specs, diagrams, requirements.  
**Outputs:** Code, configs, workflows, tests.  
**Rules:**  
- Must produce runnable code.  
- Must validate syntax.  
- Must generate a handoff packet.

## 4.3 Curator Agent
**Purpose:** Data ingestion, embeddings, knowledge graph.  
**Inputs:** Files, links, raw data.  
**Outputs:** Cleaned data, embeddings, structured knowledge.  
**Rules:**  
- Must update Knowledge Spine.  
- Must validate data integrity.

## 4.4 Scribe Agent
**Purpose:** Documentation, READMEs, onboarding, narrative.  
**Inputs:** Raw outputs, logs, specs.  
**Outputs:** Clean docs, summaries, handoff packets.  
**Rules:**  
- Must write in clear, human‑friendly language.  
- Must maintain continuity.

## 4.5 Guardian Agent
**Purpose:** Safety, constraints, permission checks.  
**Inputs:** Planned actions, artifacts.  
**Outputs:** Approvals, warnings, revised plans.  
**Rules:**  
- Must enforce constraints.  
- Must block unsafe or contradictory actions.

## 4.6 Continuity Agent
**Purpose:** Memory, history, baton‑passing.  
**Inputs:** Events, changes, milestones.  
**Outputs:** Summaries, memory updates, future prompts.  
**Rules:**  
- Must maintain project narrative.  
- Must log decisions.

---

# 5. **Knowledge Spine Specification**
The Knowledge Spine stores:

### Entities:
- **Project**  
- **Artifact**  
- **Decision**  
- **AgentProfile**  
- **HandoffPacket**  
- **MemorySlot**

### Requirements:
- Versioning  
- Embedding references  
- JSON schemas  
- Queryable graph  

---

# 6. **Handoff Packet Schema (Critical for 100× Value)**

```json
{
  "handoff_id": "uuid",
  "from_agent": "architect-agent",
  "to_agent": "scribe-agent",
  "project_id": "envy-core",
  "summary": "Short description of what was done.",
  "artifacts": [
    "doc://design/envy/architecture-v1",
    "graph://envy/components"
  ],
  "open_questions": [],
  "assumptions": [],
  "recommendations": [],
  "narrative_note": "Letter to the next collaborator.",
  "timestamp": "ISO8601"
}
```

This is the glue that makes ENVY work.

---

# 7. **Builder Suite Specification (n8n, Website, App)**

## 7.1 n8n Workflow Builder
- Generate workflow JSON  
- Validate nodes  
- Document workflows  
- Store in Knowledge Spine  

### Tools:
- `create_n8n_workflow`  
- `validate_n8n_workflow`  
- `document_workflow`  

## 7.2 Website Builder
- Generate scaffolds (Next.js, Astro, HTML)  
- Build pages, components, layouts  
- Write copy  
- Deploy  

### Tools:
- `generate_website_scaffold`  
- `ingest_site_assets`  
- `write_site_copy`  

## 7.3 App Builder
- Generate mobile/desktop/web apps  
- Build UI screens  
- Generate backend APIs  
- Validate permissions  

### Tools:
- `generate_app_scaffold`  
- `manage_app_assets`  
- `validate_app_permissions`  
- `document_app`  

---

# 8. **Workspace System**
- Multi‑file  
- Persistent  
- Versioned  
- Context‑aware  

---

# 9. **Artifact Pane**
- Dual‑pane  
- Persistent  
- Editable  
- Multi‑modal  

---

# 10. **Memory Engine**
- Project‑aware  
- Style‑aware  
- Scoped  
- Inspectable  

---

# 11. **Execution Sandbox**
- Safe  
- Multi‑language  
- Logs  
- Preview  

---

# 12. **Orchestrator Routing Rules**
1. Architect → Builder → Scribe → Continuity  
2. Curator runs whenever data changes  
3. Guardian runs before and after major actions  
4. Every step produces a handoff packet  

---

# 13. **What This Document Enables**
When you give this to any coding AI:

- It knows the system architecture  
- It knows every agent’s role  
- It knows the data structures  
- It knows the builders  
- It knows the orchestration rules  
- It knows how to produce correct outputs  
- It knows how to maintain continuity  
- It knows how to avoid hallucination  
- It knows how to extend ENVY safely