import time
import uuid

from memory.observability import record_latency


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Correlation-ID", "")[:64]
        request.correlation_id = incoming if incoming and all(char.isalnum() or char in "-_" for char in incoming) else str(uuid.uuid4())
        started = time.perf_counter()
        response = self.get_response(request)
        latency = round((time.perf_counter() - started) * 1000, 2)
        record_latency(latency)
        response["X-Correlation-ID"] = request.correlation_id
        response["Server-Timing"] = f"app;dur={latency}"
        return response
