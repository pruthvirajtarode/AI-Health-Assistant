# src/pipeline_disease.py

import os
import json
import faiss
import numpy as np

# 🔁 Reuse the SAME embedding function as pipeline.py
#    so FAISS dimension always matches and no second big model loads.
try:
    from pipeline import _embed
except ImportError:
    from src.pipeline import _embed

BASE = os.path.dirname(os.path.dirname(__file__))
DISEASE_FILE = os.path.join(BASE, "data", "diseases.jsonl")
INDEX_FILE = os.path.join(BASE, "models", "faiss_index_diseases.bin")

print("🔍 Loading diseases dataset...")
diseases = []
with open(DISEASE_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        diseases.append(json.loads(line))

print(f"📌 Loaded {len(diseases)} diseases.")

print("🔍 Loading disease FAISS index...")
index = faiss.read_index(INDEX_FILE)
dim = index.d
print(f"📌 Disease index dim = {dim}")


def predict_disease(text: str, top_k: int = 5):
    """
    Given free-text symptoms, return top-k matching diseases.
    Uses same encoder as src/pipeline.py (intfloat/multilingual-e5-base).
    """
    text = (text or "").strip()
    if not text:
        return {"input": text, "predictions": []}

    # Embed using SAME model as concepts index
    qv = _embed([text]).astype("float32")
    scores, ids = index.search(qv, top_k)

    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0 or idx >= len(diseases):
            continue
        d = diseases[idx]
        results.append({
            "label": d.get("label", ""),
            "description": d.get("description", ""),
            "score": float(score),
            "system": d.get("system", ""),
            "specialists": d.get("specialists", []),
            "recommended_tests": d.get("recommended_tests", []),
        })

    return {
        "input": text,
        "predictions": results
    }


if __name__ == "__main__":
    # Simple CLI test:
    import argparse, json as _json
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", type=str, required=True)
    ap.add_argument("--topk", type=int, default=5)
    args = ap.parse_args()

    out = predict_disease(args.text, top_k=args.topk)
    print(_json.dumps(out, ensure_ascii=False, indent=2))
