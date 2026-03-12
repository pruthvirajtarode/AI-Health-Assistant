import os
import json
import faiss
import numpy as np

# ---------------------------------------------------
# Use SAME embedding function as pipeline.py
# Ensures FAISS dimension is identical (important!)
# ---------------------------------------------------
try:
    from pipeline import _embed
except ImportError:
    from src.pipeline import _embed

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data", "diseases.jsonl")
OUT = os.path.join(BASE, "models", "faiss_index_diseases.bin")

print("📌 Reading diseases.jsonl...")

diseases = []
texts = []

with open(DATA, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        diseases.append(obj)

        # What we embed:
        label = obj.get("label", "")
        desc = obj.get("description", "")
        text = f"{label}. {desc}".strip()
        texts.append(text)

print(f"📌 Found {len(texts)} diseases.")
if len(texts) == 0:
    raise ValueError("❌ ERROR: diseases.jsonl is empty!")

# ---------------------------------------------------
# Embed using SAME model as symptom pipeline
# ---------------------------------------------------
print("📌 Encoding diseases with shared embedder...")
emb = _embed(texts).astype("float32")

dim = emb.shape[1]
print(f"📌 Embedding dimension = {dim}")

# ---------------------------------------------------
# Build FAISS index
# ---------------------------------------------------
print("📌 Building FAISS index (Inner Product)...")
index = faiss.IndexFlatIP(dim)
index.add(emb)

# ---------------------------------------------------
# Save index
# ---------------------------------------------------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
faiss.write_index(index, OUT)

print("✅ SUCCESS: Disease FAISS index saved to ->", OUT)
