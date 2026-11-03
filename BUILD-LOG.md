# TraceForge — Build Log

This document records the factual, chronological development log for the TraceForge platform across six primary milestones on 3 November 2026.

---

### Entry 1: Project Initialization & Environment Setup
- **Date & Time**: 3 November 2026, 12:45 – 13:00 IST
- **Objectives**: Set up development environment, isolate runtime binaries, and configure security boundaries.
- **Activities**:
  - Located and configured portable runtime tools (`.tools/python/python.exe` 3.11.9 and `.tools/nodejs/` v20.12.2 / npm 10.5.0).
  - Created isolated backend virtual environment at `backend/venv` and installed dependencies: `fastapi==0.111.0`, `uvicorn==0.29.0`, `neo4j==5.20.0`, `pydantic==2.7.1`, `pydantic-settings==2.2.1`, `certifi`, `pytest==8.2.0`, `httpx==0.27.0`.
  - Configured frontend dependencies (144 packages including `react`, `vite`, `typescript`, `tailwindcss`, `cytoscape`, `cytoscape-dagre`, `lucide-react`).
  - Established `.gitignore` enforcing strict exclusion of `.env`, `backend/.env`, `frontend/.env`, `node_modules`, and virtual environments.
  - Provided sanitized `backend/.env.example` template.

---

### Entry 2: Architecture Design & Security Specifications
- **Date & Time**: 3 November 2026, 13:00 – 13:30 IST
- **Objectives**: Formulate system architecture, graph schema, progressive visualization model, and safety constraints.
- **Activities**:
  - Produced comprehensive architecture document (`traceforge_architecture_plan.md`).
  - Defined 6-node graph data model (`Repository`, `File`, `Module`, `Class`, `Function`, `ExternalPackage`) and 4 primary relationship types (`CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`).
  - Enforced strict security model: zero execution of uploaded code (`exec`/`eval`/`import` strictly prohibited; static AST inspection only).
  - Implemented `SecureZipExtractor` in `backend/app/parser/zip_handler.py` with ZipSlip path traversal protection (`is_safe_path`), 25MB archive size limit, 50MB uncompressed footprint limit, and automated directory filtering (`.git`, `venv`, `__pycache__`, `node_modules`).

---

### Entry 3: Python AST Static Extraction & Call Graph Resolution
- **Date & Time**: 3 November 2026, 13:30 – 14:00 IST
- **Objectives**: Build AST parser, repository-wide symbol catalog, and static call inference engine.
- **Activities**:
  - Implemented `backend/app/parser/ast_extractor.py` utilizing Python's standard `ast.NodeVisitor` to extract modules, classes, functions, docstrings, 1-based line numbers, and formatted parameter signatures.
  - Implemented syntax error isolation ensuring malformed Python files report warnings without terminating ingestion.
  - Developed `backend/app/parser/symbol_table.py` managing indexed cross-module symbol resolution and standard library detection.
  - Built `backend/app/parser/call_resolver.py` to statically infer internal local calls, `self.method()` calls, cross-module imported calls, and third-party library invocations with confidence scoring (`"exact"` vs `"approximate"`).
  - Authored automated unit test suites (`test_ast_extractor.py`, `test_call_resolver.py`, `test_security.py`).

---

### Entry 4: Neo4j AuraDB Integration & Live Schema Constraints
- **Date & Time**: 3 November 2026, 14:00 – 14:20 IST
- **Objectives**: Connect backend to Neo4j AuraDB cloud database, handle TLS verification, and enforce unique constraints.
- **Activities**:
  - Implemented `backend/app/database/neo4j_client.py` using official Neo4j Python Driver.
  - Resolved Windows sandbox TLS trust failure by configuring `certifi.where()` CA bundle at module load time without weakening SSL encryption.
  - Executed idempotent schema migrations in `backend/app/database/schema.py`, creating 6 node property uniqueness constraints (`repo_id_unique`, `file_id_unique`, `module_id_unique`, `class_id_unique`, `function_id_unique`, `package_id_unique`) and lookup indexes.
  - Verified live database connectivity to instance `neo4j+s://a4a9a644.databases.neo4j.io` (engine version `5.27-aura`).

---

### Entry 5: Graph UX Visualization & Evidence Drawer
- **Date & Time**: 3 November 2026, 14:20 – 14:40 IST
- **Objectives**: Develop interactive frontend interface adhering to cybersecurity dark visual identity and progressive graph rendering.
- **Activities**:
  - Built `frontend/src/components/graph/GraphCanvas.tsx` using Cytoscape.js with `cytoscape-dagre` hierarchical layout and concentric fallback.
  - Enforced anti-hairball design: default view requests bounded overview (`limit=35`), while double-clicking any node progressively expands its 1-hop connected neighborhood.
  - Implemented `EvidenceDrawer.tsx` retrieving exact source slices, line ranges, signatures, and inbound/outbound references via `/api/v1/evidence/{id}`.
  - Built `Sidebar.tsx` with live telemetry metrics and kind/relationship filter toggles.
  - Implemented `SearchBar.tsx` with `Ctrl+K` shortcut for symbol lookup.
  - Completed production frontend build (`tsc && vite build`) outputting compiled assets to `frontend/dist/`.

---

### Entry 6: Real Repository Ingestion & High-Performance Batching
- **Date & Time**: 3 November 2026, 14:40 – 16:25 IST
- **Objectives**: Verify real end-to-end repository ingestion, eliminate scale bottlenecks, and ensure data consistency.
- **Activities**:
  - Verified live ingestion of `sample_repo.zip` into Neo4j AuraDB with idempotent re-ingestion.
  - Diagnosed Uvicorn auto-reload interruption: disabled file watching on `data/repos/` during extraction.
  - Ingested large repository `requests-main` (37 files). Identified bottleneck where ~1,450 unbatched individual network queries over TLS caused execution hangs.
  - Re-architected `_persist_to_neo4j` to use parameterized Cypher `UNWIND $batch AS item` batching and indexed label lookups, offloading database I/O to a worker thread. Ingestion time dropped to **5.77 seconds**.
  - Reconciled typing `@overload` function reporting and fixed class constructor call resolution (`class:` vs `func:` ID prefix).
  - Executed automated test suite: all 10 pytest tests passed, and all 28 live API integration assertions passed against Neo4j AuraDB.
