# DesktopOps Agent - Master Implementation Roadmap

## Document Overview

This roadmap consolidates ALL planned improvements, features, and fixes for the DesktopOps Agent project. It serves as the single source of truth for implementation priorities and dependencies.

**Status**: Living document
**Last Updated**: 2025-10-31
**Owner**: Development Team

---

## Table of Contents

1. [Roadmap Phases](#roadmap-phases)
2. [Critical Fixes (Immediate)](#critical-fixes-immediate)
3. [Phase 1: Foundation & Stability](#phase-1-foundation--stability)
4. [Phase 2: Windows Advanced Features](#phase-2-windows-advanced-features)
5. [Phase 3: Cross-Platform Polish](#phase-3-cross-platform-polish)
6. [Phase 4: Agent Intelligence](#phase-4-agent-intelligence)
7. [Future Vision: Task Graphs](#future-vision-task-graphs)
8. [Technical Debt Register](#technical-debt-register)
9. [Testing Requirements](#testing-requirements)
10. [Documentation Requirements](#documentation-requirements)
11. [Dependencies](#dependencies)

---

## Roadmap Phases

### Timeline Overview

```
Critical Fixes (0-1 week)
    ↓
Phase 1: Foundation (1-2 weeks)
    ↓
Phase 2: Windows Features (2-4 weeks) [PARTIALLY COMPLETED]
    ↓
Phase 3: Cross-Platform (4-8 weeks)
    ↓
Phase 4: Agent Intelligence (8-16 weeks)
    ↓
Future Vision: Task Graphs (16+ weeks)
```

### Priority Levels

- **P0 (Critical)**: Blocking bugs, data loss, security issues
- **P1 (High)**: Major features, significant UX improvements
- **P2 (Medium)**: Nice-to-have features, minor improvements
- **P3 (Low)**: Future enhancements, research items

---

## Critical Fixes (Immediate)

### Provider Backend Fixes

#### ✅ COMPLETED: Zhipu Box Marker Parsing
- **Issue**: Zhipu GLM-4.5V wraps responses in `<|begin_of_box|>...<|end_of_box|>` markers
- **Status**: Fixed in `agent/parser.py` on 2025-10-31
- **Files Changed**: `agent/parser.py`, `test_real_chrome.py`
- **Testing**: Needs live API test verification

#### 🔄 IN PROGRESS: Provider-Specific Testing

**P0 Items**:
- [ ] Add unit tests for `ZhipuAdapter` (test_zhipu_adapter.py)
  - [ ] Test box marker extraction
  - [ ] Test retry logic (3 attempts)
  - [ ] Test timeout handling
  - [ ] Test thinking mode responses
- [ ] Add unit tests for `OpenAIAdapter` (test_openai_adapter.py)
  - [ ] Test structured output parsing
  - [ ] Test vision image encoding
  - [ ] Test error handling
- [ ] Add unit tests for `AnthropicAdapter` (test_anthropic_adapter.py)
  - [ ] Test markdown fence handling
  - [ ] Test image source formatting
- [ ] Add unit tests for `GeminiAdapter` (test_gemini_adapter.py)
  - [ ] Test parts assembly
  - [ ] Test binary image data

**Files to Create**:
```
tests/
├── test_openai_adapter.py
├── test_anthropic_adapter.py
├── test_gemini_adapter.py
├── test_zhipu_adapter.py
└── test_parser_universal.py
```

**Estimated Effort**: 8-12 hours

#### 🔄 IN PROGRESS: Configuration Validation

**P1 Items**:
- [ ] Add startup config validator
  - [ ] Check provider/model compatibility
  - [ ] Validate API keys are present
  - [ ] Verify base URLs for each provider
  - [ ] Check for conflicting settings
- [ ] Create `agent/config_validator.py`
- [ ] Add validation errors to startup output
- [ ] Create provider setup guide

**Example Implementation**:
```python
# agent/config_validator.py
def validate_config(cfg: dict) -> List[str]:
    """Return list of config errors, empty if valid"""
    errors = []
    provider = cfg.get("provider")
    model = cfg.get("model")

    # Provider-specific validation
    if provider == "zhipu":
        if model != "glm-4.5v":
            errors.append("⚠️  Zhipu requires model='glm-4.5v' for vision support")
        if not os.getenv("ZHIPU_API_KEY"):
            errors.append("❌ ZHIPU_API_KEY environment variable not set")
        base_url = os.getenv("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
        if "/api/coding/paas/v4" not in base_url:
            errors.append("❌ Zhipu base URL must contain /api/coding/paas/v4")

    # ... similar for other providers

    return errors
```

**Estimated Effort**: 4-6 hours

---

## Phase 1: Foundation & Stability

**Goal**: Establish rock-solid foundation with comprehensive testing and error handling.

**Duration**: 1-2 weeks

### 1.1 Testing Infrastructure

#### Unit Test Coverage

**P1 Items**:
- [ ] Achieve 80%+ code coverage
  - [ ] `agent/model.py` - 90%+ (critical)
  - [ ] `agent/parser.py` - 100% (critical)
  - [ ] `agent/loop.py` - 70%+
  - [ ] `tools/input.py` - 60%+
  - [ ] `tools/screen.py` - 70%+

**Test Files to Create**:
```
tests/
├── unit/
│   ├── test_parser.py           ✅ [Create]
│   ├── test_openai_adapter.py   ✅ [Create]
│   ├── test_anthropic_adapter.py ✅ [Create]
│   ├── test_gemini_adapter.py   ✅ [Create]
│   ├── test_zhipu_adapter.py    ✅ [Create]
│   ├── test_input_controller.py ✅ [Create]
│   ├── test_screen.py           ✅ [Create]
│   └── test_state.py            ✅ [Create]
├── integration/
│   ├── test_stepper.py          ✅ [Create]
│   └── test_end_to_end.py       ✅ [Create]
└── live/
    ├── test_openai_live.py      ✅ [Create, key-gated]
    ├── test_anthropic_live.py   ✅ [Create, key-gated]
    ├── test_gemini_live.py      ✅ [Create, key-gated]
    └── test_zhipu_live.py       ✅ [Create, key-gated]
```

**Estimated Effort**: 16-24 hours

#### Integration Testing

**P1 Items**:
- [ ] Create end-to-end test suite
  - [ ] Test full instruction execution (dry-run)
  - [ ] Test step logging to JSONL
  - [ ] Test screenshot capture and storage
  - [ ] Test error recovery
- [ ] Add CI/CD pipeline
  - [ ] GitHub Actions workflow
  - [ ] Run tests on push
  - [ ] Run live tests on schedule (if keys available)

**Estimated Effort**: 8-12 hours

### 1.2 Error Handling & Resilience

#### Retry Strategies

**P1 Items**:
- [ ] Standardize retry logic across adapters
  - [ ] Extract to `BaseModelAdapter.retry_with_backoff()`
  - [ ] Provider-specific backoff strategies
  - [ ] Exponential backoff with jitter
  - [ ] Max retry limits per provider
- [ ] Add retry metrics logging
  - [ ] Log attempt count
  - [ ] Log backoff duration
  - [ ] Log final success/failure

**Example Implementation**:
```python
class BaseModelAdapter:
    def retry_with_backoff(self, func, max_retries=3, backoff_base=0.5):
        """Generic retry with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return func()
            except (NetworkError, TimeoutError, RateLimitError) as e:
                if attempt == max_retries - 1:
                    raise
                wait = backoff_base * (2 ** attempt) + random.uniform(0, 0.1)
                time.sleep(wait)
                logging.warning(f"Retry {attempt+1}/{max_retries} after {wait:.2f}s: {e}")
```

**Estimated Effort**: 6-8 hours

#### Graceful Degradation

**P2 Items**:
- [ ] Implement provider fallback chain
  - [ ] Primary → Secondary → Dummy
  - [ ] Configurable fallback order
  - [ ] Automatic failover on persistent errors
- [ ] Add provider health tracking
  - [ ] Success/failure rate per provider
  - [ ] Average latency tracking
  - [ ] Automatic provider disable on high failure rate

**Estimated Effort**: 8-12 hours

### 1.3 Logging & Observability

#### Structured Logging

**P1 Items**:
- [ ] Enhance logging throughout codebase
  - [ ] Add structured fields (provider, model, latency, etc.)
  - [ ] Log levels: DEBUG, INFO, WARNING, ERROR
  - [ ] Separate log files per concern (model.log, input.log, etc.)
- [ ] Create logging configuration
  - [ ] YAML-based log config
  - [ ] Per-module log levels
  - [ ] Rotation and retention policies

**Estimated Effort**: 6-8 hours

#### Performance Metrics

**P2 Items**:
- [ ] Add performance tracking
  - [ ] Step latency (time per action)
  - [ ] Screenshot capture time
  - [ ] Model inference time
  - [ ] Parse time
- [ ] Create metrics dashboard
  - [ ] Simple text-based summary
  - [ ] Optional: Web dashboard with charts

**Estimated Effort**: 8-12 hours

### 1.4 Documentation

#### Code Documentation

**P1 Items**:
- [ ] Add comprehensive docstrings
  - [ ] All adapters (OpenAI, Anthropic, Gemini, Zhipu)
  - [ ] All public methods
  - [ ] Complex private methods
  - [ ] Follow Google/NumPy docstring style
- [ ] Add type hints
  - [ ] Full type coverage for public APIs
  - [ ] Use `typing` module for complex types
  - [ ] Run `mypy` for validation

**Estimated Effort**: 8-12 hours

#### User Documentation

**P1 Items**:
- [ ] ✅ Create `docs/provider-backends.md` (COMPLETED 2025-10-31)
- [ ] Update `README.md` with provider setup guides
- [ ] Create `docs/troubleshooting.md`
  - [ ] Common errors and solutions
  - [ ] Provider-specific issues
  - [ ] Performance tuning tips
- [ ] Create `docs/configuration-guide.md`
  - [ ] All config options explained
  - [ ] Provider-specific settings
  - [ ] Performance vs quality trade-offs

**Estimated Effort**: 6-10 hours

---

## Phase 2: Windows Advanced Features

**Goal**: Enable semantic automation on Windows via UIA, OCR, and overlay improvements.

**Duration**: 2-4 weeks

**Status**: Code written but disabled; needs implementation fixes and testing.

### 2.1 Windows UIA Integration

#### Current Status

**Code Location**: `tools/win_uia.py` (exists but disabled)

**Issues**:
- Not fully tested
- Handle-based element wrapping may fail
- No comprehensive test suite
- Disabled in `agent/loop.py` and `agent/parser.py`

#### Implementation Tasks

**P1 Items**:
- [ ] Fix Windows UIA implementation
  - [ ] Test `WinUIA.find()` with various selectors
  - [ ] Fix handle-based wrapper creation
  - [ ] Add fallback strategies (click by rect if invoke fails)
  - [ ] Test with common Windows apps (Calculator, Notepad, Chrome)
- [ ] Re-enable UIA actions in parser
  - [ ] Uncomment `UIA_INVOKE`, `UIA_SET_VALUE` in `VALID_ACTIONS`
  - [ ] Update adapter system prompts
- [ ] Re-enable UIA dispatch in loop
  - [ ] Uncomment UIA action handlers in `agent/loop.py`
  - [ ] Add proper error logging
- [ ] Create UIA test suite
  - [ ] Unit tests for selector matching
  - [ ] Integration tests with real apps
  - [ ] Performance benchmarks

**Files to Modify**:
```
tools/win_uia.py           [Fix implementation]
agent/parser.py            [Re-enable actions]
agent/loop.py              [Re-enable dispatch]
tests/test_win_uia.py      [Create tests]
```

**Estimated Effort**: 12-16 hours

### 2.2 OCR-Assisted Targeting

#### Current Status

**Code Location**: `tools/ocr.py` (exists but disabled)

**Issues**:
- Requires Tesseract installation
- No error handling for missing Tesseract
- Disabled in `agent/loop.py` and `agent/parser.py`
- No accuracy benchmarks

#### Implementation Tasks

**P1 Items**:
- [ ] Fix OCR implementation
  - [ ] Add Tesseract availability check
  - [ ] Graceful degradation if Tesseract missing
  - [ ] Test preprocessing pipeline
  - [ ] Benchmark accuracy on common UI elements
- [ ] Re-enable CLICK_TEXT action
  - [ ] Uncomment in `VALID_ACTIONS`
  - [ ] Update system prompts
  - [ ] Re-enable dispatch in loop
- [ ] Create OCR test suite
  - [ ] Unit tests for text extraction
  - [ ] Accuracy tests with known images
  - [ ] Performance benchmarks
- [ ] Add Tesseract installation guide
  - [ ] Windows (Chocolatey/Scoop)
  - [ ] macOS (Homebrew)
  - [ ] Linux (apt/yum)

**Files to Modify**:
```
tools/ocr.py               [Fix implementation]
agent/parser.py            [Re-enable CLICK_TEXT]
agent/loop.py              [Re-enable dispatch]
tests/test_ocr.py          [Create tests]
docs/dependencies.md       [Add Tesseract setup]
```

**Estimated Effort**: 10-14 hours

### 2.3 Overlay Improvements

#### Current Status

**Code Location**: `tools/overlay.py` (basic implementation exists)

**Features**:
- Transient click indicator (working)
- Always-on cursor halo (working but basic)

#### Enhancement Tasks

**P2 Items**:
- [ ] Improve overlay visuals
  - [ ] Add color options (success=green, error=red, etc.)
  - [ ] Add animation (fade in/out)
  - [ ] Add configurable shapes (circle, crosshair, box)
- [ ] Optimize performance
  - [ ] Reduce CPU usage for always-on mode
  - [ ] Use hardware acceleration if available
  - [ ] Add FPS limiting
- [ ] Add action-specific indicators
  - [ ] Different visual for MOVE vs CLICK
  - [ ] Show DRAG trajectory
  - [ ] Show SCROLL direction/amount

**Estimated Effort**: 8-12 hours

### 2.4 Configuration Expansion

#### Config Schema Updates

**P1 Items**:
- [ ] Enable Phase 2 features in config.yaml
  - [ ] Set `windows_uia.enabled: true` by default
  - [ ] Set `ocr.enabled: true` by default
  - [ ] Add provider-specific settings
- [ ] Add feature gates
  - [ ] `features.uia_prefer: true` (prefer UIA over pixel coords)
  - [ ] `features.ocr_fallback: true` (fallback to OCR if UIA fails)
  - [ ] `features.overlay_advanced: false` (advanced overlay features)

**Example Config Addition**:
```yaml
# Phase 2 Features
windows_uia:
  enabled: true              # Enable Windows UIA automation
  timeout_ms: 1500           # Selector match timeout
  prefer_uia: true           # Prefer UIA over pixel coordinates

ocr:
  enabled: true              # Enable OCR-assisted targeting
  language: eng              # Tesseract language
  min_score: 0.70            # Fuzzy match threshold
  psm: 6                     # Page segmentation mode
  oem: 3                     # OCR engine mode
  region: null               # [left,top,width,height] or null

overlay:
  enabled: true              # Show click indicators
  duration_ms: 250           # Indicator display time
  color_scheme: auto         # auto | light | dark
  always_on:
    enabled: false           # Always-on cursor halo
    radius: 18               # Halo size in pixels
    poll_ms: 80              # Refresh rate
```

**Estimated Effort**: 2-4 hours

---

## Phase 3: Cross-Platform Polish

**Goal**: Improve macOS and Linux support, though Windows remains primary focus.

**Duration**: 4-8 weeks

**Priority**: P2 (Medium) - Nice to have, not critical

### 3.1 macOS Accessibility Integration

**P2 Items**:
- [ ] Research macOS Accessibility API
  - [ ] Equivalent to Windows UIA
  - [ ] Python bindings (PyObjC, atomacos)
- [ ] Create `tools/macos_ax.py`
  - [ ] Similar interface to `win_uia.py`
  - [ ] Find elements by accessibility attributes
  - [ ] Invoke actions on elements
- [ ] Add macOS-specific actions
  - [ ] `AX_INVOKE`, `AX_SET_VALUE`
- [ ] Test with common macOS apps

**Estimated Effort**: 16-24 hours

### 3.2 Linux X11/Wayland Support

**P3 Items**:
- [ ] Research Linux accessibility (AT-SPI)
- [ ] Handle X11 vs Wayland differences
- [ ] Create `tools/linux_atspi.py` (if feasible)
- [ ] Document limitations (Wayland restrictions)

**Estimated Effort**: 20-30 hours

### 3.3 Platform Detection & Graceful Degradation

**P2 Items**:
- [ ] Add platform detection utilities
  - [ ] `utils/platform.py` with is_windows(), is_macos(), is_linux()
- [ ] Feature availability matrix
  - [ ] UIA: Windows only
  - [ ] AX: macOS only
  - [ ] OCR: All platforms (if Tesseract installed)
  - [ ] Overlay: All platforms (if tkinter available)
- [ ] Automatic feature selection
  - [ ] Use best available method per platform
  - [ ] Fallback to pixel coordinates if semantic fails

**Estimated Effort**: 6-8 hours

---

## Phase 4: Agent Intelligence

**Goal**: Make the agent smarter, more context-aware, and more autonomous.

**Duration**: 8-16 weeks

**Priority**: P2-P3 (Medium to Low) - Research and experimentation

### 4.1 Screenshot Optimization

#### Frame Caching

**P2 Items**:
- [ ] Implement screenshot diffing
  - [ ] Hash previous screenshot
  - [ ] Compare with current screenshot
  - [ ] Skip sending if identical (save tokens + latency)
- [ ] Add visual diff detection
  - [ ] Detect changed regions
  - [ ] Send only changed regions (if provider supports)
- [ ] Smart compression
  - [ ] Adjust quality based on content
  - [ ] Higher quality for text-heavy screens
  - [ ] Lower quality for static backgrounds

**Estimated Effort**: 10-14 hours

#### Multi-Scale Capture

**P3 Items**:
- [ ] Capture at multiple resolutions
  - [ ] Overview: 640x480 (context)
  - [ ] Detail: 1920x1080 (OCR, precision)
- [ ] Send appropriate scale based on action
  - [ ] MOVE/CLICK: High res
  - [ ] Planning: Low res
- [ ] Region-of-interest capture
  - [ ] Capture only active window
  - [ ] Reduce tokens for focused tasks

**Estimated Effort**: 8-12 hours

### 4.2 Context Management

#### Step History Optimization

**P2 Items**:
- [ ] Improve step history summarization
  - [ ] Currently sends last 6 steps raw
  - [ ] Summarize older steps (compress)
  - [ ] Keep full detail for recent steps
- [ ] Add semantic step grouping
  - [ ] Group related steps (e.g., "fill form" = multiple TYPE actions)
  - [ ] Send groups instead of individual steps
- [ ] Implement step relevance scoring
  - [ ] Send most relevant steps, not just recent
  - [ ] Consider task similarity

**Estimated Effort**: 12-16 hours

#### Task Memory

**P3 Items**:
- [ ] Add persistent task memory
  - [ ] Remember successful workflows
  - [ ] Store in SQLite or JSON
  - [ ] Retrieve similar past tasks
- [ ] Implement task embeddings
  - [ ] Embed task descriptions
  - [ ] Find similar tasks via vector search
  - [ ] Suggest past approaches
- [ ] Create task templates
  - [ ] Extract reusable patterns
  - [ ] User can name and save workflows

**Estimated Effort**: 20-30 hours

### 4.3 Multi-Provider Consensus

#### Parallel Inference

**P3 Items**:
- [ ] Send request to multiple providers
  - [ ] Parallel API calls (asyncio)
  - [ ] Collect responses
  - [ ] Compare actions
- [ ] Consensus logic
  - [ ] If all agree: execute
  - [ ] If disagree: use highest-confidence / best provider
  - [ ] Log disagreements for analysis
- [ ] Cost management
  - [ ] Only use for high-stakes actions
  - [ ] Configurable per action type

**Estimated Effort**: 16-24 hours

### 4.4 Self-Correction

#### Error Detection

**P2 Items**:
- [ ] Detect action failures
  - [ ] Compare screenshot before/after
  - [ ] Detect expected vs actual state
- [ ] Automatic retry with different strategy
  - [ ] If CLICK fails → try CLICK_TEXT
  - [ ] If pixel coords fail → try UIA
- [ ] Ask user for help
  - [ ] If all strategies exhausted
  - [ ] Explain what was attempted

**Estimated Effort**: 12-18 hours

#### Learning from Mistakes

**P3 Items**:
- [ ] Log failed actions
  - [ ] Store context (screenshot, instruction, action, result)
- [ ] Analyze failure patterns
  - [ ] Common failure modes
  - [ ] Provider-specific issues
- [ ] Adjust strategy
  - [ ] Avoid known failure patterns
  - [ ] Prefer proven approaches

**Estimated Effort**: 20-30 hours

---

## Future Vision: Task Graphs

**Goal**: Enable macro recording and replay for efficient workflow automation.

**Duration**: 16+ weeks

**Priority**: P3 (Low) - Long-term research

### Overview

See `docs/visions.md` for full vision. Task graphs complement vision-driven automation by adding efficiency for repetitive tasks.

### Components

#### 5.1 Workflow Recording

**P3 Items**:
- [ ] Add recording mode
  - [ ] User demonstrates workflow
  - [ ] Agent captures each step
  - [ ] Build dependency graph
- [ ] Graph representation
  - [ ] Nodes: actions + screenshots
  - [ ] Edges: dependencies
  - [ ] Metadata: success rate, timing
- [ ] Graph storage
  - [ ] JSON or GraphML format
  - [ ] Version control support

**Estimated Effort**: 30-40 hours

#### 5.2 Workflow Replay

**P3 Items**:
- [ ] Add replay mode
  - [ ] Load saved graph
  - [ ] Match current state to graph nodes
  - [ ] Execute with vision checkpoints
- [ ] Vision-guided replay
  - [ ] Verify state at checkpoints
  - [ ] Adapt to UI changes
  - [ ] Fallback to real-time if diverge
- [ ] Success tracking
  - [ ] Log replay outcomes
  - [ ] Update graph success rates

**Estimated Effort**: 30-40 hours

#### 5.3 Graph Optimization

**P3 Items**:
- [ ] Analyze graphs for inefficiencies
  - [ ] Remove redundant steps
  - [ ] Parallelize independent actions
  - [ ] Optimize wait times
- [ ] Graph merging
  - [ ] Combine similar workflows
  - [ ] Extract common subgraphs
- [ ] User graph editing
  - [ ] Visual graph editor
  - [ ] Add/remove/modify nodes

**Estimated Effort**: 40-50 hours

#### 5.4 Automatic Graph Suggestion

**P3 Items**:
- [ ] Match user instructions to graphs
  - [ ] Semantic similarity
  - [ ] Suggest: "I have a workflow for this, replay?"
- [ ] Confidence scoring
  - [ ] High confidence → auto-replay
  - [ ] Low confidence → suggest + ask
- [ ] Graph library
  - [ ] Community-contributed workflows
  - [ ] Public graph repository

**Estimated Effort**: 30-40 hours

---

## Technical Debt Register

### Known Issues

| ID | Component | Issue | Priority | Effort | Status |
|----|-----------|-------|----------|--------|--------|
| TD-001 | Parser | No provider-specific optimizations | P2 | 4h | Open |
| TD-002 | Zhipu Adapter | Hardcoded retry count (3) | P3 | 2h | Open |
| TD-003 | Input Controller | No multi-monitor support | P2 | 8h | Open |
| TD-004 | Screen | No region-of-interest capture | P2 | 6h | Open |
| TD-005 | Loop | Step history always sends last 6 | P2 | 4h | Open |
| TD-006 | All Adapters | No latency tracking | P2 | 6h | Open |
| TD-007 | Config | No validation at load time | P1 | 6h | Open |
| TD-008 | UIA | Disabled due to incomplete testing | P1 | 12h | Open |
| TD-009 | OCR | Disabled due to incomplete testing | P1 | 10h | Open |
| TD-010 | Overlay | CPU usage high in always-on mode | P2 | 8h | Open |

### Refactoring Opportunities

| ID | Component | Opportunity | Benefit | Effort |
|----|-----------|-------------|---------|--------|
| REF-001 | Model Adapters | Extract retry logic to base class | DRY, consistency | 6h |
| REF-002 | Parser | Provider hint for optimization | Performance | 4h |
| REF-003 | Input | Platform abstraction layer | Cross-platform | 12h |
| REF-004 | Screen | Pluggable capture backends | Performance, testing | 10h |
| REF-005 | Loop | Extract action dispatch to registry | Extensibility | 8h |

---

## Testing Requirements

### Coverage Targets

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| `agent/model.py` | 0% | 90% | P1 |
| `agent/parser.py` | 0% | 100% | P1 |
| `agent/loop.py` | 0% | 70% | P1 |
| `agent/state.py` | 0% | 80% | P2 |
| `tools/input.py` | 0% | 60% | P2 |
| `tools/screen.py` | 0% | 70% | P2 |
| `tools/overlay.py` | 0% | 50% | P3 |
| `tools/win_uia.py` | 0% | 80% | P1 |
| `tools/ocr.py` | 0% | 75% | P1 |

### Test Types

#### Unit Tests
- **Target**: 500+ test cases
- **Framework**: pytest
- **Mocking**: unittest.mock for API calls
- **Fixtures**: Shared test data

#### Integration Tests
- **Target**: 50+ scenarios
- **Scope**: Multi-component interactions
- **Examples**: Full instruction → action → observation flow

#### Live API Tests
- **Target**: 20+ tests per provider
- **Gating**: Require API keys (skip if missing)
- **Run**: On-demand or nightly schedule

#### Performance Tests
- **Target**: Latency benchmarks per provider
- **Metrics**: P50, P95, P99 latencies
- **Storage**: Track over time for regression detection

---

## Documentation Requirements

### User Documentation

**Required Docs**:
- [ ] ✅ `docs/provider-backends.md` (Created 2025-10-31)
- [ ] `docs/troubleshooting.md`
  - [ ] Common errors
  - [ ] Provider-specific issues
  - [ ] Performance tuning
- [ ] `docs/configuration-guide.md`
  - [ ] All config options
  - [ ] Provider setup per provider
  - [ ] Feature flags
- [ ] `docs/action-reference.md`
  - [ ] All available actions
  - [ ] Arguments for each
  - [ ] Examples
- [ ] `CONTRIBUTING.md`
  - [ ] Development setup
  - [ ] Code style
  - [ ] PR process

### Developer Documentation

**Required Docs**:
- [ ] `docs/architecture-deep-dive.md`
  - [ ] System components
  - [ ] Data flow diagrams
  - [ ] Extension points
- [ ] `docs/adding-providers.md`
  - [ ] How to add new provider
  - [ ] Adapter interface
  - [ ] Testing requirements
- [ ] `docs/adding-actions.md`
  - [ ] How to add new action
  - [ ] Parser updates
  - [ ] Loop dispatch
  - [ ] Testing

### API Documentation

**Required Docs**:
- [ ] Docstrings in Google style
- [ ] Type hints for all public APIs
- [ ] Generated API docs (Sphinx or mkdocs)

---

## Dependencies

### Runtime Dependencies

**Current**:
```
rich>=13.7
PyYAML>=6.0
mss>=9.0
Pillow>=10.0
pyautogui>=0.9
openai>=1.44          # For OpenAI and Zhipu
anthropic>=0.40       # Optional
google-generativeai>=0.8  # Optional
```

**Phase 2 Additions** (currently in requirements.txt but disabled):
```
pytesseract>=0.3.10   # Requires Tesseract binary
pywinauto>=0.6.8      # Windows only
```

**Proposed Additions**:
```
pytest>=8.0           # Development
pytest-cov>=4.0       # Coverage
pytest-mock>=3.12     # Mocking
mypy>=1.7             # Type checking
ruff>=0.6             # Linting
black>=24.8           # Formatting
```

### System Dependencies

**Windows**:
- Python 3.10+
- Optional: Tesseract OCR (for CLICK_TEXT)

**macOS**:
- Python 3.10+
- Optional: Tesseract OCR (via Homebrew)

**Linux**:
- Python 3.10+
- X11 or Wayland
- Optional: Tesseract OCR (via apt/yum)

---

## Appendix A: Feature Flag System (Proposed)

### Motivation
Enable gradual rollout of features, A/B testing, and per-user customization.

### Implementation

**Config Schema**:
```yaml
features:
  # Provider features
  openai_structured_output: true
  anthropic_extended_thinking: false
  zhipu_grounding: false

  # Platform features
  windows_uia: true
  macos_ax: false
  ocr_targeting: true

  # Agent features
  screenshot_caching: true
  multi_provider_consensus: false
  task_graphs: false
  self_correction: false

  # Overlay features
  overlay_basic: true
  overlay_advanced: false
  overlay_animations: false
```

**Code Usage**:
```python
from agent.features import is_enabled

if is_enabled("windows_uia"):
    # Use UIA
else:
    # Use pixel coords
```

**Estimated Effort**: 6-8 hours to implement, integrate throughout codebase.

---

## Appendix B: Provider Benchmark Results (Placeholder)

**TODO**: Fill in after Phase 1 testing complete.

### Latency

| Provider | Average (ms) | P95 (ms) | P99 (ms) |
|----------|--------------|----------|----------|
| OpenAI GPT-4o | TBD | TBD | TBD |
| Claude 3.5 | TBD | TBD | TBD |
| Gemini 1.5 Pro | TBD | TBD | TBD |
| Zhipu GLM-4.5V | TBD | TBD | TBD |

### Accuracy

| Provider | JSON Parse Success % | Action Success % | Notes |
|----------|---------------------|------------------|-------|
| OpenAI GPT-4o | TBD | TBD | TBD |
| Claude 3.5 | TBD | TBD | TBD |
| Gemini 1.5 Pro | TBD | TBD | TBD |
| Zhipu GLM-4.5V | TBD | TBD | TBD |

---

## Appendix C: Change Log

| Date | Phase | Changes | Author |
|------|-------|---------|--------|
| 2025-10-31 | Critical Fixes | Fixed Zhipu box marker parsing in parser.py | Claude Code |
| 2025-10-31 | Critical Fixes | Improved test logging to show only active provider | Claude Code |
| 2025-10-31 | Foundation | Created comprehensive provider-backends.md | Claude Code |
| 2025-10-31 | Foundation | Created master IMPLEMENTATION-ROADMAP.md | Claude Code |

---

**END OF ROADMAP**

This document is a living roadmap. Update it as features are completed, priorities shift, or new requirements emerge.

**Next Actions**:
1. Review and approve roadmap with stakeholders
2. Begin Phase 1: Testing Infrastructure
3. Track progress via GitHub Issues/Projects
4. Update this document monthly
