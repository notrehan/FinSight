"""Versioned, deterministic quality gate for the FinSight evaluation set."""
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.conf import settings
from django.test import Client
from django.core.management import call_command
from django.contrib.auth import get_user_model


def run_evaluation(dataset_path: str | None = None) -> dict[str, Any]:
    call_command("migrate", interactive=False, verbosity=0)
    call_command("seed_demo_data", verbosity=0)
    path = Path(dataset_path) if dataset_path else settings.BASE_DIR.parent / "evaluations" / "v1.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))
    client = Client()
    user_model = get_user_model()
    eval_user, _ = user_model.objects.get_or_create(username="finsight-eval-runner")
    client.force_login(eval_user)
    results = []
    for case in dataset["cases"]:
        response = client.post(
            "/api/v1/assistant/ask",
            data=json.dumps({
                "question": case["question"],
                "symbol": case.get("symbol"),
                "company_id": case.get("company_id"),
                "as_of_preference": case.get("as_of_preference", "latest_available"),
            }),
            content_type="application/json",
            HTTP_HOST="localhost",
            HTTP_X_CORRELATION_ID=f"eval_{case['id']}",
        )
        try:
            body = response.json()
        except Exception:
            body = {}
        checks = {
            "http_success": response.status_code == 200,
            "schema_shape": all(key in body for key in ("trace_id", "answer", "safety_label", "citations", "numeric_claims", "limitations")),
            "expected_safety": body.get("safety_label") == case["expected_safety_label"],
        }
        required_tools = set(case.get("required_tools", []))
        actual_tools = {item.get("tool") for item in body.get("tool_trace", []) if isinstance(item, dict)}
        checks["required_tools"] = required_tools.issubset(actual_tools)
        if case.get("expected_numeric_claim"):
            expected = case["expected_numeric_claim"]
            checks["numeric_claim"] = any(
                _same_decimal(claim.get("value"), expected["value"])
                and claim.get("unit") == expected["unit"]
                and claim.get("period") == expected["period"]
                and bool(claim.get("source_id"))
                and bool(claim.get("as_of"))
                for claim in body.get("numeric_claims", [])
            )
        if case.get("expected_citation_page") is not None:
            checks["citation_page"] = any(
                citation.get("page") == case["expected_citation_page"]
                and citation.get("source_url", "").startswith("https://")
                for citation in body.get("citations", [])
            )
        if case.get("answer_contains"):
            checks["grounded_text"] = case["answer_contains"].lower() in body.get("answer", "").lower()
        results.append({
            "case_id": case["id"], "checks": checks, "passed": all(checks.values()),
            "status_code": response.status_code, "actual_safety_label": body.get("safety_label"),
            "actual_tools": sorted(actual_tools),
            "actual_answer": body.get("answer", ""),
            "actual_tool_trace": body.get("tool_trace", []),
            "actual_numeric_claims": body.get("numeric_claims", []),
            "actual_citation_pages": [citation.get("page") for citation in body.get("citations", [])],
        })

    total = len(results)
    passed = sum(result["passed"] for result in results)
    refusal_cases = [result for result, case in zip(results, dataset["cases"]) if case["expected_safety_label"] == "refusal"]
    report = {
        "dataset_version": dataset["version"],
        "prompt_version": getattr(settings, "PROMPT_VERSION", "unknown"),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "case_count": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "refusal_count": len(refusal_cases),
        "refusal_pass_rate": round(sum(case["checks"]["expected_safety"] for case in refusal_cases) / len(refusal_cases), 4) if refusal_cases else None,
        "results": results,
    }
    output_dir = settings.BASE_DIR.parent / "evaluations" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(output_path)
    return report


def _same_decimal(actual: Any, expected: Any) -> bool:
    try:
        return Decimal(str(actual)) == Decimal(str(expected))
    except (InvalidOperation, ValueError, TypeError):
        return False
