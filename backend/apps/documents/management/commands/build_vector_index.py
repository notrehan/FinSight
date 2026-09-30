from django.core.management.base import BaseCommand, CommandError
from rag.vector_index import VectorIndex


class Command(BaseCommand):
    help = "Build a versioned FAISS index over active page-aware filing chunks."

    def handle(self, *args, **options):
        try:
            result = VectorIndex.build()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Indexed {result['chunk_count']} chunks with {result['embedding_model']} "
            f"(corpus SHA-256 {result['corpus_sha256']})."
        ))
