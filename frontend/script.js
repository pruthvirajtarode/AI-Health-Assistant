// -------------------------------
// script.js - Updated frontend logic (full file)
// -------------------------------

/* --------- Config --------- */
// Auto-detect environment: use local if on localhost, otherwise placeholder (user will update)
const IS_LOCAL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const BACKEND_BASE = IS_LOCAL ? "http://127.0.0.1:8000" : "https://ai-health-assistant-rry0.onrender.com";

const BACKEND_JSON_URL = `${BACKEND_BASE}/predict`;
const BACKEND_GET_URL = `${BACKEND_BASE}/predict`;
const OVERPASS_API = "https://overpass-api.de/api/interpreter";
const NEARBY_RADIUS = 5000; // meters
const MAX_DOCTORS = 10;

let recognition = null;
let recording = false;
let userLocation = null;
let lang = "en";

/* --------- i18n --------- */
const L = {
    en: {
        tip_loc: "Tip: Allow location access to find nearby doctors. Uses free OpenStreetMap data.",
        analyzing: "⏳ Analyzing…",
        no_input: "⚠ Please enter symptoms!",
        server_err: "❌ Server Error:",
        network_err: "❌ Network Error:",
        no_predictions: "No disease found. Try adding more details.",
        nearby_title: "Nearby doctors (from OpenStreetMap)",
        loc_denied: "Location access denied or unavailable. Doctor search disabled.",
        voice_on: "🔴 Listening... click to stop",
        voice_off: "🎤 Speak",
        triage_REASONS: "Triage reasons"
    },
    hi: {
        tip_loc: "टिप: पास के डॉक्टर खोजने के लिए लोकेशन की अनुमति दें। (OpenStreetMap का उपयोग करता है)",
        analyzing: "⏳ विश्लेषण किया जा रहा है…",
        no_input: "⚠ कृपया लक्षण दर्ज करें!",
        server_err: "❌ सर्वर त्रुटि:",
        network_err: "❌ नेटवर्क त्रुटि:",
        no_predictions: "कोई बीमारी नहीं मिली। और विवरण देने की कोशिश करें।",
        nearby_title: "पास के डॉक्टर (OpenStreetMap से)",
        loc_denied: "लोकेशन अनुमति अस्वीकृत। डॉक्टर खोज अक्षम।",
        voice_on: "🔴 सुन रहा है... रोकने के लिए क्लिक करें",
        voice_off: "🎤 बोलें",
        triage_REASONS: "ट्रायज कारण"
    },
    mr: {
        tip_loc: "टीप: जवळील डॉक्टर शोधण्यासाठी स्थान प्रवेश द्या. (OpenStreetMap वापरते)",
        analyzing: "⏳ विश्लेषण चालू आहे…",
        no_input: "⚠ कृपया लक्षणे प्रविष्ट करा!",
        server_err: "❌ सर्व्हर त्रुटी:",
        network_err: "❌ नेटवर्क त्रुटी:",
        no_predictions: "कोणतीही आजार सापडली नाही. अधिक तपशील देऊन प्रयत्न करा.",
        nearby_title: "जवळील डॉक्टर (OpenStreetMap द्वारे)",
        loc_denied: "स्थान प्रवेश नाकारला. डॉक्टर शोध अक्षम.",
        voice_on: "🔴 ऐकत आहे... थांबवण्यासाठी क्लिक करा",
        voice_off: "🎤 बोला",
        triage_REASONS: "त्रायज कारणे"
    }
};

function t(key) {
    return (L[lang] && L[lang][key]) ? L[lang][key] : L["en"][key];
}

// Helper: find an element by a list of possible ids (fallbacks)
function getElByIds(ids) {
    for (let id of ids) {
        const el = document.getElementById(id);
        if (el) return el;
    }
    return null;
}

// Better: prefer input/textarea elements and return inner inputs when passed a container
function getInputElByIds(ids) {
    for (let id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        const tag = (el.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || typeof el.value !== 'undefined') return el;
        // try to find an input/textarea inside the container
        if (el.querySelector) {
            const inner = el.querySelector('textarea, input');
            if (inner) return inner;
        }
        // fallback to element itself
        return el;
    }
    return null;
}

let _origTextsSaved = false;
let _origMap = new Map();

