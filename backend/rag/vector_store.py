"""
ChromaDB persistent vector store wrapper — one collection per medical
domain (Blood RAG / Imaging RAG / Drug RAG), matching the domain-specific
agents. Each agent only ever queries its own collection, which keeps
retrieval precise (a lab-value query won't accidentally surface drug
side-effect text, etc).

Uses Chroma's built-in sentence-transformer embedding function by
default so the project runs with zero external embedding API calls.
Swap `embedding_functions.OpenAIEmbeddingFunction` etc. in here if you'd
rather use a hosted embedder in production.
"""
import chromadb
from chromadb.utils import embedding_functions
from core.config import get_settings

settings = get_settings()

_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
_embedder = embedding_functions.DefaultEmbeddingFunction()

# Domain -> collection name. Keep these in sync with the subfolders under
# rag/knowledge_base/ (blood/, imaging/, drug/).
DOMAIN_COLLECTIONS = {
    "blood": "blood_knowledge",
    "imaging": "imaging_knowledge",
    "drug": "drug_knowledge",
}


def get_collection(domain: str):
    name = DOMAIN_COLLECTIONS.get(domain)
    if not name:
        raise ValueError(f"Unknown RAG domain: {domain}. Expected one of {list(DOMAIN_COLLECTIONS)}")
    return _client.get_or_create_collection(
        name=name,
        embedding_function=_embedder,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(domain: str, ids: list[str], texts: list[str], metadatas: list[dict]):
    collection = get_collection(domain)
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)


def query(domain: str, text: str, top_k: int = 5):
    collection = get_collection(domain)
    return collection.query(query_texts=[text], n_results=top_k)


def collection_count(domain: str) -> int:
    return get_collection(domain).count()


def all_domains_populated() -> bool:
    return all(collection_count(d) > 0 for d in DOMAIN_COLLECTIONS)
