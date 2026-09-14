from qdrant_client import QdrantClient


COLLECTION_NAME = "motor_policy"
QDRANT_PATH = ".qdrant"


# One shared Qdrant client for the whole application.
qdrant_client = QdrantClient(
    path=QDRANT_PATH
)