from collections import deque
from threading import Lock

_latencies = deque(maxlen=1000)
_lock = Lock()


def record_latency(value):
    with _lock:
        _latencies.append(value)


def latency_summary():
    with _lock:
        values = sorted(_latencies)
    def percentile(value):
        if not values:
            return None
        return round(values[min(len(values) - 1, int((len(values) - 1) * value))], 2)
    return {"sample_count": len(values), "latency_ms": {"p50": percentile(.5), "p95": percentile(.95)},
            "scope": "This application worker process only."}
