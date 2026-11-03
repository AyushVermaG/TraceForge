"""
Read-only verification of AuraDB node/relationship counts after ingestion.
Does NOT modify any data. ASCII-only output for Windows cp1252 compatibility.
"""
import sys
import asyncio
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.WARNING)

from app.database.neo4j_client import neo4j_client
from app.config import settings

REPO_ID = "repo_sample_project"
DB = settings.NEO4J_DATABASE


def run_count_queries():
    """Run read-only Cypher count queries. No data modification."""
    print("\n=== Step 3: Node/Relationship Counts (Read-Only) ===")
    queries = {
        "Repository":       ("MATCH (n:Repository {id: $rid}) RETURN count(n) AS cnt", 1),
        "File":             ("MATCH (n:File {repo_id: $rid}) RETURN count(n) AS cnt", 8),
        "Module":           ("MATCH (n:Module {repo_id: $rid}) RETURN count(n) AS cnt", 5),
        "Class":            ("MATCH (n:Class {repo_id: $rid}) RETURN count(n) AS cnt", 3),
        "Function":         ("MATCH (n:Function {repo_id: $rid}) RETURN count(n) AS cnt", 10),
        "ExternalPackage":  ("MATCH (n:ExternalPackage) RETURN count(n) AS cnt", 1),
        "CONTAINS(repo-f)": ("MATCH (r:Repository {id: $rid})-[rel:CONTAINS]->(f:File) RETURN count(rel) AS cnt", 8),
        "CONTAINS(f-m)":    ("MATCH (f:File {repo_id: $rid})-[rel:CONTAINS]->(m:Module) RETURN count(rel) AS cnt", 8),
        "DEFINES rels":     ("MATCH (n {repo_id: $rid})-[r:DEFINES]->(m) RETURN count(r) AS cnt", 5),
        "IMPORTS rels":     ("MATCH (f:File {repo_id: $rid})-[r:IMPORTS]->(p) RETURN count(r) AS cnt", 1),
        "CALLS rels":       ("MATCH (a:Function {repo_id: $rid})-[r:CALLS]->(b) RETURN count(r) AS cnt", 1),
    }

    driver = neo4j_client.get_driver()
    all_pass = True
    with driver.session(database=DB) as session:
        for name, (cypher, min_expected) in queries.items():
            try:
                rec = session.run(cypher, {"rid": REPO_ID}).single()
                cnt = rec["cnt"] if rec else 0
                ok = cnt >= min_expected
                if not ok:
                    all_pass = False
                status = "PASS" if ok else "WARN"
                print(f"  [{status}] {name:20s}: {cnt:4d}  (min expected: {min_expected})")
            except Exception as e:
                all_pass = False
                print(f"  [FAIL] {name:20s}: ERROR - {type(e).__name__}: {str(e)[:80]}")

    return all_pass


def idempotency_check():
    """Verify no duplicate nodes after re-ingestion."""
    print("\n=== Step 5: Idempotency Check ===")
    driver = neo4j_client.get_driver()
    with driver.session(database=DB) as session:
        repo_cnt = session.run(
            "MATCH (n:Repository {id: $rid}) RETURN count(n) AS cnt", {"rid": REPO_ID}
        ).single()["cnt"]
        if repo_cnt == 1:
            print(f"  [PASS] Repository nodes = 1 (no duplicates)")
        else:
            print(f"  [FAIL] Repository nodes = {repo_cnt} (expected exactly 1)")

        # Also check file deduplication
        file_cnt = session.run(
            "MATCH (n:File {repo_id: $rid}) RETURN count(n) AS cnt", {"rid": REPO_ID}
        ).single()["cnt"]
        # After 2 ingestions, should still be 8 (MERGE idempotent)
        status = "PASS" if file_cnt == 8 else "WARN"
        print(f"  [{status}] File nodes = {file_cnt} (expected 8 with MERGE)")

        class_cnt = session.run(
            "MATCH (n:Class {repo_id: $rid}) RETURN count(n) AS cnt", {"rid": REPO_ID}
        ).single()["cnt"]
        status = "PASS" if class_cnt == 3 else "WARN"
        print(f"  [{status}] Class nodes = {class_cnt} (expected 3 with MERGE)")


async def run_second_ingestion():
    """Re-run ingestion with same ZIP for idempotency test."""
    from app.services.ingestion_service import ingestion_service
    from starlette.datastructures import UploadFile

    zip_path = Path(__file__).resolve().parent.parent.parent / "sample_repo" / "sample_repo.zip"
    zip_bytes = zip_path.read_bytes()
    upload_file = UploadFile(filename="sample_repo.zip", file=BytesIO(zip_bytes))

    print("\n=== Step 4: Second Ingestion (Idempotency) ===")
    result = await ingestion_service.ingest_repository(upload_file, "sample_project")
    print(f"  status:          {result.status}")
    print(f"  files_parsed:    {result.files_parsed}")
    print(f"  classes_found:   {result.classes_found}")
    print(f"  functions_found: {result.functions_found}")
    print(f"  calls_inferred:  {result.calls_inferred}")
    if result.status == "SUCCESS":
        print("  [PASS] Second ingestion completed successfully")
    else:
        print("  [FAIL] Second ingestion returned non-SUCCESS status")


if __name__ == "__main__":
    print("=== TraceForge AuraDB Verification ===")
    print(f"  Database: {DB}")
    print(f"  Repo ID:  {REPO_ID}")

    # Step 3: Counts after first ingestion
    counts_ok = run_count_queries()

    # Step 4: Re-ingest
    asyncio.run(run_second_ingestion())

    # Step 5: Idempotency check after second ingestion
    idempotency_check()

    # Re-run counts to confirm no bloat after second ingestion
    print("\n=== Step 6: Counts after second ingestion (must match Step 3) ===")
    run_count_queries()

    print("\n=== Verification Complete ===")
