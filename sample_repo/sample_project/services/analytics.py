"""Analytics telemetry recorder and aggregator."""
import json
import math
from typing import Dict, Any, List

def calculate_percentile(values: List[float], percentile: float = 95.0) -> float:
    """Calculate the p-th percentile of a list of numeric measurements."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return d0 + d1

def serialize_metrics(name: str, samples: List[float]) -> str:
    """Format and serialize telemetry data into standard JSON payload."""
    p95 = calculate_percentile(samples, 95.0)
    avg = sum(samples) / len(samples) if samples else 0.0
    payload = {
        "metric_name": name,
        "sample_count": len(samples),
        "mean": round(avg, 2),
        "p95": round(p95, 2),
    }
    return json.dumps(payload)
