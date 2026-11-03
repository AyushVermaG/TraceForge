# TraceForge — Evidence-First Codebase Intelligence

**TraceForge** is a premium, evidence-first codebase intelligence platform powered by a real **Neo4j** graph database, **Python AST** static analysis, and an interactive **React + Cytoscape.js** visualization interface.

Developers upload a Python repository ZIP. TraceForge validates and unpacks it securely, extracts files, modules, classes, functions, imports, and statically inferable function calls, persists the topology directly into **Neo4j AuraDB**, and allows developers to progressively explore dependency networks and inspect exact source evidence with line-level accuracy.

---

## Problem Statement

Understanding real-world Python codebases is challenging:
1. **Mental Model Fragmentation**: Reading code file-by-file obscures architectural dependencies, caller/callee relationships, and third-party library boundaries.
2. **Graph Hairball Traps**: Naive code visualization tools dump thousands of nodes onto a canvas, resulting in an unreadable "tangled hairball" that crashes browsers and obscures insights.
3. **Black-Box Summaries**: Modern AI assistants and static tools often generate summaries without citing exact source lines or verifiable structural relationships.
4. **Execution Security Risks**: Many dependency analyzers require executing repository code (`setup.py`, dynamic imports), exposing systems to malicious code execution.

**TraceForge solves this** by providing zero-code-execution AST parsing, persistent storage in a genuine Neo4j graph database, progressive bounded graph expansion, and an Evidence Drawer that provides line-level source code validation for every node and relationship.

---

## Technology Stack

### Backend
- **Language & Runtime**: Python 3.11.9
- **Web Framework**: FastAPI 0.111.0 (Starlette, Pydantic v2, AnyIO, Uvicorn)
- **Static Analysis Engine**: Python Standard Library `ast` (zero runtime code execution)
- **Database Driver**: Official `neo4j` Python Driver 5.20.0 with `certifi` CA verification
- **Testing**: `pytest` 8.2.0, `httpx` 0.27.0 TestClient

### Frontend
- **Framework & Tooling**: React 18, Vite 5.4, TypeScript 5.2
- **Styling**: Tailwind CSS 3.4 (Cybersecurity Dark aesthetic)
- **Graph Visualization**: Cytoscape.js 3.30 with `cytoscape-dagre` hierarchical layout
- **Icons**: Lucide React 0.378

### Database
- **Graph Database**: Neo4j AuraDB (Cloud Instance, Engine Version 5.27-aura)
- **Data Model**: 6 Node Labels (`Repository`, `File`, `Module`, `Class`, `Function`, `ExternalPackage`) & 4 Relationship Types (`CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`)

---

## Key Capabilities & Architecture

- **Real Neo4j Database Persistence**: Zero mock data or simulated graphs. Every node and relationship is stored and queried via parameterized Cypher transactions with idempotent `MERGE` constraints.
- **Python AST Static Analysis**: Parses Python code safely using the standard `ast` module. Does **not** execute uploaded repository code (`exec`/`eval`/`import`). Gracefully isolates and reports syntax errors without halting ingestion.
- **Static Call Graph Inference**: Identifies statically inferable calls:
  - Local functions within the same file.
  - Class method calls via `self.method()`.
  - Cross-module calls via explicit imports (`from x.y import fn` or `mod.fn()`).
  - Calls with dynamic dispatch or unresolved targets are documented with confidence indicators (`"exact"` vs `"approximate"`).
- **Progressive Graph UX**: Never loads an unreadable hairball graph. Starts with a high-level module hierarchy, supporting 1-hop progressive expansion, neighborhood isolation, and full-text symbol search.
- **Evidence Inspector Drawer**: Inspect any node to view its qualified name, file location, line range (e.g. `L12 - L48`), docstring, parameter signature, and exact source code slice alongside caller and callee links.
- **Cybersecurity Dark Visual Identity**: Designed for technical professionals with deep midnight navy backgrounds (`#06080E`), electric cyan accents (`#00F2FE`), violet definition lines (`#A855F7`), emerald invocation paths (`#10B981`), and subtle glow micro-interactions.

---

## Graph Data Model & Schema

### Node Classifications
| Node Label | ID Format | Key Properties |
| :--- | :--- | :--- |
| **`Repository`** | `repo:{timestamp}_{name}` | `name`, `ingested_at`, `total_files` |
| **`File`** | `file:{repo_id}:{relative_path}` | `path`, `line_count`, `repo_id` |
| **`Module`** | `module:{repo_id}:{dot_path}` | `name`, `docstring`, `repo_id` |
| **`Class`** | `class:{repo_id}:{path}:{name}` | `name`, `qualname`, `start_line`, `end_line`, `docstring`, `bases` |
| **`Function`** | `func:{repo_id}:{path}:{qualname}` | `name`, `qualname`, `start_line`, `end_line`, `signature`, `docstring`, `is_async`, `is_method` |
| **`ExternalPackage`** | `pkg:{name}` | `name`, `is_stdlib` |

