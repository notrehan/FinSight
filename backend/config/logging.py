import json
import logging
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        data = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                "logger": record.name, "message": record.getMessage()}
        for field in ("correlation_id", "latency_ms", "provider", "error_type", "ticker"):
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)
