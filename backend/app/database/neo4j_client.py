"""Neo4j client management using official Python Driver."""
import os
import logging
from typing import Optional, Dict, Any, List
import certifi
from neo4j import GraphDatabase, Driver, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError
from app.config import settings

# Configure standard CA certificate bundle for secure TLS connections
if not os.environ.get("SSL_CERT_FILE"):
    try:
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except Exception:
        pass

logger = logging.getLogger("TraceForge.Database")

class Neo4jClient:
    """Manages thread-safe Neo4j driver connection and query execution."""

    def __init__(self):
        self._driver: Optional[Driver] = None

    def is_configured(self) -> bool:
        """Check if valid non-placeholder credentials have been provided."""
        if not settings.NEO4J_URI or not settings.NEO4J_PASSWORD:
            return False
        if "your-instance" in settings.NEO4J_URI or "your-secure-password" in settings.NEO4J_PASSWORD:
            return False
        return True

    def get_driver(self) -> Driver:
        """Lazily initialize and return the Neo4j driver."""
        if not self.is_configured():
            raise ValueError("Neo4j URI or Password is not configured in backend/.env")

        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                    max_connection_lifetime=30 * 60,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=15.0,
                )
                logger.info("Neo4j driver initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
                raise
        return self._driver

    def close(self):
        """Close driver connections on shutdown."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    def ping(self) -> Dict[str, Any]:
        """Verify Neo4j connectivity and fetch version metadata."""
        if not self.is_configured():
            return {
                "connected": False,
                "configured": False,
                "version": None,
                "error": "Neo4j credentials (NEO4J_URI, NEO4J_PASSWORD) are not yet configured in backend/.env"
            }

        try:
            driver = self.get_driver()
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Validate simple query
                result = session.run("RETURN 1 AS ping")
                record = result.single()
                if not record or record["ping"] != 1:
                    return {
                        "connected": False,
                        "configured": True,
                        "version": None,
                        "error": "Unexpected response from Neo4j ping"
                    }
                
                # Fetch database component version
                try:
                    v_res = session.run("CALL dbms.components() YIELD name, versions RETURN versions[0] AS version LIMIT 1")
                    v_rec = v_res.single()
                    version = v_rec["version"] if v_rec else "AuraDB"
                except Exception:
                    version = "Neo4j AuraDB"

                return {
                    "connected": True,
                    "configured": True,
                    "version": version,
                    "error": None
                }
        except AuthError as e:
            logger.error("Neo4j authentication failed: invalid credentials")
            return {
                "connected": False,
                "configured": True,
                "version": None,
                "error": "Neo4j Authentication Failed: Check NEO4J_USERNAME and NEO4J_PASSWORD"
            }
        except ServiceUnavailable as e:
            logger.error(f"Neo4j instance unreachable: {str(e)}")
            return {
                "connected": False,
                "configured": True,
                "version": None,
                "error": f"Neo4j Service Unavailable: Could not reach {settings.NEO4J_URI}"
            }
        except Exception as e:
            logger.error(f"Neo4j health check error: {str(e)}")
            return {
                "connected": False,
                "configured": True,
                "version": None,
                "error": f"Neo4j Connection Error: {type(e).__name__}"
            }

    def execute_read(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run a parameterized read transaction."""
        driver = self.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run a parameterized write transaction."""
        driver = self.get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

neo4j_client = Neo4jClient()
