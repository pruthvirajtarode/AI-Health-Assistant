# src/triage.py
from typing import List, Dict, Any, Optional
import re

# Symptom keyword -> weight (higher = more dangerous)
_SYMPTOM_WEIGHTS = {
    "chest pain": 0.9,
    "shortness of breath": 0.9,
    "breathless": 0.9,
    "loss of consciousness": 0.9,
    "unconscious": 0.9,
    "severe bleeding": 0.9,
    "severe trauma": 0.9,
    "stroke": 0.9,
    "facial droop": 0.9,
    "slurred speech": 0.9,
    "sudden weakness": 0.9,
    "seizure": 0.85,
    "pregnancy complications": 0.85,
    "high fever": 0.6,
    "fever": 0.45,
    "dehydration": 0.5,
    "severe pain": 0.55,
    "abdominal pain": 0.5,
    "dizziness": 0.45,
    "headache": 0.35,
    "confusion": 0.55,
    "fast heart": 0.6,
    "palpitations": 0.55,
    "vomiting": 0.45,
    "bleeding": 0.7,
    "cough": 0.2,
    "sore throat": 0.15,
    "runny nose": 0.1,
    "fatigue": 0.1,
    "rash": 0.25,
    "back pain": 0.25,
    "joint pain": 0.25,
    "muscle pain": 0.2,
    "eye redness": 0.2
}

# Comorbidity keywords raising baseline risk
_COMORBIDITY_WEIGHTS = {
    "diabetes": 0.1,
    "hypertension": 0.08,
    "heart disease": 0.15,
    "lung disease": 0.15,
    "asthma": 0.12,
    "cancer": 0.15,
    "pregnant": 0.15,
    "immunocompromised": 0.18
}

def _normalize_text(text: str) -> str:
    return (text or "").lower().strip()

def _score_from_symptoms(text: str) -> Dict[str, Any]:
    txt = _normalize_text(text)
    score = 0.0
    reasons: List[str] = []

    # phrase matches
    for phrase, w in _SYMPTOM_WEIGHTS.items():
        if phrase in txt:
            score += w
            reasons.append(f"symptom: {phrase} (+{w:.2f})")

    # token-level partial matches (avoid double-counting)
    tokens = re.split(r"[^\w]+", txt)
    for token in tokens:
        if not token:
            continue
        for phrase, w in _SYMPTOM_WEIGHTS.items():
            if token == phrase or token in phrase.split():
                if phrase not in txt:
                    add = w * 0.25
                    score += add
                    reasons.append(f"partial symptom match: {token} (+{add:.2f})")

    return {"score": score, "reasons": reasons}

def _score_from_comorbidities(text: str) -> Dict[str, Any]:
    txt = _normalize_text(text)
    add = 0.0
    reasons: List[str] = []
    for com, w in _COMORBIDITY_WEIGHTS.items():
        if com in txt:
            add += w
            reasons.append(f"comorbidity: {com} (+{w:.2f})")
    return {"add": add, "reasons": reasons}

def assess(symptoms: str,
           age: Optional[int] = None,
           severity_label: Optional[str] = None,
           comorbidities_text: Optional[str] = None,
           meds_or_report_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Return triage dict:
      {
        "level": "LOW" | "MEDIUM" | "HIGH",
        "score": float (0..1),
        "reasons": [str, ...]
      }
    """
    base = _score_from_symptoms(symptoms)
    score = base["score"]
    reasons = base["reasons"]

    # comorbidities
    if comorbidities_text:
        c = _score_from_comorbidities(comorbidities_text)
    else:
        c = _score_from_comorbidities(symptoms)
    score += c["add"]
    reasons.extend(c["reasons"])

    # user severity
    sev = (severity_label or "").lower()
    if sev == "mild":
        score += 0.0
        reasons.append("self-reported severity: mild (+0.00)")
    elif sev == "moderate":
        score += 0.12
        reasons.append("self-reported severity: moderate (+0.12)")
    elif sev == "severe":
        score += 0.25
        reasons.append("self-reported severity: severe (+0.25)")

    # Age adjustments
    try:
        if age is not None:
            if age >= 65:
                score += 0.12
                reasons.append(f"age >=65 (+0.12)")
            elif age <= 12:
                score += 0.08
                reasons.append("age <=12 (+0.08)")
    except Exception:
        pass

    # Medication / reports
    if meds_or_report_text:
        txt = _normalize_text(meds_or_report_text)
        if any(x in txt for x in ["paracetamol", "acetaminophen", "ibuprofen", "antibiotic", "antibiotics", "prednisone", "steroid"]):
            score -= 0.08
            reasons.append("recent medication reported (reduces score slightly) (-0.08)")
        if any(x in txt for x in ["surgery", "hospitalized", "icu", "admitted"]):
            score += 0.15
            reasons.append("recent hospitalization / surgery (+0.15)")

    score = max(0.0, score)
    normalized = min(1.0, score / 2.0)

    if normalized >= 0.65:
        level = "HIGH"
    elif normalized >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "level": level,
        "score": round(normalized, 3),
        "reasons": reasons
    }

# Provide a compatibility wrapper named `simple_triage` so older code works.
def simple_triage(symptom_labels: List[str], premise_text: str = "") -> Dict[str, Any]:
    """
    Accepts symptom_labels (list of top symptom strings) and a premise_text (user full text).
    Returns the same structure as assess().
    This wrapper builds a combined text to feed into assess.
    """
    combined = " ".join(symptom_labels).strip()
    if not combined:
        combined = (premise_text or "").strip()
    return assess(combined, age=None)

# Human-readable mapping table
MAPPING_TABLE = [
    {"symptoms": ["chest pain", "shortness of breath", "breathless", "sudden weakness"], "priority": "HIGH",
     "advice": "Immediate medical care; call emergency services."},
    {"symptoms": ["severe bleeding", "seizure", "loss of consciousness"], "priority": "HIGH",
     "advice": "Immediate medical care; call emergency services."},
    {"symptoms": ["high fever", "confusion", "dehydration", "vomiting"], "priority": "MEDIUM",
     "advice": "Seek doctor within 24 hours; monitor closely."},
    {"symptoms": ["cough", "sore throat", "runny nose", "fatigue"], "priority": "LOW",
     "advice": "Home care; see doctor if worsens or persists."}
]