async function changeLanguage() {
    lang = document.getElementById("langSelect") ? document.getElementById("langSelect").value : "en";

    const selectors = [
        'h1', 'h2', 'h3', 'h4', '.subtitle', '.feature p', '.hero-link-primary', '.hero-link-secondary',
        'label', 'button', '.small-note', '.upload-text', '.upload-hint', '.about-tagline',
        '.about-feature-card p', '.tech-badge', '.disclaimer-icon + h4', '.about-disclaimer p',
        '#nearbyTitle', '.doctors-list p'
    ];

    const elements = document.querySelectorAll(selectors.join(', '));
    const inputs = document.querySelectorAll('input[placeholder], textarea[placeholder]');

    if (!_origTextsSaved) {
        elements.forEach(el => {
            if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {
                _origMap.set(el, el.innerText.trim());
            } else if (el.children.length === 0) {
                _origMap.set(el, el.innerText.trim());
            }
        });
        inputs.forEach(el => {
            if (el.placeholder) _origMap.set(el, el.placeholder.trim());
        });
        _origTextsSaved = true;
    }

    let toTranslate = [];
    let elsToUpdate = [];

    elements.forEach(el => {
        if (_origMap.has(el) && _origMap.get(el) !== "") {
            toTranslate.push(_origMap.get(el));
            elsToUpdate.push(el);
        }
    });
    inputs.forEach(el => {
        if (_origMap.has(el) && _origMap.get(el) !== "") {
            toTranslate.push(_origMap.get(el));
            elsToUpdate.push(el);
        }
    });

    if (lang === "en") {
        elsToUpdate.forEach((el, i) => {
            const txt = toTranslate[i];
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = txt;
            else el.innerText = txt;
        });
        if (document.getElementById("status")) document.getElementById("status").innerText = "";
        return;
    }

    if (document.getElementById("status")) document.getElementById("status").innerText = "Translating interface (Please wait 5-10 seconds)...";

    try {
        let res = await fetch(`${BACKEND_BASE}/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ texts: toTranslate, lang: lang })
        });
        let data = await res.json();
        if (data.translations) {
            if (data.translations.length !== elsToUpdate.length) {
                console.warn("Translation mismatch. Requested:", elsToUpdate.length, "Received:", data.translations.length);
            }
            elsToUpdate.forEach((el, i) => {
                const txt = data.translations[i] || toTranslate[i];
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = txt;
                else el.innerText = txt;
            });
        }
    } catch (e) {
        console.error("Translation request failed", e);
    }

    if (document.getElementById("status")) document.getElementById("status").innerText = "";
    if (document.getElementById("voiceBtn")) document.getElementById("voiceBtn").innerText = t("voice_off");
}

/* --------- Voice recognition (toggle) --------- */
function toggleVoice() {
    if (!('SpeechRecognition' in window) && !('webkitSpeechRecognition' in window)) {
        alert("Speech Recognition not supported in this browser. Use Chrome on desktop or Android.");
        return;
    }
    if (recording) {
        recognition.stop();
        return;
    }
    startVoice();
}

function startVoice() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
        alert("Speech Recognition not supported right now.");
        return;
    }
    recognition = new Speech();
    recognition.lang = (lang === "en") ? "en-IN" : (lang === "hi" ? "hi-IN" : "mr-IN");
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        recording = true;
        const vb = document.getElementById("voiceBtn");
        if (vb) vb.innerText = t("voice_on");
        setStatus(t("analyzing"));
    };

    recognition.onresult = (ev) => {
        const text = ev.results[0][0].transcript;
        const ta = getInputElByIds(["symptomsText", "symptoms"]);
        if (ta) ta.value = text;
    };

    recognition.onerror = (ev) => {
        console.warn("Voice error", ev);
        setStatus(t("network_err") + " " + (ev.error || ""), true);
    };

    recognition.onend = () => {
        recording = false;
        const vb = document.getElementById("voiceBtn");
        if (vb) vb.innerText = t("voice_off");
        setStatus("");
    };

    recognition.start();
}

/* --------- status helper --------- */
function setStatus(msg, isError = false) {
    const s = document.getElementById("status");
    if (!s) return;
    s.innerText = msg || "";
    s.style.color = isError ? "#d9534f" : "rgba(34,34,34,0.85)";
}

/* --------- Build request metadata (if present inputs exist) --------- */
function collectMeta() {
    // flexible lookup for ids changed in UI; returns first non-empty value
    const getVal = (candidates) => {
        for (let id of candidates) {
            const el = document.getElementById(id);
            if (!el) continue;
            const v = (el.value || "").toString().trim();
            if (v) return v;
        }
        return null;
    };

    return {
        age: getVal(["ageInput", "age"]),
        gender: getVal(["genderInput", "gender"]),
        severity: getVal(["severityInput", "severity"]),
        comorbidities: getVal(["comorbiditiesInput", "comorbidities"]),
        meds_or_reports: getVal(["medsInput", "meds_or_reports", "priorMeds"]),
        prior_doctor: getVal(["priorDoctorInput", "prior_doctor", "priorMeds"])
    };
}

/* --------- Analyze -> call backend --------- */
async function analyze() {
    console.log('analyze() invoked');
    let txt = "";
    try {
        const ta = getInputElByIds(["symptomsText", "symptoms"]);
        txt = (ta && typeof ta.value !== 'undefined') ? (ta.value || '').toString().trim() : "";
    } catch (e) {
        console.error('error reading symptoms input', e);
        txt = "";
    }
    if (!txt) {
        alert(t("no_input"));
        return;
    }

    setStatus(t("analyzing"));
    const output = document.getElementById("output");
    if (output) output.innerHTML = "";

    try {
        // prepare payload (include metadata if available)
        const meta = collectMeta();
        console.log('analyze payload meta:', meta);
        const payload = { symptoms: txt, ...meta, lang: lang };
        console.log('POST payload:', payload);

        let res = await fetch(BACKEND_JSON_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        console.log('fetch sent, awaiting response: ', BACKEND_JSON_URL);

        // fallback if server expects query param (422/400)
        if (res.status === 422 || res.status === 400) {
            const q = encodeURIComponent(txt);
            res = await fetch(`${BACKEND_GET_URL}?symptoms=${q}`, { method: "GET" });
        }

        if (!res.ok) {
            setStatus(`${t("server_err")} ${res.status}`, true);
            if (output) output.innerHTML = `<div class="card" style="color:#991b1b">${t("server_err")} ${res.status}</div>`;
            return;
        }

        const data = await res.json();
        console.log('response data:', data);

        // If backend returns both symptom predictions (predictions) and diseases, remove label dupes
        if (Array.isArray(data.predictions) && Array.isArray(data.diseases)) {
            const diseaseLabels = new Set(data.diseases.map(d => String(d.label || "").toLowerCase()));
            data.predictions = data.predictions.filter(p => !diseaseLabels.has(String(p.label || "").toLowerCase()));
        }

        renderOutput(data);
        setStatus("");

        // If location already allowed, update doctors list
        if (userLocation) fetchNearbyDoctors(userLocation.lat, userLocation.lon);

    } catch (err) {
        console.error(err);
        setStatus(t("network_err") + " " + err, true);
        if (output) output.innerHTML = `<div class="card" style="color:#991b1b">${t("network_err")} ${err}</div>`;
    }
}

/* --------- Render triage bar helper --------- */
function renderTriageBar(score) {
    // score expected 0..1
    const pct = Math.min(1, Math.max(0, Number(score || 0))) * 100;
    // determine color gradient: green -> yellow -> orange -> red
    let color = "#5cb85c";
    if (pct > 80) color = "#d9534f";
    else if (pct > 60) color = "#f97316"; // orange
    else if (pct > 35) color = "#f59e0b"; // amber
    else color = "#10b981"; // green

    return `
        <div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;font-weight:600;color:#334155;margin-bottom:6px;">
                <div>Danger level</div><div>${pct.toFixed(0)}%</div>
            </div>
            <div style="width:100%;height:12px;background:#e6f2ef;border-radius:999px;overflow:hidden;border:1px solid rgba(0,0,0,0.03)">
                <div style="width:${pct}%;height:100%;background:${color};transition:width 0.4s ease;"></div>
            </div>
        </div>
    `;
}

/* --------- Render combined output (symptoms + diseases + triage) --------- */
function renderOutput(data) {
    const out = document.getElementById("output");
    if (!out) return;
    out.innerHTML = "";

    const symptoms = Array.isArray(data.predictions) ? data.predictions : [];
    const diseases = Array.isArray(data.diseases) ? data.diseases : [];

    // triage may be { level, score, reasons } or string
    let triageObj = { level: "LOW", score: 0.0, reasons: [] };
    if (data.triage) {
        if (typeof data.triage === "string") {
            triageObj.level = data.triage;
        } else if (typeof data.triage === "object") {
            triageObj.level = data.triage.level || data.triage.level_name || triageObj.level;
            triageObj.score = (typeof data.triage.score === "number") ? data.triage.score : (data.triage.score ? Number(data.triage.score) : 0);
            triageObj.reasons = Array.isArray(data.triage.reasons) ? data.triage.reasons : (data.triage.reasons || []);
        }
    }

    // top triage card
    out.insertAdjacentHTML("beforeend", `<div class="card">${renderTriageBar(triageObj.score)}<div style="font-weight:700;color:#0f766e;margin-bottom:8px">${(String(triageObj.level)).toUpperCase()}</div></div>`);

    // show triage reasons if present
    if (triageObj.reasons && triageObj.reasons.length) {
        const reasonsHtml = triageObj.reasons.map(r => `<li>${escapeHtml(String(r))}</li>`).join("");
        out.insertAdjacentHTML("beforeend", `<div class="card"><h3 style="margin-bottom:8px">${t("triage_REASONS")}</h3><ul style="margin-left:18px;color:#475569">${reasonsHtml}</ul></div>`);
    }

    // Symptom cards
    if (symptoms.length) {
        out.insertAdjacentHTML("beforeend", `<h3 style="color:#0f766e;margin-top:10px">Top matching symptoms</h3>`);
        symptoms.forEach(p => {
            const testsHtml = (Array.isArray(p.recommended_tests) ? p.recommended_tests : [])
                .map(t => (typeof t === "string") ? `<li>${escapeHtml(t)}</li>` : `<li><b>${escapeHtml(t.test || t.name || "")}</b> — ${escapeHtml(t.reason || t.desc || "")}</li>`)
                .join("");
            const specialistsHtml = Array.isArray(p.specialists) ? p.specialists.join(", ") : (p.specialists || "");
            const card = `
                <div class="card">
                    <h2>🩺 ${escapeHtml(p.label || "Unknown")} — <span class="score">${(p.score || 0).toFixed(2)}</span></h2>
                    <p>${escapeHtml(p.desc || "")}</p>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <div><b>👨‍⚕ Specialists:</b> ${escapeHtml(specialistsHtml)}</div>
                    </div>
                    <h4 style="margin-top:10px;">🧪 Suggested Tests</h4>
                    <ul>${testsHtml}</ul>
                </div>`;
            out.insertAdjacentHTML("beforeend", card);
        });
    }

    // Disease cards
    if (diseases.length) {
        out.insertAdjacentHTML("beforeend", `<h3 style="color:#0f766e;margin-top:20px">Possible diseases based on your symptoms</h3>`);
        diseases.forEach(d => {
            const testsHtml = (Array.isArray(d.recommended_tests) ? d.recommended_tests : [])
                .map(t => (typeof t === "string") ? `<li>${escapeHtml(t)}</li>` : `<li><b>${escapeHtml(t.test || t.name || "")}</b> — ${escapeHtml(t.reason || t.desc || "")}</li>`)
                .join("");
            const specialistsHtml = Array.isArray(d.specialists) ? d.specialists.join(", ") : (d.specialists || "");
            const card = `
                <div class="card">
                    <h2>🦠 ${escapeHtml(d.label || "Unknown")} — <span class="score">${(d.score || 0).toFixed(2)}</span></h2>
                    <p>${escapeHtml(d.description || d.desc || "")}</p>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <div><b>👨‍⚕ Specialists:</b> ${escapeHtml(specialistsHtml)}</div>
                    </div>
                    <h4 style="margin-top:10px;">🧪 Suggested Tests</h4>
                    <ul>${testsHtml}</ul>
                </div>`;
            out.insertAdjacentHTML("beforeend", card);
        });
    }

    // show triage mapping table if backend sent it
    if (Array.isArray(data.triage_mapping) && data.triage_mapping.length) {
        const mappingHtml = data.triage_mapping.map(m => `<li><b>${escapeHtml(m.priority || m.priority_name || "")}</b>: ${escapeHtml((m.symptoms || []).join(", "))} — ${escapeHtml(m.advice || "")}</li>`).join("");
        out.insertAdjacentHTML("beforeend", `<div class="card"><h3>Triage mapping (reference)</h3><ul style="margin-left:18px;color:#475569">${mappingHtml}</ul></div>`);
    }

    // small disclaimer if provided
    if (data.disclaimer) {
        out.insertAdjacentHTML("beforeend", `<div class="card"><b>Disclaimer:</b> ${escapeHtml(data.disclaimer)}</div>`);
    }
}

/* --------- escape helper --------- */
function escapeHtml(s) {
    if (!s && s !== 0) return "";
    return String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

/* --------- Location & Overpass doctors --------- */
function requestLocation() {
    if (!navigator.geolocation) {
        setStatus("Geolocation not supported by your browser.", true);
        return;
    }
    setStatus("📍 Obtaining location...");
    navigator.geolocation.getCurrentPosition(pos => {
        userLocation = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setStatus(`Location: ${userLocation.lat.toFixed(4)}, ${userLocation.lon.toFixed(4)}`);
        if (document.getElementById("nearbyTitle")) document.getElementById("nearbyTitle").innerText = t("nearby_title");
        fetchNearbyDoctors(userLocation.lat, userLocation.lon);
    }, err => {
        console.warn("loc error", err);
        setStatus(t("loc_denied"), true);
    }, { enableHighAccuracy: true, maximumAge: 60000, timeout: 10000 });
}

async function fetchNearbyDoctors(lat, lon) {
    const listEl = document.getElementById("doctorsList");
    if (!listEl) return;
    listEl.innerHTML = "<p style='color:rgba(34,34,34,0.8)'>Searching nearby doctors…</p>";

    const query = `
        [out:json][timeout:25];
        (
          node["amenity"="doctors"](around:${NEARBY_RADIUS},${lat},${lon});
          node["amenity"="clinic"](around:${NEARBY_RADIUS},${lat},${lon});
          node["healthcare"="doctor"](around:${NEARBY_RADIUS},${lat},${lon});
        );
        out center ${MAX_DOCTORS};
    `;

    try {
        const res = await fetch(OVERPASS_API, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" },
            body: `data=${encodeURIComponent(query)}`
        });
        if (!res.ok) { listEl.innerHTML = `<p style="color:#d44">Doctor search failed (${res.status})</p>`; return; }
        const json = await res.json();
        const elems = json.elements || [];
        if (!elems.length) {
            listEl.innerHTML = `<p style="color:rgba(34,34,34,0.7)">No nearby doctors found within ${(NEARBY_RADIUS / 1000).toFixed(1)} km.</p>`;
            return;
        }

        const withDist = elems.map(el => {
            const lat2 = el.lat || (el.center && el.center.lat);
            const lon2 = el.lon || (el.center && el.center.lon);
            const d = distanceMeters(lat, lon, lat2, lon2);
            const name = (el.tags && (el.tags.name || el.tags.operator)) || "Doctor / Clinic";
            const addr = [
                el.tags && el.tags["addr:street"],
                el.tags && el.tags["addr:housenumber"],
                el.tags && el.tags["addr:city"],
                el.tags && el.tags["addr:postcode"]
            ].filter(Boolean).join(", ");
            return { name, addr, lat: lat2, lon: lon2, dist: d, tags: el.tags || {} };
        });

        withDist.sort((a, b) => a.dist - b.dist);
        listEl.innerHTML = "";
        withDist.slice(0, MAX_DOCTORS).forEach(d => {
            const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(d.lat + ',' + d.lon)}`;
            const doctorHtml = `
                <div class="doctor">
                    <div class="left">
                        <h4>${escapeHtml(d.name)}</h4>
                        <div class="meta">${escapeHtml(d.addr || (d.tags.specialty || "Clinic"))}</div>
                        <div class="meta">${(d.dist < 1000) ? (d.dist.toFixed(0) + " m") : ((d.dist / 1000).toFixed(2) + " km")}</div>
                    </div>
                    <div class="right">
                        <a class="map-link" href="${mapsUrl}" target="_blank" rel="noopener">Open in Maps</a>
                    </div>
                </div>`;
            listEl.insertAdjacentHTML("beforeend", doctorHtml);
        });

    } catch (err) {
        console.error(err);
        listEl.innerHTML = `<p style="color:#d44">${t("network_err")} ${err}</p>`;
    }
}

