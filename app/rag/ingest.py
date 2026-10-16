from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    HasIdCondition,
)

from app.rag.embeddings import embed_text
from app.rag.qdrant_store import (
    qdrant_client,
    COLLECTION_NAME,
)


def split_policy_into_sections(
    policy_text: str
) -> list[str]:
    sections = []
    current_section = []
    inside_section = False

    for line in policy_text.splitlines():
        stripped = line.strip()

        if stripped.startswith("SECTION "):

            if current_section:
                section = "\n".join(
                    current_section
                ).strip()

                if section:
                    sections.append(section)

            current_section = [
                stripped
            ]

            inside_section = True

        elif inside_section:
            current_section.append(
                line
            )

    if current_section:
        section = "\n".join(
            current_section
        ).strip()

        if section:
            sections.append(section)

    return sections


def create_collection():
    if qdrant_client.collection_exists(
        COLLECTION_NAME
    ):
        return

    test_vector = embed_text(
        "insurance policy"
    )

    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=len(test_vector),
            distance=Distance.COSINE,
        ),
    )


def ingest_policy(
    file_path: str
):
    print(
        f"Reading policy from: {file_path}"
    )

    policy_text = Path(
        file_path
    ).read_text(
        encoding="utf-8"
    )

    sections = split_policy_into_sections(
        policy_text
    )
    if not sections:
        raise ValueError("Policy must contain at least one SECTION header.")

    source_key = str(Path(file_path).resolve())

    print(
        f"Found {len(sections)} policy sections."
    )

    points = []

    for index, section in enumerate(
        sections
    ):
        print(
            f"Embedding section {index + 1}: "
            f"{section.splitlines()[0]}"
        )

        vector = embed_text(
            section
        )

        point = PointStruct(
            # Stable source-specific IDs support replacing the active policy
            # only after its complete replacement has been embedded.
            id=str(uuid5(NAMESPACE_URL, f"{source_key}#{index}")),

            vector=vector,

            payload={
                "text": section,
                "source": file_path,
            },
        )

        points.append(
            point
        )

    # Complete extraction and embedding before changing the index.
    create_collection()
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    # The application has one active policy and retrieval is not source-scoped.
    # Remove all previous policy sections, including legacy numeric-ID points,
    # so unrelated or obsolete clauses cannot enter coverage analysis.
    qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must_not=[HasIdCondition(has_id=[point.id for point in points])],
        ),
        wait=True,
    )

    print(
        "Qdrant upsert complete."
    )

    return len(points)


if __name__ == "__main__":
    print(
        "Starting ClaimPilot policy ingestion..."
    )

    count = ingest_policy(
        "data/policies/motor_policy.txt"
    )

    print(
        f"Ingested {count} policy sections successfully."
    )
