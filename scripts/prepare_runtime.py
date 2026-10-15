"""Prepare public model caches and the bundled policy index during image build.

Run from the repository root with ``python -m scripts.prepare_runtime``.
No Groq API key is required. Fail the build if any preparation stage fails.
"""

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def prepare_embeddings():
    from app.rag.embeddings import embed_text

    vector = embed_text("insurance policy")
    print(f"Embedding model cached ({len(vector)} dimensions).", flush=True)


def prepare_ocr():
    from app.services.ocr_service import get_reader

    get_reader()
    print("English OCR detection and recognition models cached.", flush=True)


def prepare_policy():
    from app.rag.ingest import ingest_policy
    from app.rag.qdrant_store import qdrant_client

    try:
        count = ingest_policy("data/policies/motor_policy.txt")
        print(f"Bundled policy index prepared ({count} sections).", flush=True)
    finally:
        # Release Qdrant's local lock and flush storage before Docker saves
        # this layer. Do not rely on interpreter-shutdown finalizers.
        qdrant_client.close()


def main(argv=None):
    stages = {
        "embeddings": prepare_embeddings,
        "ocr": prepare_ocr,
        "policy": prepare_policy,
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=stages)
    args = parser.parse_args(argv)

    if args.stage:
        stages[args.stage]()
        return

    for stage in stages:
        subprocess.run(
            [sys.executable, "-m", "scripts.prepare_runtime", "--stage", stage],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
