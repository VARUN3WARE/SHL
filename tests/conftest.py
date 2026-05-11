"""Keep CI/local tests fast: no embedding index file, no Gemini by default."""

from __future__ import annotations

import os

os.environ.setdefault("EMBEDDING_INDEX_PATH", "/tmp/shl_test_embeddings_missing.npz")
os.environ.setdefault("USE_GEMINI", "false")
os.environ.setdefault("USE_GROQ", "false")
