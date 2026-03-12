import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(__file__)
CONCEPTS = os.path.join(ROOT, "data", "concepts.jsonl")
OUT = os.path.join(ROOT, "models", "faiss_index.bin")

MODEL = "intfloat/multilingual-e5-base"

print("📌 Loading model:", MODEL)
model = SentenceTransformer(MODEL)

texts = []
with open(CONCEPTS, "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        label = obj["label"]
        desc = obj.get("description", "")
        texts.append(label + ". " + desc)

print("📌 Encoding", len(texts), "concepts…")
emb = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).astype("float32")

dim = emb.shape[1]
print("📌 Embedding dim =", dim)

index = faiss.IndexFlatIP(dim)
index.add(emb)

faiss.write_index(index, OUT)
print("✅ SUCCESS: Saved index to", OUT)
