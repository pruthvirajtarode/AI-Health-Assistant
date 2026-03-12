# server.py (updated)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict
import uvicorn
import os
import sys
import traceback
import logging
from deep_translator import GoogleTranslator

# Use a highly-available mirror for downloading HuggingFace models, bypassing local connection issues
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")

# Fix path so pipeline/triage can be imported from src/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ----------------------------
# Import symptom pipeline (safe)
# ----------------------------
infer = None
pipeline_error = None
try:
    # try direct import first
    from pipeline import infer as _infer
    infer = _infer
    log.info("Imported pipeline.infer from project root.")
except Exception:
    try:
        # try from src
        from src.pipeline import infer as _infer
        infer = _infer
        log.info("Imported src.pipeline.infer.")
    except Exception as e:
        pipeline_error = f"Failed to import pipeline.infer: {e}"
        log.warning(pipeline_error)
        log.debug(traceback.format_exc())

# If import failed, provide a safe fallback infer() so server doesn't crash
if infer is None:
    def infer(text: str) -> Dict[str, Any]:
        """
        Fallback dummy pipeline. Returns minimal structure so frontend can still work.
        Real pipeline import failed — see /health or pipeline_error in responses.
        """
        return {
            "normalized_text": text,
            "predictions": [],
            "triage": {},
            "pipeline_error": pipeline_error or "pipeline not available"
        }

# ----------------------------
# Import triage (safe)
# ----------------------------
triage_assess = None
MAPPING_TABLE = []

# optional disease predictor
disease_predict = None
try:
    from pipeline_disease import predict_disease as _predict_disease
    disease_predict = _predict_disease
    log.info("Imported pipeline_disease.predict_disease from project root.")
except Exception:
    try:
        from src.pipeline_disease import predict_disease as _predict_disease
        disease_predict = _predict_disease
        log.info("Imported src.pipeline_disease.predict_disease.")
    except Exception as e:
        log.warning(f"Failed to import pipeline_disease.predict_disease: {e}")
        log.debug(traceback.format_exc())
try:
    from triage import assess as _assess, MAPPING_TABLE as _map
    triage_assess = _assess
    MAPPING_TABLE = _map
    log.info("Imported triage.assess from project root.")
except Exception:
    try:
        from src.triage import assess as _assess, MAPPING_TABLE as _map
        triage_assess = _assess
        MAPPING_TABLE = _map
        log.info("Imported src.triage.assess.")
    except Exception as e:
        log.warning(f"Failed to import triage.assess: {e}")
        log.debug(traceback.format_exc())
        # fallback simple assessor
        def triage_assess(symptoms: str, age: Optional[int] = None, severity_label: Optional[str] = None,
                          comorbidities_text: Optional[str] = None, meds_or_report_text: Optional[str] = None):
            # very simple heuristic fallback
            s = (symptoms or "").lower()
            level = "LOW"
            score = 0.0
            reasons = []
            if any(x in s for x in ["chest pain", "shortness of breath", "breathless", "loss of consciousness", "severe bleeding"]):
                level = "HIGH"; score = 0.9; reasons.append("critical symptom matched")
            elif any(x in s for x in ["high fever", "confusion", "seizure"]):
                level = "MEDIUM"; score = 0.5; reasons.append("warning symptom matched")
            else:
                level = "LOW"; score = 0.1; reasons.append("no red-flag symptoms")
            return {"level": level, "score": score, "reasons": reasons}
        MAPPING_TABLE = [
            {"symptoms": ["chest pain", "shortness of breath"], "priority": "HIGH", "advice": "Seek emergency care."},
            {"symptoms": ["fever", "confusion"], "priority": "MEDIUM", "advice": "See doctor soon."},
            {"symptoms": ["cough", "sore throat"], "priority": "LOW", "advice": "Home care / GP if persists."}
        ]

