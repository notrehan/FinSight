import json
from django.core.management.base import BaseCommand, CommandError
from apps.evaluations.runner import run_evaluation


class Command(BaseCommand):
    help = "Run the versioned FinSight API evaluation dataset and write a JSON report."

    def add_arguments(self, parser):
        parser.add_argument("--dataset")

    def handle(self, *args, **options):
        try:
            report = run_evaluation(options.get("dataset"))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(report, indent=2))
