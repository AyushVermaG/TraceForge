"""Neo4j schema constraints and index migrations."""
import logging
from typing import List
from app.database.neo4j_client import neo4j_client

logger = logging.getLogger("TraceForge.Schema")

SCHEMA_CONSTRAINTS: List[str] = [
    # Primary Key Uniqueness Constraints
    "CREATE CONSTRAINT repo_id_unique IF NOT EXISTS FOR (r:Repository) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT file_id_unique IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT module_id_unique IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT function_id_unique IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
    "CREATE CONSTRAINT package_id_unique IF NOT EXISTS FOR (p:ExternalPackage) REQUIRE p.id IS UNIQUE",

    # Performance Lookup Indexes
    "CREATE INDEX repo_name_idx IF NOT EXISTS FOR (r:Repository) ON (r.name)",
    "CREATE INDEX file_repo_idx IF NOT EXISTS FOR (f:File) ON (f.repo_id)",
    "CREATE INDEX module_repo_idx IF NOT EXISTS FOR (m:Module) ON (m.repo_id)",
    "CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name)",
    "CREATE INDEX function_name_idx IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
]

def init_schema():
    """Apply Neo4j constraints and indexes idempotently."""
    health = neo4j_client.ping()
    if not health["connected"]:
        logger.warning(f"Skipping schema initialization: {health['error']}")
        return False
    
    logger.info("Initializing Neo4j schema constraints and indexes...")
    for statement in SCHEMA_CONSTRAINTS:
        try:
            neo4j_client.execute_write(statement)
        except Exception as e:
            logger.warning(f"Constraint statement '{statement}' warning: {str(e)}")
    
    logger.info("Neo4j schema constraints verified successfully")
    return True
