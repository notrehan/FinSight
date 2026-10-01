import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("finsight.audit")

class StructuredLogger:
    @staticmethod
    def log_event(
        trace_id: str,
        session_id: str,
        event_type: str,
        node: str,
        status: str,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        event = {
            "timestamp": time.time(),
            "trace_id": trace_id,
            "session_id": session_id,
            "event_type": event_type,
            "node": node,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error_code": error_code,
            "metadata": metadata or {}
        }
        logger.info(json.dumps(event))
        return event
