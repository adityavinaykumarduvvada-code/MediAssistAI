"""
Domain-scoped retrieval helpers. Every domain agent (Blood/Imaging/Drug)
and the Clinical Reasoning Agent call through here rather than touching
ChromaDB directly, so retrieval logic stays in one place.
"""
from rag.vector_store import query as vector_query
from core.config import get_settings

settings = get_settings()


def retrieve(domain: str, query_text: str, top_k: int | None = None) -> list[dict]:
    """Return top-k relevant knowledge chunks from a single domain's RAG collection."""
    top_k = top_k or settings.RAG_TOP_K
    result = vector_query(domain, query_text, top_k=top_k)

    chunks = []
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        chunks.append({
            "domain": domain,
            "source": meta.get("source", "unknown"),
            "text": doc,
            "score": round(1 - dist, 4),  # cosine distance -> similarity
        })
    return chunks


def retrieve_for_topics(domain: str, topics: list[str], top_k_each: int = 2) -> list[dict]:
    """Run multiple retrieval queries (one per finding/medicine/etc.) within one
    domain and merge, deduped. Used by domain agents to ground their own output,
    and by the Clinical Reasoning Agent to pull cross-domain context."""
    seen = set()
    merged = []
    for topic in topics:
        for chunk in retrieve(domain, topic, top_k=top_k_each):
            key = (chunk["source"], chunk["text"][:80])
            if key not in seen:
                seen.add(key)
                merged.append(chunk)
    return merged


def retrieve_across_domains(topics_by_domain: dict[str, list[str]], top_k_each: int = 2) -> list[dict]:
    """Retrieve from multiple domains at once — used by the Clinical Reasoning
    Agent, which needs Blood + Imaging + Drug context together."""
    merged = []
    for domain, topics in topics_by_domain.items():
        if topics:
            merged += retrieve_for_topics(domain, topics, top_k_each=top_k_each)
    return merged
