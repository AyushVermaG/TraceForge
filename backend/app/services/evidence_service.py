"""Evidence service for extracting exact source slices and call dependencies."""
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import HTTPException
from app.config import settings
from app.database.neo4j_client import neo4j_client
from app.models.graph_models import EvidenceDetail, DependencyRef, NodeKind
from app.parser.zip_handler import is_safe_path

logger = logging.getLogger("TraceForge.EvidenceService")

class EvidenceService:
    """Retrieves source code evidence and caller/callee context for any node."""

    def get_node_evidence(self, node_id: str) -> EvidenceDetail:
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # 1. Fetch node details
            node_res = session.run("""
                MATCH (n {id: $node_id})
                RETURN n, labels(n) AS labels
            """, {"node_id": node_id}).single()

            if not node_res:
                raise HTTPException(status_code=404, detail=f"Entity '{node_id}' not found in graph database")

            node_data = node_res["n"]
            labels = node_res["labels"]
            kind = self._resolve_label(labels)

            repo_id = node_data.get("repo_id")
            file_path = node_data.get("file_path") or node_data.get("path") or ""
            start_line = int(node_data.get("start_line", 1))
            end_line = int(node_data.get("end_line", start_line))

            # 2. Fetch inbound dependencies (who calls or imports this)
            inbound_refs: List[DependencyRef] = []
            inbound_res = session.run("""
                MATCH (caller)-[r]->(tgt {id: $node_id})
                RETURN caller.id AS id, caller.name AS name, labels(caller) AS labels,
                       r.line_no AS line_no, r.confidence AS confidence, caller.file_path AS file_path
                LIMIT 25
            """, {"node_id": node_id})
            for rec in inbound_res:
                inbound_refs.append(DependencyRef(
                    node_id=rec["id"],
                    name=rec["name"] or rec["id"].split(":")[-1],
                    kind=self._resolve_label(rec["labels"]),
                    line_no=rec["line_no"],
                    confidence=rec["confidence"],
                    file_path=rec["file_path"]
                ))

            # 3. Fetch outbound dependencies (who this calls or imports)
            outbound_refs: List[DependencyRef] = []
            outbound_res = session.run("""
                MATCH (src {id: $node_id})-[r]->(callee)
                RETURN callee.id AS id, callee.name AS name, labels(callee) AS labels,
                       r.line_no AS line_no, r.confidence AS confidence, callee.file_path AS file_path
                LIMIT 25
            """, {"node_id": node_id})
            for rec in outbound_res:
                outbound_refs.append(DependencyRef(
                    node_id=rec["id"],
                    name=rec["name"] or rec["id"].split(":")[-1],
                    kind=self._resolve_label(rec["labels"]),
                    line_no=rec["line_no"],
                    confidence=rec["confidence"],
                    file_path=rec["file_path"]
                ))

            # 4. Extract source code slice from disk cache
            code_snippet = self._read_source_slice(repo_id, file_path, start_line, end_line)

            return EvidenceDetail(
                node_id=node_id,
                kind=kind,
                name=node_data.get("name", "Symbol"),
                qualified_name=node_data.get("qualname") or node_data.get("name", ""),
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                docstring=node_data.get("docstring"),
                signature=node_data.get("signature"),
                is_async=node_data.get("is_async"),
                is_method=node_data.get("is_method"),
                code_snippet=code_snippet,
                inbound_dependencies=inbound_refs,
                outbound_dependencies=outbound_refs
            )

    def _read_source_slice(self, repo_id: Optional[str], file_path: str, start_line: int, end_line: int) -> str:
        """Safely read lines [start_line..end_line] from disk."""
        if not repo_id or not file_path:
            return "# Source unavailable for this node type"

        repo_source_dir = settings.storage_path / repo_id / "source"
        target_file = repo_source_dir / file_path

        if not is_safe_path(repo_source_dir, target_file) or not target_file.exists():
            return f"# Source file not found or inaccessible: {file_path}"

        try:
            lines = target_file.read_text(encoding="utf-8", errors="replace").splitlines()
            # 1-indexed line numbers
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)
            slice_lines = lines[start_idx:end_idx]
            return "\n".join(slice_lines)
        except Exception as e:
            return f"# Error reading source file: {str(e)}"

    def _resolve_label(self, labels: List[str]) -> NodeKind:
        for lbl in (NodeKind.FUNCTION, NodeKind.CLASS, NodeKind.MODULE, NodeKind.FILE, NodeKind.REPOSITORY, NodeKind.EXTERNAL_PACKAGE):
            if lbl.value in labels:
                return lbl
        return NodeKind.MODULE

evidence_service = EvidenceService()
