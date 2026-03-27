# 🧠 Skill: Vertex — Spatial Versioning for 3D Environments

## 1. Overview

Vertex is a Git-integrated version control system for Blender that transforms binary `.blend` files into structured, domain-specific JSON representations.

This enables:
- Diffing of 3D scenes
- Non-linear collaboration
- AI-assisted merging
- Time-travel visualization of scene history

This skill orchestrates multiple agents to manage serialization, versioning, validation, and merging workflows.

---

## 2. System Architecture

### Core Layers

1. **Blender Layer (bpy)**
   - Source of truth for scene data
   - Objects, materials, lights, modifiers

2. **Serialization Layer**
   - Converts scene → domain JSON files
   - Ensures atomic, trackable units

3. **Git Middleware Layer**
   - Wraps Git CLI
   - Handles snapshot, commit, restore

4. **Agent Orchestration Layer (Antigravity)**
   - Coordinates tasks between agents
   - Maintains system state and workflows

---

## 3. Domain File Structure

### spatial.json
```json
{
  "name": "object_name",
  "loc": [x, y, z],
  "rot": [x, y, z],
  "scale": [x, y, z]
}

### materials.json
{
  "obj": "object_name",
  "mat_name": "material",
  "base_color": [r, g, b, a]
}

### lighting.json
{
  "light": "light_name",
  "type": "POINT",
  "energy": float,
  "color": [r, g, b]
}

### modifiers.json
{
  "obj": "object_name",
  "modifier": "type",
  "settings": {}
}

4. Agents
🧩 Agent 1: Antigravity (Architect)

Role:

System orchestrator
Task manager
Workflow controller

Responsibilities:

Maintain file structure
Trigger workflows
Coordinate between agents
Ensure consistency across domains

🛠 Agent 2: Developer Agent (Claude Code)

Role:

Implementation engine

Responsibilities:

Write Blender Python (bpy) scripts
Serialize scene into JSON
Restore scene from JSON
Validate data integrity

5. Core Workflows
5.1 Snapshot Workflow

Trigger: Scene update

Steps:

Iterate through bpy.data
Extract domain-specific data
Serialize into JSON files
Overwrite existing domain files

5.2 Commit Workflow

Steps:

Run:
git add .
git commit -m "vertex snapshot"
Store state in Git history

5.3 Restore Workflow

Trigger: Checkout commit

Steps:

Run: git checkout <commit_hash>
Load JSON files
Reconstruct scene using bpy

5.4 Visual Diff Workflow ("Ghosts")

Logic:

Compare current state vs previous commit

Steps:

Duplicate changed objects
Set:
display_type = 'WIRE'
color = (0,1,0,0.5)
Overlay in viewport

5.5 AI Merge Workflow

Trigger: Conflict in same object across branches

Steps:

Extract conflicting JSON states
Generate prompt:
Branch A: moved object
Branch B: changed material

Merge into a valid unified state
Apply merged result

6. Prompt Templates
6.1 Serialization Prompt

Extract all objects from bpy.data.objects and convert them into spatial.json format.
Ensure no duplicate object names exist.

6.2 Validation Prompt
Validate that:
- All object IDs are unique
- No missing references exist
- JSON schema is consistent

6.3 Merge Prompt

Given two JSON states of the same object:
- Preserve spatial transformations
- Merge non-conflicting attributes
- Resolve conflicts logically

Return a valid JSON object.

6.4 Restore Prompt
Read JSON domain files and reconstruct the Blender scene.
Ensure:
- Object hierarchy is preserved
- Materials and lighting are applied correctly

7. Constraints
JSON must be deterministic
No duplicate IDs
Git operations must be atomic
Scene reconstruction must be lossless
Domain separation must be maintained

8. Error Handling
Common Errors
Duplicate object names
Missing JSON fields
Git conflicts
Invalid bpy references
Strategy
Fail fast on validation
Log errors per domain
Provide recovery suggestions

9. Extensibility

Future capabilities:

Animation support (animation.json)
Physics simulation tracking
Multi-user real-time collaboration
Cloud sync layer
Scene dependency graph analysis

10. Success Metrics
≥95% reduction in repository size
Instant scene restoration (<3s)
Clean merge of conflicting edits
Visual clarity in diffing

11. Execution Notes for Antigravity
Always prioritize serialization consistency
Delegate code-heavy tasks to Developer Agent
Maintain strict separation between domains
Trigger workflows based on state changes

