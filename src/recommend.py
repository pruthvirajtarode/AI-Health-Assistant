# src/recommend.py
import os
import json
from typing import List, Dict, Any, Optional

# Fuzzy matching
try:
    from rapidfuzz import process, fuzz
except Exception:
    process = None
    fuzz = None

ROOT = os.path.dirname(os.path.dirname(__file__))
# Use concepts_enriched.jsonl if you created that, else fall back to concepts.jsonl
CONCEPTS_PATHS = [
    os.path.join(ROOT, "data", "concepts_enriched.jsonl"),
    os.path.join(ROOT, "data", "concepts_mapped.jsonl"),
    os.path.join(ROOT, "data", "concepts.jsonl")
]

_CONCEPTS: Optional[List[Dict[str, Any]]] = None
_PHRASE_TO_IDX: Optional[Dict[str, int]] = None

def _load_concepts() -> List[Dict[str, Any]]:
    global _CONCEPTS, _PHRASE_TO_IDX
    if _CONCEPTS is None:
        for p in CONCEPTS_PATHS:
            if os.path.exists(p):
                path = p
                break
        else:
            raise FileNotFoundError("No concepts file found. Expected one of: " + ", ".join(CONCEPTS_PATHS))
        _CONCEPTS = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    _CONCEPTS.append(json.loads(line))
        # build phrase map for fuzzy matching
        _PHRASE_TO_IDX = {}
        for idx, c in enumerate(_CONCEPTS):
            label = (c.get("label") or "").strip().lower()
            if label:
                _PHRASE_TO_IDX[label] = idx
            syns = c.get("synonyms", []) or []
            if isinstance(syns, str):
                syns = [s.strip() for s in syns.split("|") if s.strip()]
            for s in syns:
                s2 = (s or "").strip().lower()
                if s2:
                    _PHRASE_TO_IDX[s2] = idx
    return _CONCEPTS

def _best_fuzzy_match(label: str, score_cutoff: int = 70) -> Optional[Dict[str, Any]]:
    """
    Use rapidfuzz to match a label/sentence to the closest concept phrase (label or synonym).
    Returns the concept dict if match score >= cutoff, else None.
    """
    if process is None or _PHRASE_TO_IDX is None:
        return None
    choices = list(_PHRASE_TO_IDX.keys())
    # process.extractOne returns (match, score, index)
    try:
        match = process.extractOne(label.lower(), choices, scorer=fuzz.partial_ratio)
    except Exception:
        return None
    if not match:
        return None
    matched_phrase, score, _ = match
    if score >= score_cutoff:
        idx = _PHRASE_TO_IDX.get(matched_phrase)
        if idx is not None:
            concepts = _load_concepts()
            return concepts[idx]
    return None

def get_concept_by_label(label: str) -> Optional[Dict[str, Any]]:
    """
    Try exact label/id match -> exact synonym -> fuzzy match (partial ratio).
    This makes recommend functions robust to slightly different phrasing.
    """
    if not label:
        return None
    label_l = label.strip().lower()
    concepts = _load_concepts()
    # exact match on label or id
    for c in concepts:
        if (c.get("label","").strip().lower() == label_l) or (c.get("id","").strip().lower() == label_l):
            return c
    # exact match on synonyms
    for c in concepts:
        syns = c.get("synonyms", []) or []
        if isinstance(syns, str):
            syns = [s.strip() for s in syns.split("|") if s.strip()]
        for s in syns:
            if s and s.strip().lower() == label_l:
                return c
    # fuzzy fallback
    c_fuzzy = _best_fuzzy_match(label, score_cutoff=70)
    if c_fuzzy:
        return c_fuzzy
    return None

def recommend_specialists(label: str) -> List[str]:
    c = get_concept_by_label(label)
    if not c:
        return []
    return c.get("specialists", []) or []

def recommend_tests(label: str) -> List[Dict[str, Any]]:
    c = get_concept_by_label(label)
    if not c:
        return []
    return c.get("recommended_tests", []) or []
