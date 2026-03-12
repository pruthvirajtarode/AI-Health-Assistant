import json
from typing import List, Dict


def load_diseases(path: str = "data/diseases.jsonl") -> List[Dict]:
    diseases = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    diseases.append(json.loads(line))
                except Exception:
                    # skip malformed lines
                    continue
    except FileNotFoundError:
        return []
    return diseases


def _text_to_terms(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower()
    # split on common delimiters; keep words of length >= 3
    tokens = [t.strip() for t in text.replace(",", " ").replace("/", " ").split()]
    return [t for t in tokens if len(t) >= 3]


def find_diseases_by_text(text: str, path: str = "data/diseases.jsonl", top_n: int = 5) -> List[Dict]:
    """Return top_n disease records ranked by simple overlap with hallmark symptoms and label/synonyms.

    This is a lightweight fallback matcher (no ML) intended for low-resource environments or
    when the main disease predictor is not available.
    """
    ds = load_diseases(path)
    if not ds:
        return []

    terms = set(_text_to_terms(text))
    scored = []
    for d in ds:
        score = 0
        hallmarks = {s.lower() for s in d.get("hallmark_symptoms", [])}
        # overlap with hallmark symptoms
        score += len(terms & hallmarks)
        label = d.get("label", "").lower()
        if any(t in label for t in terms):
            score += 1
        for syn in d.get("synonyms", []):
            syn_l = syn.lower()
            if any(t in syn_l for t in terms):
                score += 1
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_n]]


if __name__ == "__main__":
    # quick local test
    ds = find_diseases_by_text("fever fatigue")
    print(json.dumps(ds, indent=2, ensure_ascii=False))
