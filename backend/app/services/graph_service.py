"""Progressive Cypher query service for bounded graph visualization."""
import logging
from typing import List, Dict, Any, Optional
from app.config import settings
from app.database.neo4j_client import neo4j_client
from app.models.graph_models import GraphNode, GraphEdge, GraphResponse, NodeKind, RelationshipKind
from app.models.api_models import SearchItem, SearchResponse, RepositorySummary

logger = logging.getLogger("TraceForge.GraphService")


def _sanitize_props(props: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Neo4j-native types (DateTime, Date, etc.) to JSON-safe strings."""
    result = {}
    for k, v in props.items():
        if hasattr(v, "iso_format"):
            # neo4j.time.DateTime / Date / Time all have iso_format()
            result[k] = v.iso_format()
        elif isinstance(v, (str, int, float, bool, list)) or v is None:
            result[k] = v
        else:
            result[k] = str(v)
    return result

class GraphService:
    """Provides progressive, bounded graph queries for frontend visualization."""

    def get_overview(self, repo_id: str, limit: int = 35) -> GraphResponse:
        """Fetch initial clean repository overview (Repo + Modules + Files)."""
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Check total node count for this repo
            count_res = session.run("""
                MATCH (n) WHERE n.repo_id = $repo_id OR n.id = $repo_id
                RETURN count(n) AS total
            """, {"repo_id": repo_id}).single()
            total_count = count_res["total"] if count_res else 0

            # Progressive overview query: Fetch Repository, Files, and Modules
            query = """
                MATCH (r:Repository {id: $repo_id})
                OPTIONAL MATCH (r)-[rel1:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[rel2:CONTAINS]->(m:Module)
                RETURN r, collect(DISTINCT f)[0..$file_limit] AS files,
                          collect(DISTINCT m)[0..$mod_limit] AS modules
            """
            result = session.run(query, {
                "repo_id": repo_id,
                "file_limit": limit // 2,
                "mod_limit": limit // 2
            }).single()

            if not result or not result["r"]:
                return GraphResponse(message=f"Repository '{repo_id}' not found")

            nodes_dict: Dict[str, GraphNode] = {}
            edges: List[GraphEdge] = []

            # Add Repository Node
            r_node = result["r"]
            nodes_dict[r_node["id"]] = GraphNode(
                id=r_node["id"],
                kind=NodeKind.REPOSITORY,
                name=r_node.get("name", "Repository"),
                properties=_sanitize_props(dict(r_node))
            )

            # Add Files & Edges
            for f in result.get("files", []):
                if f:
                    f_id = f["id"]
                    nodes_dict[f_id] = GraphNode(
                        id=f_id,
                        kind=NodeKind.FILE,
                        name=f.get("path", "").split("/")[-1] or f.get("path", "file"),
                        properties=_sanitize_props(dict(f))
                    )
                    edges.append(GraphEdge(
                        id=f"rel_repo_{f_id}",
                        source=r_node["id"],
                        target=f_id,
                        type=RelationshipKind.CONTAINS
                    ))

            # Add Modules & Edges
            for m in result.get("modules", []):
                if m:
                    m_id = m["id"]
                    nodes_dict[m_id] = GraphNode(
                        id=m_id,
                        kind=NodeKind.MODULE,
                        name=m.get("name", "").split(".")[-1] or m.get("name", "module"),
                        properties=_sanitize_props(dict(m))
                    )
                    # Find parent file
                    p_file = f"file:{repo_id}:{m.get('name', '').replace('.', '/')}.py"
                    if p_file in nodes_dict:
                        edges.append(GraphEdge(
                            id=f"rel_file_{m_id}",
                            source=p_file,
                            target=m_id,
                            type=RelationshipKind.CONTAINS
                        ))
                    else:
                        edges.append(GraphEdge(
                            id=f"rel_repo_{m_id}",
                            source=r_node["id"],
                            target=m_id,
                            type=RelationshipKind.CONTAINS
                        ))

            nodes = list(nodes_dict.values())
            is_truncated = total_count > len(nodes)
            msg = f"Showing {len(nodes)} overview entities out of {total_count} total." if is_truncated else None

            return GraphResponse(
                nodes=nodes,
                edges=edges,
                total_nodes_in_scope=total_count,
                returned_nodes_count=len(nodes),
                truncated=is_truncated,
                message=msg
            )

    def expand_node(self, node_id: str, depth: int = 1, limit: int = 30) -> GraphResponse:
        """Progressively expand the 1-hop neighborhood of a given node."""
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Fetch target node
            root_res = session.run("MATCH (n {id: $node_id}) RETURN n, labels(n) AS labels", {"node_id": node_id}).single()
            if not root_res:
                return GraphResponse(message=f"Node '{node_id}' not found")

            root_data = root_res["n"]
            root_kind = self._resolve_label(root_res["labels"])

            nodes_dict: Dict[str, GraphNode] = {
                node_id: GraphNode(
                    id=node_id,
                    kind=root_kind,
                    name=root_data.get("name") or root_data.get("qualname") or "Node",
                    properties=_sanitize_props(dict(root_data))
                )
            }
            edges: List[GraphEdge] = []

            # Outgoing relationships
            out_res = session.run("""
                MATCH (src {id: $node_id})-[r]->(tgt)
                RETURN src, r, tgt, type(r) AS rel_type, labels(tgt) AS tgt_labels
                LIMIT $limit
            """, {"node_id": node_id, "limit": limit})

            for rec in out_res:
                tgt = rec["tgt"]
                tgt_id = tgt["id"]
                tgt_kind = self._resolve_label(rec["tgt_labels"])

                if tgt_id not in nodes_dict:
                    nodes_dict[tgt_id] = GraphNode(
                        id=tgt_id,
                        kind=tgt_kind,
                        name=tgt.get("name") or tgt.get("qualname") or tgt_id.split(":")[-1],
                        properties=_sanitize_props(dict(tgt))
                    )

                edges.append(GraphEdge(
                    id=f"{rec['rel_type']}_{node_id}_{tgt_id}_{rec['r'].element_id}",
                    source=node_id,
                    target=tgt_id,
                    type=RelationshipKind(rec["rel_type"]),
                    properties=_sanitize_props(dict(rec["r"]))
                ))

            # Incoming relationships
            in_res = session.run("""
                MATCH (src)-[r]->(tgt {id: $node_id})
                RETURN src, r, tgt, type(r) AS rel_type, labels(src) AS src_labels
                LIMIT $limit
            """, {"node_id": node_id, "limit": limit})

            for rec in in_res:
                src = rec["src"]
                src_id = src["id"]
                src_kind = self._resolve_label(rec["src_labels"])

                if src_id not in nodes_dict:
                    nodes_dict[src_id] = GraphNode(
                        id=src_id,
                        kind=src_kind,
                        name=src.get("name") or src.get("qualname") or src_id.split(":")[-1],
                        properties=_sanitize_props(dict(src))
                    )

                edges.append(GraphEdge(
                    id=f"{rec['rel_type']}_{src_id}_{node_id}_{rec['r'].element_id}",
                    source=src_id,
                    target=node_id,
                    type=RelationshipKind(rec["rel_type"]),
                    properties=_sanitize_props(dict(rec["r"]))
                ))

            nodes = list(nodes_dict.values())
            return GraphResponse(
                nodes=nodes,
                edges=edges,
                total_nodes_in_scope=len(nodes),
                returned_nodes_count=len(nodes),
                truncated=False,
                message=f"Expanded {len(nodes) - 1} connected neighbors for {nodes_dict[node_id].name}"
            )

    def search_symbols(self, repo_id: str, query: str, limit: int = 20) -> SearchResponse:
        """Search classes, functions, and modules by name/qualname."""
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            cypher = """
                MATCH (n)
                WHERE (n.repo_id = $repo_id OR $repo_id = '')
                  AND (toLower(n.name) CONTAINS toLower($q) OR toLower(n.qualname) CONTAINS toLower($q))
                  AND (n:Class OR n:Function OR n:Module OR n:File)
                RETURN n, labels(n) AS labels
                LIMIT $limit
            """
            results = session.run(cypher, {"repo_id": repo_id, "q": query.strip(), "limit": limit})
            items: List[SearchItem] = []
            for rec in results:
                n = rec["n"]
                kind = self._resolve_label(rec["labels"])
                items.append(SearchItem(
                    id=n["id"],
                    kind=kind,
                    name=n.get("name", "Symbol"),
                    qualified_name=n.get("qualname") or n.get("name", ""),
                    file_path=n.get("file_path") or n.get("path"),
                    line_no=n.get("start_line")
                ))
            return SearchResponse(query=query, results=items, total=len(items))

    def list_repositories(self) -> List[RepositorySummary]:
        """List all ingested repositories with aggregated statistics."""
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            query = """
                MATCH (r:Repository)
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                OPTIONAL MATCH (m)-[:DEFINES]->(fn1:Function)
                OPTIONAL MATCH (c)-[:DEFINES]->(fn2:Function)
                OPTIONAL MATCH (caller:Function {repo_id: r.id})-[rel:CALLS]->()
                RETURN r.id AS id, r.name AS name, toString(r.ingested_at) AS ingested_at,
                       count(DISTINCT f) AS total_files,
                       count(DISTINCT m) AS total_modules,
                       count(DISTINCT c) AS total_classes,
                       count(DISTINCT fn1) + count(DISTINCT fn2) AS total_functions,
                       count(DISTINCT rel) AS total_calls
                ORDER BY ingested_at DESC
            """
            results = session.run(query)
            repos: List[RepositorySummary] = []
            for rec in results:
                repos.append(RepositorySummary(
                    id=rec["id"],
                    name=rec["name"] or "Repository",
                    ingested_at=rec["ingested_at"] or "",
                    total_files=rec["total_files"],
                    total_modules=rec["total_modules"],
                    total_classes=rec["total_classes"],
                    total_functions=rec["total_functions"],
                    total_calls=rec["total_calls"]
                ))
            return repos

    def delete_repository(self, repo_id: str) -> bool:
        """Completely detach and remove all graph nodes belonging to repo_id."""
        driver = neo4j_client.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            session.run("""
                MATCH (n) WHERE n.repo_id = $repo_id OR n.id = $repo_id
                DETACH DELETE n
            """, {"repo_id": repo_id})
            return True

    def _resolve_label(self, labels: List[str]) -> NodeKind:
        for lbl in (NodeKind.FUNCTION, NodeKind.CLASS, NodeKind.MODULE, NodeKind.FILE, NodeKind.REPOSITORY, NodeKind.EXTERNAL_PACKAGE):
            if lbl.value in labels:
                return lbl
        return NodeKind.MODULE

graph_service = GraphService()
