# TraceForge — Build Summary

## 1. Problem Solved
Modern software development requires navigating and understanding complex, unfamiliar codebases. Developers face several acute challenges:
- **Navigational Cognitive Load**: Comprehending non-trivial codebases through file trees obscures caller/callee paths and cross-module dependencies.
- **Graph "Hairball" Trap**: Standard code visualizers dump entire dependency graphs onto a canvas at once, rendering thousands of tangled nodes unreadable and crashing client browsers.
- **Unverifiable Summaries**: AI code summaries and static tools often lack ground-truth validation or exact source code references.
- **Security Hazards in Analysis**: Many existing dependency tools execute setup scripts or import modules dynamically, risking Remote Code Execution (RCE) on untrusted repositories.

TraceForge solves these problems by providing an evidence-first codebase intelligence platform that parses Python code purely via static AST inspection, stores the resulting topology in an actual Neo4j graph database, and allows developers to progressively explore dependency networks with line-level source code validation.

---

## 2. Solution & Key Features

- **Zero-Code-Execution Ingestion**: Analyzes Python repositories strictly via Python's standard `ast` compiler. Uploaded code is never executed, imported, or run in Python runtime memory.
- **ZipSlip Defense & Resource Controls**: Validates ZIP entries against path traversal attacks (`../`), enforces file count and byte footprint thresholds, and filters out virtual environments, `.git`, `__pycache__`, and binaries.
- **Persistent Neo4j AuraDB Storage**: Every repository, file, module, class, function, external package, and call edge is stored in real Neo4j AuraDB with parameterized, idempotent Cypher transactions. Zero mock data or simulated responses.
- **Static Call Graph Inference**: Infers same-file local calls, class methods (`self.method()`), imported module calls, and third-party library invocations with explicit confidence tags (`exact` vs `approximate`).
- **Progressive Graph Exploration**: Avoids graph hairballs by loading a clean, bounded module hierarchy by default (`limit=35`). Users can double-click any node to expand its 1-hop connected neighborhood on demand.
- **Evidence Drawer**: Clicking any node opens a slide-out drawer presenting its qualified name, file path, exact 1-based start/end line range, docstrings, parameter signatures, source code slice, and active inbound/outbound references.
- **Full-Text Symbol Search**: Instant keyboard-driven lookup (`Ctrl+K`) for jumping directly to any function, class, or module.
- **Cybersecurity Dark UI**: Aesthetic dark theme built with deep midnight navy (`#06080E`), cyan (`#00F2FE`), violet (`#A855F7`), and emerald (`#10B981`) styling tokens.

---

## 3. Architecture & Technology Stack

```
TraceForge Architecture
┌────────────────────────────────────────────────────────┐
│               React + Vite Frontend                    │
│   (Cytoscape.js, Dagre Layout, Tailwind CSS, Lucide)   │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP REST (JSON)
┌──────────────────────────▼─────────────────────────────┐
│                 FastAPI Backend                        │
│ ┌──────────────────────┐      ┌──────────────────────┐ │
│ │  SecureZipExtractor  │      │  AST Static Engine   │ │
│ │  (ZipSlip Defense)   │      │  (NodeVisitor/Calls) │ │
│ └──────────┬───────────┘      └──────────┬───────────┘ │
│            │                             │             │
│ ┌──────────▼─────────────────────────────▼───────────┐ │
│ │     Ingestion Service (Parameterized UNWIND)        │ │
│ └──────────────────────────┬─────────────────────────┘ │
└────────────────────────────┼───────────────────────────┘
                             │ Bolt + TLS (certifi)
┌────────────────────────────▼───────────────────────────┐
│               Neo4j AuraDB (Cloud)                     │
│    (6 Uniqueness Constraints, Indexes, Cypher Graph)    │
└────────────────────────────────────────────────────────┘
```

- **Backend**: Python 3.11.9, FastAPI 0.111.0, Pydantic v2, Uvicorn, AnyIO.
- **Database Driver**: Official Neo4j Python Driver 5.20.0 with `certifi` CA validation.
- **Frontend**: React 18, Vite 5.4.21, TypeScript 5.2, Tailwind CSS 3.4, Cytoscape.js 3.30 with Dagre layout plugin.
- **Database**: Neo4j AuraDB Cloud (Version 5.27-aura).

---

## 4. Testing & Verification Results

All automated test suites and live database integration checks have been established and verified with concrete output:

### A. Backend Unit & Regression Suite (pytest)
- **Status**: **10 passed, 0 failures**
- `test_ast_extractor_sample_engine`: PASS
- `test_ast_extractor_handles_syntax_error`: PASS
- `test_static_call_resolution_local_and_method`: PASS
- `test_root_endpoint`: PASS
- `test_health_endpoint`: PASS
- `test_upload_requires_zip`: PASS
- `test_upload_requires_name`: PASS
- `test_persist_to_neo4j_uses_batched_unwind`: PASS (Regression test verifying $O(1)$ batched Cypher)
- `test_is_safe_path_valid`: PASS
- `test_is_safe_path_zip_slip`: PASS

### B. Live Neo4j AuraDB API Verification (TestClient)
- **Status**: **28 passed, 0 failures**
- Verified live against Neo4j AuraDB instance (`neo4j+s://a4a9a644.databases.neo4j.io`).
- Tested Health (`/api/v1/health`), Repositories (`/api/v1/repositories`), Graph Overview (`/api/v1/graph/overview`), 1-Hop Expansion (`/api/v1/graph/expand`), Symbol Search (`/api/v1/graph/search`), and Source Evidence (`/api/v1/evidence/{id}`).

### C. Frontend Production Build
- **Status**: **0 TypeScript errors, Exit Code 0**
- Generated assets: `frontend/dist/index.html` (1.24 kB), `dist/assets/index.css` (23.46 kB), `dist/assets/index.js` (738.83 kB).

### D. Large-Repository Ingestion Benchmark (`requests-main`)
- **Status**: **SUCCESS** in **5.77 seconds** (37 files, 37 modules, 78 classes, 618 unique functions, 691 distinct calls).

---

## 5. Known Limitations & Future Improvements

### Known Limitations
1. **Dynamic Dispatch**: Python dynamic features (`getattr(obj, name)()`, `eval()`, runtime monkey patching) cannot be fully resolved statically; these calls are flagged with `"confidence": "approximate"`.
2. **Language Scope**: Currently focused on Python (`.py`). Non-Python source files in polyglot repositories are indexed as files but not parsed into code symbols.
3. **Free Tier DB Capacity**: Very large monorepos (> 100,000 LOC) may require higher memory limits on Neo4j AuraDB Free tier.

### Future Improvements
1. **Multi-Language AST Support**: Incorporate tree-sitter to expand static parsing to TypeScript, JavaScript, Go, and Rust.
2. **Git Diff & Temporal Evolution**: Ingest consecutive commits to visualize architectural drift and identify hot-spot dependency regressions over time.
3. **Automated Impact Analysis**: Calculate blast-radius metrics for proposed function changes prior to deployment.
