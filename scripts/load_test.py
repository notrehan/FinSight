"""Small repeatable HTTP load check for the local/deployed research API."""
import argparse
import concurrent.futures
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/ask")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--company", default="tcs")
    args = parser.parse_args()
    if not 1 <= args.requests <= 500 or not 1 <= args.workers <= 32:
        parser.error("requests must be 1–500 and workers 1–32")

    def one(index):
        started = time.perf_counter()
        payload = {"company": args.company, "question": "What was revenue reported in the latest annual report?", "session_id": str(uuid.uuid4())}
        try:
            response = requests.post(args.url, json=payload, timeout=45, headers={"X-Correlation-ID": str(uuid.uuid4())})
            return {"latency_ms": round((time.perf_counter() - started) * 1000, 2), "status": response.status_code}
        except Exception as exc:
            return {"latency_ms": round((time.perf_counter() - started) * 1000, 2), "status": "error", "error": type(exc).__name__}

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, range(args.requests)))
    duration = time.perf_counter() - started
    timings = sorted(row["latency_ms"] for row in results)
    percentile = lambda p: timings[min(len(timings) - 1, int((len(timings) - 1) * p))] if timings else None
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "url": args.url, "request_count": args.requests,
        "workers": args.workers, "duration_seconds": round(duration, 3), "throughput_rps": round(args.requests / duration, 3),
        "latency_ms": {"p50": percentile(.50), "p95": percentile(.95), "max": max(timings) if timings else None},
        "status_counts": {str(code): sum(str(row["status"]) == str(code) for row in results) for code in {row["status"] for row in results}},
        "failures": [row for row in results if row["status"] != 200]}
    output_dir = ROOT / "data" / "evals" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"load-test-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved report to {output}")


if __name__ == "__main__":
    main()
