"""Ingestion service coordinating parsing and Neo4j graph persistence."""
import asyncio
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile
from app.config import settings
from app.database.neo4j_client import neo4j_client
from app.parser.zip_handler import SecureZipExtractor
from app.parser.ast_extractor import parse_python_file, ParsedFileResult
from app.parser.symbol_table import SymbolCatalog, SymbolDef, ImportDef
from app.parser.call_resolver import StaticCallResolver, ResolvedCallEdge
from app.models.api_models import UploadResponse

logger = logging.getLogger("TraceForge.IngestionService")

class IngestionService:
    """End-to-end ingestion pipeline from ZIP to Neo4j graph nodes & edges."""

    async def ingest_repository(self, upload_file: UploadFile, repo_name: str) -> UploadResponse:
        clean_name = repo_name.strip().replace(" ", "_").lower()
        repo_id = f"repo_{clean_name}"
        zip_extractor = SecureZipExtractor(repo_id=repo_id)

        # 1. Extract ZIP securely
        source_dir, warnings = await zip_extractor.extract_upload(upload_file)
        python_files = zip_extractor.list_python_files()

        logger.info(f"Ingesting repo '{repo_name}' ({repo_id}) with {len(python_files)} python files")

        catalog = SymbolCatalog(repo_id=repo_id)
        parsed_results: List[ParsedFileResult] = []

        # 2. Parse all Python files into AST and populate SymbolCatalog
        for py_file in python_files:
            parsed = parse_python_file(file_path=py_file, root_dir=source_dir)
            parsed_results.append(parsed)

            if parsed.syntax_error:
                warnings.append(f"{parsed.relative_path}: {parsed.syntax_error}")
                continue

            catalog.register_module(parsed.module_dot_path, parsed.relative_path)

            for imp in parsed.imports:
                catalog.register_import(parsed.relative_path, ImportDef(
                    module=imp.module,
                    name=imp.name,
                    alias=imp.alias,
                    line_no=imp.line_no,
                    is_from=imp.is_from
                ))

            for cls in parsed.classes:
                catalog.register_symbol(SymbolDef(
                    repo_id=repo_id,
                    file_path=parsed.relative_path,
                    module_path=parsed.module_dot_path,
                    qualname=cls.qualname,
                    kind="Class",
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    docstring=cls.docstring,
                    bases=cls.bases
                ))
                for method in cls.methods:
                    catalog.register_symbol(SymbolDef(
                        repo_id=repo_id,
                        file_path=parsed.relative_path,
                        module_path=parsed.module_dot_path,
                        qualname=method.qualname,
                        kind="Function",
                        parent_class=cls.name,
                        start_line=method.start_line,
                        end_line=method.end_line,
                        signature=method.signature,
                        docstring=method.docstring,
                        is_async=method.is_async,
                        is_method=True
                    ))

            for fn in parsed.functions:
                catalog.register_symbol(SymbolDef(
                    repo_id=repo_id,
                    file_path=parsed.relative_path,
                    module_path=parsed.module_dot_path,
                    qualname=fn.qualname,
                    kind="Function",
                    start_line=fn.start_line,
                    end_line=fn.end_line,
                    signature=fn.signature,
                    docstring=fn.docstring,
                    is_async=fn.is_async,
                    is_method=False
                ))

        # 3. Resolve static calls
        call_resolver = StaticCallResolver(repo_id=repo_id, catalog=catalog)
        all_resolved_calls: List[ResolvedCallEdge] = []
        for parsed in parsed_results:
            if not parsed.syntax_error:
                calls = call_resolver.resolve_file_calls(parsed)
                all_resolved_calls.extend(calls)

        # 4. Check Neo4j health and persist graph
        health = neo4j_client.ping()
        if not health["connected"]:
            logger.error(f"Cannot persist graph: {health['error']}")
            raise ConnectionError(f"Neo4j database connection unavailable: {health['error']}")

        await asyncio.to_thread(
            self._persist_to_neo4j,
            repo_id=repo_id,
            repo_name=repo_name,
            parsed_results=parsed_results,
            catalog=catalog,
            resolved_calls=all_resolved_calls
        )

        # Count extracted statistics (distinct graph entities persisted to Neo4j)
        total_classes = sum(len(p.classes) for p in parsed_results)

        distinct_function_ids = set()
        for p in parsed_results:
            if p.syntax_error:
                continue
            for fn in p.functions:
                distinct_function_ids.add(f"func:{repo_id}:{p.relative_path}:{fn.qualname}")
            for c in p.classes:
                for m in c.methods:
                    distinct_function_ids.add(f"func:{repo_id}:{p.relative_path}:{m.qualname}")

        distinct_call_keys = {(c.source_id, c.target_id, c.line_no) for c in all_resolved_calls}

        return UploadResponse(
            repo_id=repo_id,
            name=repo_name,
            status="SUCCESS",
            files_parsed=len(python_files),
            modules_found=len(catalog.module_to_file),
            classes_found=total_classes,
            functions_found=len(distinct_function_ids),
            calls_inferred=len(distinct_call_keys),
            warnings=warnings
        )

    def _persist_to_neo4j(
        self,
        repo_id: str,
        repo_name: str,
        parsed_results: List[ParsedFileResult],
        catalog: SymbolCatalog,
        resolved_calls: List[ResolvedCallEdge]
    ):
        """Persist graph entities into Neo4j via high-performance parameterized batched Cypher."""
        driver = neo4j_client.get_driver()

        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # 1. Upsert Repository
            session.run("""
                MERGE (r:Repository {id: $repo_id})
                ON CREATE SET r.name = $repo_name, r.ingested_at = datetime(), r.total_files = $total_files
                ON MATCH SET r.name = $repo_name, r.last_updated = datetime(), r.total_files = $total_files
            """, {"repo_id": repo_id, "repo_name": repo_name, "total_files": len(parsed_results)})

            # 2. Upsert External Packages in batch
            if catalog.external_packages:
                pkgs_batch = [{"pkg_id": f"pkg:{pkg}", "pkg_name": pkg} for pkg in catalog.external_packages]
                session.run("""
                    UNWIND $batch AS item
                    MERGE (p:ExternalPackage {id: item.pkg_id})
                    ON CREATE SET p.name = item.pkg_name, p.is_stdlib = false
                """, {"batch": pkgs_batch})

            # 3. Upsert Files in batch
            files_batch = [{
                "file_id": f"file:{repo_id}:{parsed.relative_path}",
                "rel_path": parsed.relative_path,
                "line_count": parsed.line_count
            } for parsed in parsed_results]

            if files_batch:
                session.run("""
                    MATCH (r:Repository {id: $repo_id})
                    UNWIND $batch AS item
                    MERGE (f:File {id: item.file_id})
                    ON CREATE SET f.repo_id = $repo_id, f.path = item.rel_path, f.line_count = item.line_count
                    ON MATCH SET f.line_count = item.line_count
                    MERGE (r)-[:CONTAINS]->(f)
                """, {"repo_id": repo_id, "batch": files_batch})

            # 4. Upsert Modules in batch
            modules_batch = [{
                "file_id": f"file:{repo_id}:{parsed.relative_path}",
                "module_id": f"module:{repo_id}:{parsed.module_dot_path}",
                "mod_name": parsed.module_dot_path,
                "docstring": parsed.docstring or ""
            } for parsed in parsed_results if not parsed.syntax_error]

            if modules_batch:
                session.run("""
                    UNWIND $batch AS item
                    MATCH (f:File {id: item.file_id})
                    MERGE (m:Module {id: item.module_id})
                    ON CREATE SET m.repo_id = $repo_id, m.name = item.mod_name, m.docstring = item.docstring
                    ON MATCH SET m.docstring = item.docstring
                    MERGE (f)-[:CONTAINS]->(m)
                """, {"repo_id": repo_id, "batch": modules_batch})

            # 5. Upsert Imports in batch
            imports_batch = []
            for parsed in parsed_results:
                if parsed.syntax_error:
                    continue
                f_id = f"file:{repo_id}:{parsed.relative_path}"
                for imp in parsed.imports:
                    target_pkg = imp.module.split(".")[0]
                    imports_batch.append({
                        "file_id": f_id,
                        "target_pkg_id": f"pkg:{target_pkg}",
                        "pkg_name": target_pkg,
                        "line_no": imp.line_no,
                        "full_mod": imp.module,
                        "alias": imp.alias or ""
                    })

            if imports_batch:
                session.run("""
                    UNWIND $batch AS item
                    MATCH (f:File {id: item.file_id})
                    MERGE (p:ExternalPackage {id: item.target_pkg_id})
                    ON CREATE SET p.name = item.pkg_name, p.is_stdlib = false
                    MERGE (f)-[rel:IMPORTS {line_no: item.line_no}]->(p)
                    ON CREATE SET rel.module = item.full_mod, rel.alias = item.alias
                """, {"batch": imports_batch})

            # 6. Upsert Classes & Methods in batch
            classes_batch = []
            methods_batch = []
            for parsed in parsed_results:
                if parsed.syntax_error:
                    continue
                module_id = f"module:{repo_id}:{parsed.module_dot_path}"
                for cls in parsed.classes:
                    class_id = f"class:{repo_id}:{parsed.relative_path}:{cls.qualname}"
                    classes_batch.append({
                        "module_id": module_id,
                        "class_id": class_id,
                        "name": cls.name,
                        "qualname": cls.qualname,
                        "rel_path": parsed.relative_path,
                        "start_line": cls.start_line,
                        "end_line": cls.end_line,
                        "docstring": cls.docstring or "",
                        "bases": cls.bases
                    })
                    for method in cls.methods:
                        method_id = f"func:{repo_id}:{parsed.relative_path}:{method.qualname}"
                        methods_batch.append({
                            "class_id": class_id,
                            "method_id": method_id,
                            "name": method.name,
                            "qualname": method.qualname,
                            "rel_path": parsed.relative_path,
                            "start_line": method.start_line,
                            "end_line": method.end_line,
                            "signature": method.signature,
                            "docstring": method.docstring or "",
                            "is_async": method.is_async
                        })

            if classes_batch:
                session.run("""
                    UNWIND $batch AS item
                    MATCH (m:Module {id: item.module_id})
                    MERGE (c:Class {id: item.class_id})
                    ON CREATE SET c.repo_id = $repo_id, c.name = item.name, c.qualname = item.qualname,
                                  c.file_path = item.rel_path, c.start_line = item.start_line,
                                  c.end_line = item.end_line, c.docstring = item.docstring, c.bases = item.bases
                    MERGE (m)-[:DEFINES]->(c)
                """, {"repo_id": repo_id, "batch": classes_batch})

            if methods_batch:
                session.run("""
                    UNWIND $batch AS item
                    MATCH (c:Class {id: item.class_id})
                    MERGE (fn:Function {id: item.method_id})
                    ON CREATE SET fn.repo_id = $repo_id, fn.name = item.name, fn.qualname = item.qualname,
                                  fn.file_path = item.rel_path, fn.start_line = item.start_line,
                                  fn.end_line = item.end_line, fn.signature = item.signature,
                                  fn.docstring = item.docstring, fn.is_async = item.is_async, fn.is_method = true
                    MERGE (c)-[:DEFINES]->(fn)
                """, {"repo_id": repo_id, "batch": methods_batch})

            # 7. Upsert Standalone Functions in batch
            functions_batch = []
            for parsed in parsed_results:
                if parsed.syntax_error:
                    continue
                module_id = f"module:{repo_id}:{parsed.module_dot_path}"
                for fn in parsed.functions:
                    fn_id = f"func:{repo_id}:{parsed.relative_path}:{fn.qualname}"
                    functions_batch.append({
                        "module_id": module_id,
                        "fn_id": fn_id,
                        "name": fn.name,
                        "qualname": fn.qualname,
                        "rel_path": parsed.relative_path,
                        "start_line": fn.start_line,
                        "end_line": fn.end_line,
                        "signature": fn.signature,
                        "docstring": fn.docstring or "",
                        "is_async": fn.is_async
                    })

            if functions_batch:
                session.run("""
                    UNWIND $batch AS item
                    MATCH (m:Module {id: item.module_id})
                    MERGE (fn:Function {id: item.fn_id})
                    ON CREATE SET fn.repo_id = $repo_id, fn.name = item.name, fn.qualname = item.qualname,
                                  fn.file_path = item.rel_path, fn.start_line = item.start_line,
                                  fn.end_line = item.end_line, fn.signature = item.signature,
                                  fn.docstring = item.docstring, fn.is_async = item.is_async, fn.is_method = false
                    MERGE (m)-[:DEFINES]->(fn)
                """, {"repo_id": repo_id, "batch": functions_batch})

            # 8. Upsert CALLS edges in batches with indexed labels
            fn_calls_batch = []
            cls_calls_batch = []
            pkg_calls_batch = []
            for call in resolved_calls:
                call_data = {
                    "source_id": call.source_id,
                    "target_id": call.target_id,
                    "line_no": call.line_no,
                    "call_expr": call.call_expr,
                    "confidence": call.confidence,
                    "res_type": call.resolution_type,
                    "details": call.details
                }
                if call.target_id.startswith("pkg:"):
                    pkg_calls_batch.append(call_data)
                elif call.target_id.startswith("class:"):
                    cls_calls_batch.append(call_data)
                else:
                    fn_calls_batch.append(call_data)

            chunk_size = 500
            if fn_calls_batch:
                for i in range(0, len(fn_calls_batch), chunk_size):
                    chunk = fn_calls_batch[i:i + chunk_size]
                    session.run("""
                        UNWIND $batch AS item
                        MATCH (source:Function {id: item.source_id})
                        MATCH (target:Function {id: item.target_id})
                        MERGE (source)-[rel:CALLS {line_no: item.line_no}]->(target)
                        ON CREATE SET rel.call_expr = item.call_expr, rel.confidence = item.confidence,
                                      rel.resolution_type = item.res_type, rel.details = item.details
                        ON MATCH SET rel.confidence = item.confidence, rel.call_expr = item.call_expr
                    """, {"batch": chunk})

            if cls_calls_batch:
                for i in range(0, len(cls_calls_batch), chunk_size):
                    chunk = cls_calls_batch[i:i + chunk_size]
                    session.run("""
                        UNWIND $batch AS item
                        MATCH (source:Function {id: item.source_id})
                        MATCH (target:Class {id: item.target_id})
                        MERGE (source)-[rel:CALLS {line_no: item.line_no}]->(target)
                        ON CREATE SET rel.call_expr = item.call_expr, rel.confidence = item.confidence,
                                      rel.resolution_type = item.res_type, rel.details = item.details
                        ON MATCH SET rel.confidence = item.confidence, rel.call_expr = item.call_expr
                    """, {"batch": chunk})

            if pkg_calls_batch:
                for i in range(0, len(pkg_calls_batch), chunk_size):
                    chunk = pkg_calls_batch[i:i + chunk_size]
                    session.run("""
                        UNWIND $batch AS item
                        MATCH (source:Function {id: item.source_id})
                        MATCH (target:ExternalPackage {id: item.target_id})
                        MERGE (source)-[rel:CALLS {line_no: item.line_no}]->(target)
                        ON CREATE SET rel.call_expr = item.call_expr, rel.confidence = item.confidence,
                                      rel.resolution_type = item.res_type, rel.details = item.details
                        ON MATCH SET rel.confidence = item.confidence, rel.call_expr = item.call_expr
                    """, {"batch": chunk})

        logger.info(f"Successfully persisted repo {repo_id} to Neo4j")

ingestion_service = IngestionService()
