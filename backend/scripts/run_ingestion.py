"""
Standalone ingestion verification script for TraceForge.
Runs the full ingestion pipeline against AuraDB with the sample repo ZIP.
Does NOT execute any uploaded code — AST only.
"""
import asyncio
import sys
import logging
from io import BytesIO
from pathlib import Path

# Ensure backend package is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(name)s | %(levelname)s | %(message)s")

from starlette.datastructures import UploadFile
from app.database.schema import init_schema
from app.services.ingestion_service import ingestion_service
from app.database.neo4j_client import neo4j_client
from app.config import settings


def run_count_queries(label: str = "repo_sample_project") -> None:
    """Run read-only count queries to verify Neo4j state. No data modification."""
    print("\n--- Neo4j Read-Only Verification Queries ---")
    db = settings.NEO4J_DATABASE
    repo_id = label

    queries = {
        "Repository":      "MATCH (n:Repository {id: $rid}) RETURN count(n) AS cnt",
        "File":            "MATCH (n:File {repo_id: $rid}) RETURN count(n) AS cnt",
        "Module":          "MATCH (n:Module {repo_id: $rid}) RETURN count(n) AS cnt",
        "Class":           "MATCH (n:Class {repo_id: $rid}) RETURN count(n) AS cnt",
        "Function":        "MATCH (n:Function {repo_id: $rid}) RETURN count(n) AS cnt",
        "ExternalPackage": "MATCH (n:ExternalPackage) RETURN count(n) AS cnt",
        "CONTAINS rels":   "MATCH (a {repo_id: $rid})-[r:CONTAINS]->(b) RETURN count(r) AS cnt",
        "DEFINES rels":    "MATCH (a {repo_id: $rid})-[r:DEFINES]->(b) RETURN count(r) AS cnt",
        "IMPORTS rels":    "MATCH (a:File {repo_id: $rid})-[r:IMPORTS]->(b) RETURN count(r) AS cnt",
        "CALLS rels":      "MATCH (a:Function {repo_id: $rid})-[r:CALLS]->(b) RETURN count(r) AS cnt",
    }

    driver = neo4j_client.get_driver()
    with driver.session(database=db) as session:
        for label_name, cypher in queries.items():
            try:
                result = session.run(cypher, {"rid": repo_id})
                rec = result.single()
                cnt = rec["cnt"] if rec else 0
                status = "OK" if cnt > 0 else "ZERO"
                print(f"  [{status}] {label_name:20s}: {cnt}")
            except Exception as e:
                print(f"  [ERR] {label_name:20s}: ERROR - {type(e).__name__}: {e}")

    # Also get repo CONTAINS File rels (Repo node uses id not repo_id)
    with driver.session(database=db) as session:
        try:
            result = session.run(
                "MATCH (r:Repository {id: $rid})-[rel:CONTAINS]->(f:File) RETURN count(rel) AS cnt",
                {"rid": repo_id}
            )
            rec = result.single()
            cnt = rec["cnt"] if rec else 0
            print(f"  [{'OK' if cnt > 0 else 'ZERO'}] {'Repo->File CONTAINS':20s}: {cnt}")
        except Exception as e:
            print(f"  [ERR] {'Repo->File CONTAINS':20s}: ERROR - {e}")


async def main():
    repo_name = "sample_project"
    repo_id = f"repo_{repo_name}"

    zip_path = Path(__file__).resolve().parent.parent.parent / "sample_repo" / "sample_repo.zip"
    if not zip_path.exists():
        print(f"FAIL: sample ZIP not found at {zip_path}")
        sys.exit(1)

    print(f"[CHECK] ZIP exists: {zip_path} ({zip_path.stat().st_size} bytes)")

    # Init schema (idempotent)
    print("\n[STEP 1] Initializing schema constraints (idempotent)...")
    try:
        init_schema()
        print("  PASS: Schema init completed")
    except Exception as e:
        print(f"  FAIL: Schema init error — {e}")
        sys.exit(1)

    # Run first ingestion
    print(f"\n[STEP 2] Running ingestion (first pass) for repo '{repo_name}'...")
    zip_bytes = zip_path.read_bytes()
    upload_file = UploadFile(filename="sample_repo.zip", file=BytesIO(zip_bytes))
    try:
        result = await ingestion_service.ingest_repository(upload_file, repo_name)
        print(f"  status:          {result.status}")
        print(f"  repo_id:         {result.repo_id}")
        print(f"  files_parsed:    {result.files_parsed}")
        print(f"  modules_found:   {result.modules_found}")
        print(f"  classes_found:   {result.classes_found}")
        print(f"  functions_found: {result.functions_found}")
        print(f"  calls_inferred:  {result.calls_inferred}")
        if result.warnings:
            for w in result.warnings:
                print(f"  WARNING: {w}")
        if result.status == "SUCCESS":
            print("  PASS: First ingestion succeeded")
        else:
            print("  FAIL: Ingestion returned non-SUCCESS status")
            sys.exit(1)
    except Exception as e:
        print(f"  FAIL: Ingestion raised exception — {type(e).__name__}: {e}")
        sys.exit(1)

    # Read-only verification after first ingestion
    print("\n[STEP 3] Verifying node/relationship counts after first ingestion...")
    run_count_queries(repo_id)

    # Run second ingestion (idempotency check)
    print(f"\n[STEP 4] Running ingestion (second pass — idempotency check)...")
    zip_bytes2 = zip_path.read_bytes()
    upload_file2 = UploadFile(filename="sample_repo.zip", file=BytesIO(zip_bytes2))
    try:
        result2 = await ingestion_service.ingest_repository(upload_file2, repo_name)
        print(f"  status:          {result2.status}")
        print(f"  files_parsed:    {result2.files_parsed}")
        print(f"  PASS: Second ingestion completed")
    except Exception as e:
        print(f"  FAIL: Second ingestion raised exception — {type(e).__name__}: {e}")

    # Idempotency: verify no duplicate Repository nodes
    print("\n[STEP 5] Idempotency check — no duplicate nodes expected...")
    run_count_queries(repo_id)

    driver = neo4j_client.get_driver()
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        repo_count = session.run(
            "MATCH (n:Repository {id: $rid}) RETURN count(n) AS cnt", {"rid": repo_id}
        ).single()["cnt"]
        if repo_count == 1:
            print(f"\n  PASS: Exactly 1 Repository node found (no duplicates)")
        else:
            print(f"\n  FAIL: Found {repo_count} Repository nodes — MERGE not working correctly")

    print("\n[DONE] Ingestion verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