### Relationships
- **`(:Repository)-[:CONTAINS]->(:File)`**
- **`(:File)-[:CONTAINS]->(:Module)`**
- **`(:Module)-[:DEFINES]->(:Class|:Function)`**
- **`(:Class)-[:DEFINES]->(:Function)`**
- **`(:File)-[:IMPORTS]->(:Module|:ExternalPackage)`**
- **`(:Function)-[:CALLS {line_no, confidence, call_expr}]->(:Function|:ExternalPackage)`**

---

## Directory Structure

```
TraceForge/
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   ├── neo4j_client.py    # Official Neo4j Python Driver wrapper
│   │   │   └── schema.py          # Unique constraints and index migrations
│   │   ├── models/
│   │   │   ├── graph_models.py    # Node, Edge, Evidence Pydantic schemas
│   │   │   └── api_models.py      # Upload and Search schemas
│   │   ├── parser/
│   │   │   ├── zip_handler.py     # ZipSlip defense and file exclusions
│   │   │   ├── ast_extractor.py   # Python AST visitor and entity extraction
│   │   │   ├── call_resolver.py   # Static call inference engine
│   │   │   └── symbol_table.py    # Repository-wide symbol catalog
│   │   ├── services/
│   │   │   ├── ingestion_service.py # Ingestion pipeline orchestrator
│   │   │   ├── graph_service.py   # Progressive Cypher query builder
│   │   │   └── evidence_service.py# Source code slice retriever
│   │   ├── routers/
│   │   │   ├── health.py          # API and Neo4j health check
│   │   │   ├── repositories.py    # Repository management & deletion
│   │   │   ├── upload.py          # ZIP upload endpoint
│   │   │   ├── graph.py           # Overview, expand, and search
│   │   │   └── evidence.py        # Code snippet endpoint
│   │   └── config.py              # Pydantic Settings configuration
│   ├── tests/
│   │   ├── test_ast_extractor.py  # AST extraction unit tests
│   │   ├── test_call_resolver.py  # Call resolution accuracy tests
│   │   ├── test_security.py       # ZipSlip defense tests
│   │   └── test_graph_api.py      # API integration tests
│   ├── .env.example
│   ├── requirements.txt
│   └── main.py                    # FastAPI server entrypoint
│
├── frontend/
│   ├── src/
│   │   ├── api/client.ts          # Typed REST API client
│   │   ├── components/
│   │   │   ├── layout/            # Navbar, Sidebar
│   │   │   ├── graph/             # GraphCanvas (Cytoscape), GraphControls, SearchBar
│   │   │   ├── evidence/          # EvidenceDrawer, CodeViewer
│   │   │   └── upload/            # UploadModal with drag-and-drop
│   │   ├── types/graph.ts         # TypeScript definitions
│   │   ├── App.tsx                # Master orchestration
│   │   ├── main.tsx
│   │   └── index.css              # Cybersecurity styling tokens
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── sample_repo/
│   ├── sample_project/            # Realistic enterprise Python codebase
│   │   ├── core/                  # engine.py, validator.py
│   │   ├── services/              # auth_service.py, analytics.py
│   │   └── main.py
│   ├── requirements.txt
│   └── sample_repo.zip            # Pre-packaged demonstration archive
│
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **Node.js 18+** & npm
- A **Neo4j** instance:
  - Free cloud instance on [Neo4j AuraDB](https://neo4j.com/cloud/platform/aura-graph-database/)
  - Or local Neo4j via Docker: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:latest`

### 2. Configure Backend Credentials
Create `backend/.env` based on `backend/.env.example`:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```ini
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-secure-password>
NEO4J_DATABASE=neo4j

HOST=127.0.0.1
PORT=8000
ENVIRONMENT=development
STORAGE_DIR=./data/repos
MAX_UPLOAD_SIZE_MB=25
```

### 3. Run Backend Server
```bash
# Activate virtual environment
backend\venv\Scripts\activate   # Windows
# or: source backend/venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Start backend API (production / stable ingestion mode: auto-reload disabled)
python backend/main.py
```
Backend API will be accessible at `http://127.0.0.1:8000`. Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Run Frontend Application
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. (The backend also automatically serves the compiled production frontend at `http://127.0.0.1:8000/`).

