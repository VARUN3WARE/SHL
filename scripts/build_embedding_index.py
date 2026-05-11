#!/usr/bin/env python3
"""
Precompute L2-normalized embeddings for each catalog row (same order as load_catalog).

Usage:
  python scripts/build_embedding_index.py
  python scripts/build_embedding_index.py --out data/catalog_embeddings.npz
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.catalog import load_catalog  # noqa: E402
from app.config import DATA_DIR, embedding_index_path, embedding_model_name  # noqa: E402
from app.embeddings import catalog_item_embed_text  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output .npz path (default: EMBEDDING_INDEX_PATH or data/catalog_embeddings.npz)",
    )
    args = p.parse_args()
    out = (args.out or embedding_index_path()).expanduser().resolve()

    catalog = load_catalog()
    if catalog.is_empty:
        print("Catalog empty — writing empty index.", file=sys.stderr)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out, embeddings=np.zeros((0, 384), dtype=np.float32), urls=np.array([], dtype=object))
        print(f"Wrote empty index to {out}")
        return

    from sentence_transformers import SentenceTransformer

    model_name = embedding_model_name()
    print(f"Loading model {model_name}...")
    model = SentenceTransformer(model_name)

    texts = [
        catalog_item_embed_text(
            it.name,
            it.description,
            it.job_levels,
            it.languages,
            it.test_type,
        )
        for it in catalog.items
    ]
    urls = [str(it.url) for it in catalog.items]

    print(f"Encoding {len(texts)} items...")
    emb = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    emb = np.asarray(emb, dtype=np.float32)

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, embeddings=emb, urls=np.array(urls, dtype=object))
    print(f"Wrote {emb.shape[0]} x {emb.shape[1]} to {out}")


if __name__ == "__main__":
    main()
