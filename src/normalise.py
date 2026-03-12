# src/normalise.py
import re
import csv
import os
from unidecode import unidecode
from langdetect import detect
from transformers import pipeline

PHRASEBOOK = os.path.join(os.path.dirname(__file__), '..', 'data', 'phrasebook.csv')

def _load_phrasebook():
    mapping = []
    if os.path.exists(PHRASEBOOK):
        with open(PHRASEBOOK, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # protect against missing columns
                patt = row.get('pattern') if isinstance(row, dict) else None
                repl = row.get('replacement') if isinstance(row, dict) else None
                if patt and repl:
                    mapping.append((patt.strip(), repl.strip()))
    return mapping

_phrasebook_cache = None

def translate_if_needed(text: str) -> str:
    try:
        lang = detect(text)
        if lang != "en":
            # Use NLLB distilled model - note: heavy. In low-resource deployment, consider a lightweight translator or skip.
            translator = pipeline("translation", model="facebook/nllb-200-distilled-600M")
            translated = translator(text, src_lang=lang, tgt_lang="eng_Latn")[0]["translation_text"]
            return translated
        return text
    except Exception as e:
        print(f"[WARNING] Translation failed: {e}")
        return text

def normalize(text: str) -> str:
    """
    Normalize user input:
    - phrasebook replacements
    - ascii transliteration
    - collapse whitespace and repeated chars
    - translate if non-English and phrasebook doesn't match
    """
    global _phrasebook_cache
    if _phrasebook_cache is None:
        _phrasebook_cache = _load_phrasebook()

    # Basic guard
    if not isinstance(text, str):
        return ""

    # Only translate if language is not English and phrasebook doesn't cover it
    lang = None
    try:
        lang = detect(text)
    except Exception:
        lang = None

    t = text
    if lang and lang != "en":
        # Check if phrasebook has a direct match before translating
        found_in_phrasebook = False
        for patt, _ in _phrasebook_cache:
            try:
                if re.search(rf'\b{re.escape(patt)}\b', t, flags=re.IGNORECASE):
                    found_in_phrasebook = True
                    break
            except re.error:
                continue
        if not found_in_phrasebook:
            t = translate_if_needed(text)

    # Basic cleaning
    t_clean = t.strip()
    t_clean = t_clean.replace('\u200d', ' ')
    t_clean = re.sub(r'\s+', ' ', t_clean)
    # collapse very long repeats e.g., heyyyy -> heyy
    t_clean = re.sub(r'(.)\1{2,}', r'\1\1', t_clean, flags=re.IGNORECASE)
    t_ascii = unidecode(t_clean)

    # Phrasebook replacements
    def apply_map(s):
        s2 = s
        for patt, repl in _phrasebook_cache:
            try:
                s2 = re.sub(rf'\b{re.escape(patt)}\b', repl, s2, flags=re.IGNORECASE)
            except re.error:
                # if a phrasebook pattern contains regex meta, skip it safely
                continue
        return s2

    t_final = apply_map(t_clean)
    t_ascii_final = apply_map(t_ascii)

    return t_ascii_final if t_ascii_final != unidecode(text) else t_final