---

## Running the Automated Test Suite

TraceForge includes automated unit and integration tests covering AST parsing, static call inference, path traversal security, and API endpoints:

```bash
# Run all backend tests
backend\venv\Scripts\pytest.exe backend/tests -v
```

---

## Demonstrating with Sample Repository

A multi-tiered safe Python repository is included in `sample_repo/sample_repo.zip`.

1. Open the TraceForge dashboard at `http://localhost:5173`.
2. Click **Ingest Repo ZIP**.
3. Drag and drop `sample_repo/sample_repo.zip` or select it from your file browser.
4. Name the repository `sample_project` and click **Begin Ingestion & Analysis**.
5. TraceForge parses the files, builds the symbol catalog, resolves internal/imported/method calls, and persists the graph into Neo4j.
6. The interactive Cytoscape canvas renders the module overview.
7. **Single-click** any class or function to slide open the **Evidence Drawer** showing exact code slices and line numbers.
8. **Double-click** any node to progressively expand its connected callers and callees.
9. Press `Ctrl+K` to search symbols by name with autocomplete.

---

## Security Model

- **Zero Remote Code Execution**: TraceForge analyzes Python source code strictly using Python's AST compiler. Uploaded files are never executed, imported, or run in Python runtime memory.
- **ZipSlip Defense**: All ZIP entries are verified against canonical resolved base paths before extraction. Traversal sequences (`../`) are strictly blocked.
- **Resource Limits**: Configurable max upload size (default 25MB), max uncompressed footprint (default 50MB), and maximum file count (default 1,000 files) protect against zip bombs.
- **Folder Exclusion**: Automated filtering ignores `.git`, `.venv`, `__pycache__`, `node_modules`, and test caches.
- **Credential Protection**: Neo4j credentials reside exclusively in server-side environment variables and are never returned in client responses or exposed in logs.

---

## Screenshots & UI Walkthrough

```
+---------------------------------------------------------------------------------------------------+
|  [⚡ TRACEFORGE]   Repo: [requests-main v]   Search: [Ctrl+K Find symbol...]   AuraDB: [ONLINE ●] |
+------------------+-------------------------------------------------------------+------------------+
| TELEMETRY        | GRAPH VIEWPORT (Cytoscape.js Hierarchical Dagre)            | EVIDENCE DRAWER  |
|                  |                                                             |                  |
| Files:        37 |                     [requests-main]                         | Session.request  |
| Modules:      37 |                            | (CONTAINS)                     | qualname:        |
| Classes:      78 |           +----------------+----------------+               | Session.request  |
| Functions:   618 |           |                                 |               |                  |
| Calls:       691 |       [models.py]                      [sessions.py]        | File:            |
|                  |           | (DEFINES)                       | (DEFINES)     | src/requests/    |
| FILTERS          |      [Request]                          [Session]           | sessions.py:480  |
| [x] Repository   |           |                                 | (CALLS)       |                  |
| [x] Module       |           +---------------------------------+               | Code Slice:      |
| [x] Class        |                                                             | def request(self,|
| [x] Function     |  [Zoom In] [Zoom Out] [Fit Screen] [Concentric / Dagre]     |   method, url...)|
| [x] Package      |                                                             |                  |
+------------------+-------------------------------------------------------------+------------------+
```

### Visual Highlights
1. **Interactive Cytoscape Canvas**: High-performance DAG layout with distinct iconography and colors for each entity kind (Cyan: Repository, Sky: Module, Slate: File, Violet: Class, Emerald: Function, Amber: Package).
2. **Slide-Out Evidence Drawer**: Click any node to inspect its exact source code slice, start/end line range, parameter signature, docstring, and active callers/callees.
3. **Neighborhood Expansion**: Double-click any node to dynamically expand its 1-hop connected neighborhood without reloading the graph.
4. **Instant Symbol Search**: Instant search dialog (`Ctrl+K`) for quickly jumping to classes, functions, and modules.

---

## Known Limitations

1. **Static Inference Boundaries**: Dynamic runtime dispatch (e.g. `getattr(obj, dynamic_str)()`, `eval()`, or indirect callbacks) cannot be resolved statically and is flagged with `"confidence": "approximate"`.
2. **Language Scope**: Currently restricted to Python (`.py`) files; multi-language polyglot repositories are parsed only for their Python components.
3. **Free AuraDB Resource Limits**: Very large monorepos (> 100,000 LOC) may hit Neo4j AuraDB Free tier transaction memory limits if not ingested in small batches.