function distanceMeters(lat1, lon1, lat2, lon2) {
    if (![lat1, lon1, lat2, lon2].every(v => typeof v === "number")) return 1e9;
    const R = 6371e3;
    const toRad = v => v * Math.PI / 180;
    const φ1 = toRad(lat1), φ2 = toRad(lat2);
    const Δφ = toRad(lat2 - lat1);
    const Δλ = toRad(lon2 - lon1);
    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) *
        Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

/* --------- Medical history modal & uploads (localStorage) --------- */
function showAbout() {
    const modal = document.getElementById("aboutModal");
    if (modal) modal.style.display = "block";
}

function closeAbout() {
    const modal = document.getElementById("aboutModal");
    if (modal) modal.style.display = "none";
}

function showTriageTable() {
    const modal = document.getElementById("triageModal");
    if (modal) modal.style.display = "block";
}

function closeTriageTable() {
    const modal = document.getElementById("triageModal");
    if (modal) modal.style.display = "none";
}

function saveTriageData() {
    const triageData = {
        visitDate: document.getElementById("visitDate") ? document.getElementById("visitDate").value : "",
        doctorName: document.getElementById("doctorName") ? document.getElementById("doctorName").value : "",
        specialty: document.getElementById("specialty") ? document.getElementById("specialty").value : "",
        diagnosis: document.getElementById("diagnosis") ? document.getElementById("diagnosis").value : "",
        medications: document.getElementById("medications") ? document.getElementById("medications").value : "",
        treatment: document.getElementById("treatment") ? document.getElementById("treatment").value : ""
    };
    localStorage.setItem('medicalHistory', JSON.stringify(triageData));
    alert("✅ Medical history saved successfully!");
    closeTriageTable();
}

