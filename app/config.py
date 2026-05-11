"""Environment-driven settings. Load via `load_dotenv()` before importing app modules that read os.environ."""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in {"1", "true", "yes", "y", "on"}


def gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()


def gemini_timeout_s() -> float:
    try:
        return float(os.environ.get("GEMINI_TIMEOUT_S", "8").strip())
    except ValueError:
        return 8.0


def use_gemini() -> bool:
    if _bool_env("USE_GEMINI", True) is False:
        return False
    return bool(gemini_api_key())


def embedding_model_name() -> str:
    return os.environ.get(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    ).strip()


def embedding_index_path() -> Path:
    p = os.environ.get("EMBEDDING_INDEX_PATH", "").strip()
    if p:
        return Path(p).expanduser().resolve()
    return (DATA_DIR / "catalog_embeddings.npz").resolve()


def hybrid_weight_semantic() -> float:
    try:
        return float(os.environ.get("HYBRID_W_SEM", "0.55").strip())
    except ValueError:
        return 0.55


def hybrid_weight_lexical() -> float:
    try:
        return float(os.environ.get("HYBRID_W_LEX", "0.45").strip())
    except ValueError:
        return 0.45
