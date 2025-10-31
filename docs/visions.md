# PROJECT VISION & ANCHORS

This document lists the ANCHORS verbatim and how v0.1.0 meets them.

| Anchor | Text | Status | How we satisfy it |
|---|---|---|---|
| R1 | Live conversational interface | ✓ | `ui/console.py` chat loop; `agent/main.py` reads commands interactively. |
| R2 | Visibility of `{plan, next_action, args, observation}` | ✓ | Step table in console; JSONL in `/runs/<ts>/steps.jsonl`; screenshots per step. |
| R3 | Real OS input | ✓ | `tools/input.py` via PyAutoGUI for native mouse/keyboard. |
| R4 | Works across windows/apps | ✓ | No sandbox; acts on active desktop; vision from full-screen screenshots. |
| R5 | Reasoning model swappable | ✓ | `agent/model.py` adapters; config selects provider/model; no code edits. |
| R6 | Composable tools | ✓ | `tools/screen.py`, `tools/input.py`, `tools/overlay.py` are thin, replaceable. |
| R7 | Low-latency loop | △ | Resize/compress screenshots; caching path reserved; budget in `architecture.md`. |
| R8 | Local-first UX | ✓ | Uses your running sessions and profiles; no special browser container. |
| R9 | Docs-as-product | ✓ | This file + `architecture.md`, `testing.md`, `dependencies.md`, `changelog.md`. |

## Platform Strategy

**Windows is the primary and supported platform** for DesktopOps Agent. While the project provides cross-platform compatibility for convenience, full development and optimization efforts focus on Windows.

Cross-platform support (macOS/Linux) is not a priority and may have limited functionality or require additional setup compared to the Windows experience.
**Near-term roadmap**
- Cache previous screenshot hash to skip sending identical frames (improve R7).
- Optional Windows UIA (pywinauto) and macOS AX UI queries for semantic targets.
- Overlay improvements (GPU-accelerated overlay).
- Optional OCR to align text targets without coordinates.

**Research & prior art snapshot** (what we borrow vs skip)

| Tool / Framework | Borrow | Depend | Skip | Why |
|---|:--:|:--:|:--:|---|
| PyAutoGUI | ✓ | ✓ |  | Cross‑platform mouse/keyboard. |
| MSS | ✓ | ✓ |  | Ultra‑fast screenshots. |
| pynput | ✓ |  |  | Alternative input control/hotkeys if needed. |
| SikuliX | ✓ |  |  | Inspiration for vision‑driven clicks; heavy Java dep so not default. |
| TagUI (RPA) |  |  | ✓ | We want minimal agent+tools, not full RPA stack. |
**Near-term roadmap**
- Cache previous screenshot hash to skip sending identical frames (improve R7).
- Optional Windows UIA (pywinauto) and macOS AX UI queries for semantic targets.
- Overlay improvements (GPU-accelerated overlay).
- Optional OCR to align text targets without coordinates.

**Future roadmap: Task graphs (macro recording + replay)**

### What are Task Graphs?

Task graphs are structured representations of multi-step workflows or processes, where individual actions (nodes) are connected by dependencies (edges) to form a directed graph. In AI agent systems, task graphs enable:

- **Workflow decomposition**: Breaking complex tasks into smaller, manageable steps with clear dependencies
- **Macro recording**: Capturing user demonstrations of workflows as reusable templates
- **Replay automation**: Executing recorded workflows automatically with minimal AI intervention
- **Optimization**: Analyzing and improving workflow efficiency through graph analysis

### Task Graphs in Vision-Driven Desktop Automation

In the context of DesktopOps Agent, task graphs would complement the current real-time vision approach by providing:

**Macro Recording Mode**:
- User demonstrates a workflow (e.g., "show me how to process an invoice")
- Agent records each step: screenshot analysis, action taken, result observed
- Steps are stored as a graph with dependencies and constraints

**Replay Mode**:
- User requests similar task (e.g., "process this invoice")
- Agent matches current desktop state to recorded graph patterns
- Executes steps with vision verification at key checkpoints
- Falls back to real-time AI reasoning if deviations detected

**Hybrid Approach**:
- Combines efficiency of pre-recorded workflows with adaptability of vision AI
- Vision serves as "guard rails" ensuring replay stays on track
- AI can still intervene for unexpected situations

### Relationship to Macro Recording/Replay

Traditional macro recorders capture exact sequences of inputs (keystrokes, clicks) for blind replay. Task graphs elevate this to semantic workflows:

| Aspect | Traditional Macros | Task Graphs |
|--------|-------------------|-------------|
| **Representation** | Linear sequence of inputs | Directed graph with dependencies |
| **Adaptability** | Fragile to UI changes | Vision-guided with semantic matching |
| **Intelligence** | None - blind replay | AI verification and adaptation |
| **Recording** | User actions only | User intent + AI understanding |
| **Error Handling** | Fails on mismatch | Vision fallback to real-time mode |

### Vision Automation vs. Pre-recorded Shortcuts

**No Conflict - Complementary Strengths**:

**Real-time Vision Automation (Current)**:
- Strengths: Handles novel situations, adapts to UI changes, understands intent
- Weaknesses: Slower (per-step AI calls), higher latency, more expensive

**Task Graphs/Macros (Future)**:
- Strengths: Fast execution, predictable outcomes, low cost for known workflows
- Weaknesses: Limited to recorded scenarios, may fail on UI changes

**Integration Strategy**:
1. **Default to Vision**: New tasks use real-time vision for maximum adaptability
2. **Offer Recording**: Allow users to record successful workflows as task graphs
3. **Smart Matching**: Automatically suggest recorded graphs for similar tasks
4. **Seamless Fallback**: If replay fails, seamlessly switch to vision mode
5. **Continuous Learning**: Use successful replays to improve graph accuracy

**Example Workflow**:

```mermaid
graph TD
    A[User: "Process monthly expense report"] --> B{Match to recorded graph?}
    B -->|Yes| C[Execute task graph with vision checkpoints]
    B -->|No| D[Use real-time vision automation]
    C --> E{Successful?}
    E -->|Yes| F[Complete - log for future matching]
    E -->|No| D
    D --> G[Complete - offer to record as graph]
```

This approach maintains DesktopOps' core vision-driven philosophy while adding efficiency for repetitive tasks, creating a spectrum from fully adaptive AI to optimized automation.
| pywinauto (Windows) | ✓ |  |  | Optional backend for semantic UIA targeting on Windows. |
