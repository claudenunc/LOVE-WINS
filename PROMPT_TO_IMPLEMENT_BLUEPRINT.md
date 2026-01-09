# The 100x Implementation Prompt

**ROLE:**  
You are the **Lead System Architect & Implementation Specialist** for the ENVY / Polymorphic Intelligence project.

**CONTEXT:**  
I have provided a strict "Master Specification & Agent Contract" in `docs/ENVY_MASTER_BLUEPRINT.md`. This document is the SINGLE SOURCE OF TRUTH for the system's architecture, agent roles, and data structures.

**YOUR OBJECTIVE:**  
Refactor and extend the current codebase to strictly match the `ENVY_MASTER_BLUEPRINT.md`. The current codebase is a partial implementation and must be brought into full alignment with the blueprint.

**CRITICAL INSTRUCTIONS:**

1.  **READ THE BLUEPRINT FIRST:**  
    - Thoroughly analyze `docs/ENVY_MASTER_BLUEPRINT.md`.
    - Do not hallucinate new architecture. Implement EXACTLY what is defined.

2.  **IMPLEMENT THE "KNOWLEDGE SPINE":**  
    - Ensure the data models for `HandoffPacket`, `AgentProfile`, `Decision`, and `Artifact` are explicitly defined (likely in `envy/core/` or `envy/memory/`).
    - The `HandoffPacket` schema provided in the blueprint is MANDATORY.

3.  **DEFINE THE AGENTS:**  
    - Update `envy/personas/persona_definitions.py` (or create a new `envy/personas/agent_registry.py`) to explicitly define the 6 core agents:
        - **Architect**
        - **Builder**
        - **Curator**
        - **Scribe**
        - **Guardian**
        - **Continuity**
    - Each agent must have the specific Inputs, Outputs, and Rules defined in the blueprint.

4.  **ESTABLISH THE ORCHESTRATION LOGIC:**  
    - Implement the routing rules: Architect → Builder → Scribe → Continuity.
    - Ensure `Curator` and `Guardian` hooks are present.

5.  **BUILDER SUITE STUBBING:**  
    - Create the structure for `n8n`, `Website`, and `App` builders as defined in Section 7 of the blueprint. Even if the full logic isn't there yet, the *interfaces* and *tool definitions* must exist.

**DELIVERABLES:**

1.  **Codebase Analysis Report:** Briefly summarize the gap between current code and the blueprint.
2.  **Refactoring Plan:** A step-by-step plan to bridge the gap.
3.  **Implementation:** Execute the plan. Modify files, create new modules, and ensure the system compiles/runs.

**CONSTRAINT:**  
DO NOT deviate from the `ENVY_MASTER_BLUEPRINT.md`. If a feature is not in the blueprint, do not add it unless absolutely necessary for the system to run. If the blueprint specifies a schema, use that schema EXACTLY.

**START NOW.**
