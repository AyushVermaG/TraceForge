"""Main application entrypoint and coordinator."""
import sys
from typing import Dict, Any
from sample_project.core.engine import ExecutionEngine
from sample_project.services.auth_service import AuthService
from sample_project.services.analytics import serialize_metrics

def bootstrap_application(env_name: str = "production") -> ExecutionEngine:
    """Instantiate dependencies and return ready engine instance."""
    auth = AuthService()
    engine = ExecutionEngine(engine_id=f"engine_{env_name}")
    return engine

def handle_incoming_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process incoming client payload with security and execution checks."""
    auth = AuthService()
    email = payload.get("user_email", "")
    token = auth.generate_token(email)
    
    if not token:
        return {"error": "Authentication failed", "code": 401}
    
    engine = bootstrap_application()
    result = engine.dispatch(job_id=payload.get("id", "job_0"), payload=payload)
    
    # Record telemetry
    telemetry_json = serialize_metrics("request_latency", [12.4, 15.8, 9.2, 45.1])
    return {
        "status": "SUCCESS",
        "result": result,
        "telemetry": telemetry_json,
    }

if __name__ == "__main__":
    demo_payload = {
        "id": "demo_job_101",
        "action": "ANALYZE_GRAPH",
        "user_email": "engineer@traceforge.dev",
    }
    response = handle_incoming_request(demo_payload)
    print(f"Executed: {response}")
