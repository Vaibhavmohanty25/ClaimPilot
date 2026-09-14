from pathlib import Path
from uuid import uuid4

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
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

        else:

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

    create_collection()

    policy_text = Path(
        file_path
    ).read_text(
        encoding="utf-8"
    )

    sections = split_policy_into_sections(
        policy_text
    )

    points = []

    for section in sections:

        vector = embed_text(
            section
        )

        point = PointStruct(
            id=str(uuid4()),

            vector=vector,

            payload={
                "text": section,
                "source": file_path,
            },
        )

        points.append(point)

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    return len(points)


if __name__ == "__main__":

    count = ingest_policy(
        "data/policies/motor_policy.txt"
    )

    print(
        f"Ingested {count} policy sections."
    )