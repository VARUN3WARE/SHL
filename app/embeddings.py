from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from app.config import embedding_index_path, embedding_model_name

logger = logging.getLogger(__name__)

_MAX_CHARS = 2000


def catalog_item_embed_text(name: str, description: str | None, job_levels: list[str], languages: list[str], test_type: str) -> str:
    parts = [name, f"test_type={test_type}"]
    if description:
        parts.append(description[:1500])
    if job_levels:
        parts.append("job_levels: " + ", ".join(job_levels[:20]))
    if languages:
        parts.append("languages: " + ", ".join(languages[:20]))
    t = " ".join(parts)
    return t[:_MAX_CHARS]


@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer

    name = embedding_model_name()
    logger.info("Loading embedding model %s", name)
    return SentenceTransformer(name)


@lru_cache(maxsize=1)
def _index_arrays() -> tuple[np.ndarray, list[str]] | None:
    path = embedding_index_path()
    if not path.is_file():
        logger.warning("Embedding index not found at %s — semantic retrieval disabled", path)
        return None
    try:
        data = np.load(path, allow_pickle=True)
        emb = np.asarray(data["embeddings"], dtype=np.float32)
        urls = [str(u) for u in np.asarray(data["urls"], dtype=object).tolist()]
        if emb.shape[0] == 0:
            return None
        if emb.shape[0] != len(urls):
            logger.error("Embedding index shape mismatch: %s rows vs %s urls", emb.shape[0], len(urls))
            return None
        # L2-normalize rows for cosine via dot product
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        emb = emb / norms
        return emb, urls
    except Exception:
        logger.exception("Failed to load embedding index from %s", path)
        return None


def encode_query_text(text: str) -> np.ndarray | None:
    if not text.strip():
        return None
    try:
        model = _encoder()
        v = model.encode(
            text[:_MAX_CHARS],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(v, dtype=np.float32).reshape(-1)
    except Exception:
        logger.exception("Query embedding failed")
        return None


def semantic_top_urls(query_text: str, k: int = 40) -> dict[str, float]:
    """
    Return mapping catalog URL -> cosine similarity [0,1] for top-k items.
    Empty if index/model unavailable.
    """
    idx = _index_arrays()
    if idx is None:
        return {}
    emb, urls = idx
    q = encode_query_text(query_text)
    if q is None:
        return {}
    sims = emb @ q
    k = max(1, min(k, len(sims)))
    top = np.argpartition(-sims, k - 1)[:k]
    top = top[np.argsort(-sims[top])]
    return {urls[int(i)]: float(sims[int(i)]) for i in top}
