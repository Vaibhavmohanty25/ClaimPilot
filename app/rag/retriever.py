from app.rag.embeddings import embed_text

from app.rag.qdrant_store import (
    qdrant_client,
    COLLECTION_NAME,
)


def retrieve_policy_context(
    query: str,
    limit: int = 4,
) -> list[dict]:

    query_vector = embed_text(
        query
    )

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
    )

    contexts = []

    for point in results.points:

        contexts.append(
            {
                "text":
                    point.payload.get(
                        "text",
                        ""
                    ),

                "source":
                    point.payload.get(
                        "source",
                        ""
                    ),

                "score":
                    point.score,
            }
        )

    return contexts