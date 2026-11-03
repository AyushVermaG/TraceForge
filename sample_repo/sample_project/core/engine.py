"""Processing engine handling transaction executions."""
import time
import logging
from typing import Dict, Any, List
from sample_project.core.validator import validate_payload, ValidationError

logger = logging.getLogger("TraceForgeSample.Engine")

class ExecutionEngine:
    """Core stateful orchestrator for task processing."""

    def __init__(self, engine_id: str, max_concurrency: int = 10):
        self.engine_id = engine_id
        self.max_concurrency = max_concurrency
        self.processed_count = 0
        self.active_jobs: List[str] = []

    def dispatch(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input payload and execute internal dispatch logic."""
        if not validate_payload(payload):
            raise ValidationError(f"Invalid job payload for {job_id}", field="payload")
        
        self.active_jobs.append(job_id)
        result = self._execute_job(job_id, payload)
        self.processed_count += 1
        return result

    def _execute_job(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal worker executing payload action."""
        start_ts = time.time()
        action = payload.get("action", "noop")
        logger.info(f"Executing {action} on job {job_id}")
        
        duration = time.time() - start_ts
        return {
            "job_id": job_id,
            "engine": self.engine_id,
            "status": "COMPLETED",
            "duration_ms": duration * 1000,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return engine operational telemetry."""
        return {
            "engine_id": self.engine_id,
            "processed_jobs": self.processed_count,
            "active_count": len(self.active_jobs),
        }
