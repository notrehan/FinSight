import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from memory.models import EvaluationScore, PromptVersion
from rag.search import search


class Command(BaseCommand):
    help = "Run the 20-question filing retrieval and citation evaluation for the active prompt version."

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR).parent / "data" / "evals" / "finqa_questions.json"
        if not path.exists():
            raise CommandError(f"Evaluation set not found: {path}")
        dataset = json.loads(path.read_text(encoding="utf-8"))
        cases = dataset.get("questions", [])
        if len(cases) < 20:
            raise CommandError("The RAG evaluation dataset must contain at least 20 questions.")
        prompt_version = PromptVersion.objects.filter(active=True).order_by("-created_at").first()
        if not prompt_version:
            raise CommandError("No active prompt version exists. Add or activate one in Django Admin.")
        results = []
        for index, case in enumerate(cases, 1):
            try:
                retrieved = search(case["company"], case["question"], top_k=5)
                context = "\n".join(str(row.get("text", "")) for row in retrieved).casefold()
                expected_hit = any(term.casefold() in context for term in case.get("expected_terms", []))
                valid_pages = bool(retrieved) and all(int(row.get("page") or 0) > 0 for row in retrieved)
                results.append({"case": index, "company": case["company"], "question": case["question"],
                    "expected_term_retrieved": expected_hit, "citation_page_available": valid_pages, "retrieved_count": len(retrieved)})
            except Exception as exc:
                results.append({"case": index, "company": case.get("company"), "question": case.get("question"),
                    "expected_term_retrieved": False, "citation_page_available": False, "error": type(exc).__name__})
        metrics = {
            "expected_term_retrieval_rate": sum(row["expected_term_retrieved"] for row in results) / len(results),
            "citation_page_availability": sum(row["citation_page_available"] for row in results) / len(results),
        }
        for metric, score in metrics.items():
            EvaluationScore.objects.create(prompt_version=prompt_version, dataset=dataset["dataset"], metric=metric,
                score=score, details={"case_count": len(results)})
        report_dir = Path(settings.BASE_DIR).parent / "data" / "evals" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = {"created_at": datetime.now(timezone.utc).isoformat(), "prompt_version": prompt_version.version,
            "dataset": dataset["dataset"], "case_count": len(results), "metrics": metrics, "cases": results}
        target = report_dir / f"{prompt_version.version}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Evaluated {len(results)} questions for {prompt_version.version}. Report: {target}"))
        self.stdout.write(json.dumps(metrics, indent=2))