# ----------------------------
# FastAPI server
# ----------------------------
app = FastAPI(title="AI Health Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictRequest(BaseModel):
    symptoms: str
    age: Optional[int] = None
    gender: Optional[str] = None
    severity: Optional[str] = None  # mild|moderate|severe
    comorbidities: Optional[str] = None
    meds_or_reports: Optional[str] = None
    prior_doctor: Optional[str] = None
    lang: Optional[str] = "en"

class TranslateRequest(BaseModel):
    texts: list[str]
    lang: str

@app.post("/translate")
def translate_endpoint(req: TranslateRequest):
    if not req.texts: return {"translations": []}
    if req.lang == "en": return {"translations": req.texts}
    try:
        translator = GoogleTranslator(source='auto', target=req.lang)
        def translate_text(t: str) -> str:
            if not t or not isinstance(t, str): return t
            try: return translator.translate(t)
            except: return t
            
        try:
            res = translator.translate_batch(req.texts)
        except Exception as e:
            res = [translate_text(t) for t in req.texts]
        return {"translations": res}
    except Exception as e:
        log.error("translation endpoint failed: %s", e)
        return {"translations": req.texts}

@app.get("/health")
def health():
    """
    Small health endpoint to check what components are available.
    """
    return {
        "ok": True,
        "pipeline_loaded": False if pipeline_error else True,
        "pipeline_error": pipeline_error,
        "triage_loaded": triage_assess is not None,
    }

@app.get("/")
def root():
    return {"message": "AI Health Assistant Backend Running!"}

@app.post("/predict")
def predict(req: PredictRequest):
    symptoms = (req.symptoms or "").strip()
    if not symptoms:
        return {"error": "Symptoms required"}

    # 1) symptom-level predictions
    try:
        base = infer(symptoms)
    except Exception as e:
        log.error("Pipeline infer() raised exception: %s", e)
        log.debug(traceback.format_exc())
        base = {"predictions": [], "normalized_text": symptoms, "triage": {}}
        base["pipeline_error"] = str(e)

    # 2) disease-level predictions: some projects provide these inside pipeline
    # 2) disease-level predictions: try to call disease predictor if available
    try:
        if disease_predict is not None:
            dp = disease_predict(symptoms)
            if isinstance(dp, dict):
                base["diseases"] = dp.get("predictions", [])
            else:
                base["diseases"] = []
        else:
            if "diseases" not in base:
                base["diseases"] = []
    except Exception as e:
        log.error("disease_predict raised exception: %s", e)
        log.debug(traceback.format_exc())
        base["diseases"] = []

    # If no disease predictions from the model, try a lightweight dataset lookup fallback
    try:
        if not base.get("diseases"):
            try:
                from src.disease_lookup import find_diseases_by_text
            except Exception:
                try:
                    from disease_lookup import find_diseases_by_text
                except Exception:
                    find_diseases_by_text = None

            if find_diseases_by_text:
                fallback = find_diseases_by_text(symptoms, path=os.path.join(BASE_DIR, "data", "diseases.jsonl"), top_n=6)
                # normalize structure to expected format (list of dicts)
                base["diseases"] = fallback
                base["diseases_source"] = "fallback_lookup"
    except Exception as e:
        log.error("disease lookup fallback failed: %s", e)
        log.debug(traceback.format_exc())

    # 3) triage assessment (improved)
    try:
        tri = triage_assess(symptoms,
                            age=req.age,
                            severity_label=(req.severity or ""),
                            comorbidities_text=(req.comorbidities or ""),
                            meds_or_report_text=(req.meds_or_reports or ""))
    except Exception as e:
        log.error("triage_assess raised exception: %s", e)
        log.debug(traceback.format_exc())
        tri = {"level": "LOW", "score": 0.0, "reasons": [f"triage_error: {e}"]}

    base["triage"] = tri
    base["triage_mapping"] = MAPPING_TABLE

    # echo back user meta for frontend
    base["user_meta"] = {
        "age": req.age,
        "gender": req.gender,
        "severity": req.severity,
        "prior_doctor": req.prior_doctor
    }

    # include pipeline import error if present
    if pipeline_error:
        base["pipeline_error_import"] = pipeline_error

    # --- translation ---
    target_lang = getattr(req, "lang", "en")
    if target_lang and target_lang != "en":
        try:
            # handle mapping like 'hi' -> 'hi', 'mr' -> 'mr'
            translator = GoogleTranslator(source='auto', target=target_lang)
            def translate_text(text: str) -> str:
                if not text or not isinstance(text, str): return text
                try: return translator.translate(text)
                except: return text

            def translate_list(lst: list) -> list:
                if not lst: return lst
                # try batch, fallback to individual
                try: 
                    return translator.translate_batch(lst)
                except: 
                    return [translate_text(x) for x in lst]

            # Translate predictions
            for p in base.get("predictions", []):
                if "label" in p: p["label"] = translate_text(p["label"])
                if "desc" in p: p["desc"] = translate_text(p["desc"])
                if "specialists" in p and isinstance(p["specialists"], list):
                    p["specialists"] = translate_list(p["specialists"])
                if "recommended_tests" in p and isinstance(p["recommended_tests"], list):
                    p["recommended_tests"] = translate_list(p["recommended_tests"])
            
            # Translate diseases
            for d in base.get("diseases", []):
                if "label" in d: d["label"] = translate_text(d["label"])
                if "desc" in d: d["desc"] = translate_text(d["desc"])
                if "description" in d: d["description"] = translate_text(d["description"])
                if "specialists" in d and isinstance(d["specialists"], list):
                    d["specialists"] = translate_list(d["specialists"])
                if "recommended_tests" in d and isinstance(d["recommended_tests"], list):
                    d["recommended_tests"] = translate_list(d["recommended_tests"])

            # Translate triage reasons
            if "triage" in base and isinstance(base["triage"], dict):
                t = base["triage"]
                if "reasons" in t and isinstance(t["reasons"], list):
                    t["reasons"] = translate_list(t["reasons"])
                    
        except Exception as e:
            log.error("Translation error: %s", e)

    return base

if __name__ == "__main__":
    # Get port from environment variable (assigned by Render/Railway)
    port = int(os.environ.get("PORT", 8000))
    # Run without the auto-reloader to avoid mid-request restarts
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
