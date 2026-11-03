"""
API integration tests against real AuraDB data (no mock data).
Tests: health, repositories list, graph overview, expand, search, evidence.
ASCII-only output for Windows cp1252 compatibility.
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.WARNING)

from fastapi.testclient import TestClient

# Import app after setting pythonpath
from main import app

REPO_ID = "repo_sample_project"
client = TestClient(app, raise_server_exceptions=True)

results = []

def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" | {detail}"
    print(msg)
    results.append((name, condition))
    return condition


print("=== TraceForge API Verification Against Real AuraDB ===")
print(f"  Repo ID: {REPO_ID}")

# --- Test 1: Health Check ---
print("\n[TEST 1] GET /api/v1/health")
r = client.get("/api/v1/health")
check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
data = r.json()
check("status=UP", data.get("status") == "UP", str(data.get("status")))
check("neo4j_connected=true", data.get("neo4j_connected") is True, str(data.get("neo4j_connected")))
check("neo4j_version present", bool(data.get("neo4j_version")), str(data.get("neo4j_version")))

# --- Test 2: List Repositories ---
print("\n[TEST 2] GET /api/v1/repositories")
r = client.get("/api/v1/repositories")
check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
data2 = r.json()
repos = data2.get("repositories", []) if isinstance(data2, dict) else data2
check("repos is list", isinstance(repos, list))
found = next((rp for rp in repos if rp.get("id") == REPO_ID), None)
check("repo_sample_project present", found is not None, f"ids={[rp.get('id') for rp in repos]}")
if found:
    check("total_files=8", found.get("total_files") == 8, str(found.get("total_files")))
    check("total_classes=3", found.get("total_classes") == 3, str(found.get("total_classes")))
    check("total_functions>=14", found.get("total_functions", 0) >= 14, str(found.get("total_functions")))

# --- Test 3: Graph Overview ---
print("\n[TEST 3] GET /api/v1/graph/overview?repo_id=repo_sample_project")
r = client.get(f"/api/v1/graph/overview?repo_id={REPO_ID}")
check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
data = r.json()
nodes = data.get("nodes", [])
edges = data.get("edges", [])
check("nodes non-empty", len(nodes) > 0, f"count={len(nodes)}")
check("edges non-empty", len(edges) > 0, f"count={len(edges)}")
check("truncated field present", "truncated" in data)
check("repository node present", any(n.get("kind") in ("repository", "Repository") for n in nodes),
      f"kinds={list(set(n.get('kind') for n in nodes))}")

# Pick a Function node for expand/evidence tests
func_node = next((n for n in nodes if n.get("kind") in ("function", "Function")), None)
# If not in overview, pick a module
module_node = next((n for n in nodes if n.get("kind") in ("module", "Module")), None)
expand_target = func_node or module_node or (nodes[0] if nodes else None)
expand_id = expand_target["id"] if expand_target else None

# --- Test 4: Expand Node ---
if expand_id:
    print(f"\n[TEST 4] GET /api/v1/graph/expand?node_id={expand_id}")
    r = client.get(f"/api/v1/graph/expand?node_id={expand_id}")
    check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    exp_nodes = data.get("nodes", [])
    check("expanded nodes non-empty", len(exp_nodes) > 0, f"count={len(exp_nodes)}")
    check("target node in expansion", any(n["id"] == expand_id for n in exp_nodes))
else:
    print("\n[TEST 4] BLOCKED - no node_id available from overview")

# --- Test 5: Search ---
print("\n[TEST 5] GET /api/v1/graph/search?q=validate&repo_id=repo_sample_project")
r = client.get(f"/api/v1/graph/search?q=validate&repo_id={REPO_ID}")
check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
data = r.json()
results_list = data.get("results", [])
check("search returns results", len(results_list) > 0, f"count={len(results_list)}")
if results_list:
    first = results_list[0]
    check("result has id", bool(first.get("id")))
    check("result has kind", bool(first.get("kind")))
    check("result has name", bool(first.get("name")))

# --- Test 6: Evidence (pick a Function node by searching for one) ---
print("\n[TEST 6] GET /api/v1/evidence/{node_id}")
# Find a Function node via search for known sample entity
r6 = client.get(f"/api/v1/graph/search?q=ExecutionEngine&repo_id={REPO_ID}")
search_data = r6.json()
func_results = [x for x in search_data.get("results", []) if x.get("kind") in ("function", "class", "Function", "Class")]
if func_results:
    ev_node_id = func_results[0]["id"]
    print(f"  target node: {ev_node_id} ({func_results[0].get('kind')})")
    r = client.get(f"/api/v1/evidence/{ev_node_id}")
    check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
    ev = r.json()
    check("node_id correct", ev.get("node_id") == ev_node_id)
    check("start_line > 0", (ev.get("start_line") or 0) > 0, str(ev.get("start_line")))
    check("file_path present", bool(ev.get("file_path")))
    # code_snippet may be None if source dir not accessible — flag it
    has_snippet = bool(ev.get("code_snippet"))
    check("code_snippet present", has_snippet, "(WARN: source file may not be in data/repos/)" if not has_snippet else "")
else:
    print("  BLOCKED - no function/class found via search")

# --- Summary ---
print("\n=== Summary ===")
total = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
print(f"  PASS: {passed}/{total}")
if failed:
    print(f"  FAIL: {failed}/{total}")
    for name, ok in results:
        if not ok:
            print(f"    - {name}")