/* File upload helpers (show filenames) */
document.addEventListener('DOMContentLoaded', function () {
    const reportUpload = document.getElementById('reportUpload');
    const prescriptionUpload = document.getElementById('prescriptionUpload');
    if (reportUpload) reportUpload.addEventListener('change', e => handleFileUpload(e.target.files, 'reportFiles'));
    if (prescriptionUpload) prescriptionUpload.addEventListener('change', e => handleFileUpload(e.target.files, 'prescriptionFiles'));
});

function handleFileUpload(files, listId) {
    const fileList = document.getElementById(listId);
    if (!fileList) return;
    const fileArray = Array.from(files);
    fileList.innerHTML = '';
    fileArray.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>📎</span>
            <span style="margin-left:8px">${escapeHtml(file.name)}</span>
            <span style="margin-left:auto; font-size:11px; color:#64748b;">${formatFileSize(file.size)}</span>
        `;
        fileList.appendChild(fileItem);
    });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
}

/* --------- Utilities & onload --------- */
window.addEventListener("load", () => {
    changeLanguage();
    if (document.getElementById("nearbyTitle")) document.getElementById("nearbyTitle").innerText = t("nearby_title");
    if (document.getElementById("voiceBtn")) document.getElementById("voiceBtn").innerText = t("voice_off");

    // restore any saved medical history to form (if present)
    const hist = localStorage.getItem('medicalHistory');
    if (hist) {
        try {
            const obj = JSON.parse(hist);
            if (obj) {
                if (document.getElementById("doctorName")) document.getElementById("doctorName").value = obj.doctorName || "";
                if (document.getElementById("diagnosis")) document.getElementById("diagnosis").value = obj.diagnosis || "";
                if (document.getElementById("medications")) document.getElementById("medications").value = obj.medications || "";
            }
        } catch (e) { /* ignore parse errors */ }
    }
});

// Make `analyze` available globally and attach click handlers to buttons as a fallback
(function attachAnalyzeHandler() {
    try {
        if (typeof analyze === 'function') {
            window.analyze = analyze;
        }
    } catch (e) { }

    // attach to any button with class 'analyze' in case inline onclick was removed
    function attachToAnalyzeButtons() {
        try {
            const btns = document.querySelectorAll('button.analyze, .btn.analyze');
            btns.forEach(b => {
                if (!b._analyzeAttached) {
                    b.addEventListener('click', (ev) => {
                        try { window.analyze && window.analyze(); } catch (e) { console.error('analyze handler error', e); }
                    });
                    // also set onclick attribute as a fallback
                    if (!b.getAttribute('onclick')) b.setAttribute('onclick', 'return false;');
                    b._analyzeAttached = true;
                }
            });
        } catch (e) { console.error(e); }
    }

    // attempt immediate attach (script is often loaded after DOM is ready)
    attachToAnalyzeButtons();
    // also attach on DOMContentLoaded for other loading orders
    document.addEventListener('DOMContentLoaded', attachToAnalyzeButtons);

    // helpful startup log
    try { console.log('frontend script loaded — analyze attached'); } catch (e) { }
})();

// Close modal on outside click (triage/about modals if you add them)
window.onclick = function (event) {
    const aboutModal = document.getElementById("aboutModal");
    const triageModal = document.getElementById("triageModal");
    if (aboutModal && event.target == aboutModal) aboutModal.style.display = "none";
    if (triageModal && event.target == triageModal) triageModal.style.display = "none";
};
