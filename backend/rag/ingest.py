"""
One-time (or on-demand) ingestion script: walks rag/knowledge_base/,
chunks each markdown/text file, and upserts embeddings into the correct
domain collection based on which subfolder it lives in (blood/, imaging/,
drug/). Run with:  python -m rag.ingest
Re-run any time you drop new WHO/NIH/textbook files into
rag/knowledge_base/<domain>/ — upsert makes it idempotent.
"""
import hashlib
from pathlib import Path

from core.config import get_settings
from rag.vector_store import add_documents, collection_count, DOMAIN_COLLECTIONS

settings = get_settings()


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return [c for c in chunks if c.strip()]


def ingest_knowledge_base():
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    total = 0

    for domain in DOMAIN_COLLECTIONS:
        domain_dir = kb_dir / domain
        if not domain_dir.exists():
            continue

        ids, texts, metas = [], [], []
        for path in domain_dir.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            for i, chunk in enumerate(chunk_text(content)):
                chunk_id = hashlib.sha1(f"{path}-{i}".encode()).hexdigest()
                ids.append(chunk_id)
                texts.append(chunk)
                metas.append({"source": path.stem.replace("_", " ").title(), "domain": domain})

        if ids:
            add_documents(domain, ids, texts, metas)
            total += len(ids)
        print(f"[{domain}] ingested {len(ids)} chunks -> {collection_count(domain)} vectors total.")

    print(f"Done. {total} chunks ingested this run.")


if __name__ == "__main__":
    ingest_knowledge_base()
