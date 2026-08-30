"""Semantic layer over collected job postings, via Chroma + LangChain.

Same best-effort contract as llm_client.py: no GEMINI_API_KEY, no network, or
any Chroma/embedding failure should degrade to "no semantic signal" rather
than break the caller. The deterministic keyword score in job_matcher.py
(app/utils/skills.py-based) stays the authoritative match score either way —
this module only ever adds a secondary signal on top of it:

- semantic_scores(): a per-job cosine-similarity score used as a secondary
  "semantic match" alongside the keyword match_score, so a resume and a job
  that describe the same skill with different words (or a skill outside the
  fixed ~50-term vocabulary in app/utils/skills.py) still surface as related.
- similar_postings(): retrieval-augmented context for ats_scorer.py's Gemini
  narrative, so "missing_strengths"/"suggestions" can be grounded in actual
  collected postings instead of only the keyword list.
"""

import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_postings"
PERSIST_DIR = str(Path(__file__).resolve().parent.parent.parent / "chroma_data")
EMBEDDING_MODEL = "models/gemini-embedding-001"

# Descriptions are embedded and stored as-is; capping length here keeps
# embedding cost/latency bounded without needing a real chunking strategy —
# a job posting's first ~4000 chars comfortably covers title/requirements.
MAX_DOC_CHARS = 4000

_store = None
_store_initialized = False


def is_available() -> bool:
    return bool(settings.gemini_api_key)


def _get_store():
    global _store, _store_initialized
    if _store_initialized:
        return _store
    _store_initialized = True

    if not settings.gemini_api_key:
        return None

    try:
        from langchain_chroma import Chroma
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=settings.gemini_api_key)
        _store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
    except Exception:
        logger.warning("Chroma vector store unavailable, semantic layer disabled", exc_info=True)
        _store = None

    return _store


def index_jobs(jobs) -> None:
    """Upserts each job's description into Chroma. No-op (not an error) if the
    semantic layer is unavailable, or if none of the jobs have a description
    yet (e.g. LinkedIn rows before a description backfill)."""
    store = _get_store()
    if store is None:
        return

    ids, docs, metadatas = [], [], []
    for job in jobs:
        if not job.description:
            continue
        ids.append(f"job-{job.id}")
        docs.append(job.description[:MAX_DOC_CHARS])
        metadatas.append({"job_id": job.id, "title": job.title, "company": job.company or ""})

    if not ids:
        return

    try:
        store.add_texts(texts=docs, metadatas=metadatas, ids=ids)
    except Exception:
        logger.warning("Failed to index jobs into Chroma", exc_info=True)


def semantic_scores(resume_text: str, job_ids: list[int]) -> dict[int, float]:
    """Cosine-similarity score (0-100, higher = more similar) between resume_text
    and each job's indexed description, keyed by job_id. A job_id missing from
    the returned dict means "no signal" (not indexed yet, or the semantic layer
    is unavailable) — callers should treat that as None, never as 0."""
    store = _get_store()
    if store is None or not job_ids or not resume_text:
        return {}

    try:
        results = store.similarity_search_with_score(
            resume_text, k=len(job_ids), filter={"job_id": {"$in": job_ids}}
        )
    except Exception:
        logger.warning("Chroma semantic query failed", exc_info=True)
        return {}

    scores: dict[int, float] = {}
    for doc, distance in results:
        job_id = doc.metadata.get("job_id")
        if job_id is None:
            continue
        # Chroma's "hnsw:space": "cosine" distance is 1 - cosine_similarity.
        # Clamp to [0, 1] before converting to a 0-100 score: cosine_similarity
        # can go slightly negative for unrelated text, which we treat the same
        # as "no similarity" rather than a meaningful negative score.
        similarity = max(0.0, min(1.0, 1 - distance))
        scores[job_id] = round(similarity * 100, 1)
    return scores


def similar_postings(query_text: str, k: int = 3) -> list[dict]:
    """Top-k real collected postings semantically similar to query_text —
    used to ground LLM-written resume suggestions in actual market listings."""
    store = _get_store()
    if store is None or not query_text:
        return []

    try:
        results = store.similarity_search(query_text, k=k)
    except Exception:
        logger.warning("Chroma similarity search failed", exc_info=True)
        return []

    return [
        {
            "title": doc.metadata.get("title", ""),
            "company": doc.metadata.get("company", ""),
            "snippet": doc.page_content[:500],
        }
        for doc in results
    ]
