# AI Health Assistant 🩺

An advanced AI-powered health assistance platform that provides instant symptom analysis, disease prediction, and finds nearby healthcare providers using zero-shot AI technology.

## 🚀 Features

- **AI Symptom Analysis**: Uses zero-shot learning to analyze symptoms and predict possible conditions.
- **Disease Prediction**: Compares symptoms against a comprehensive medical database.
- **Multilingual Support**: Supports English, Hindi, and Marathi with dynamic UI translation.
- **Nearby Doctor Finder**: Locates nearby clinics and hospitals using OpenStreetMap data.
- **Medical Triage**: Provides danger level assessment and professional advice.
- **Medical History & Triage Table**: Allows users to log previous visits and upload documents.
- **Voice Recognition**: Support for voice-to-text symptom input.

## 🛠️ Technology Stack

- **Backend**: Python, FastAPI, Uvicorn
- **AI/ML**: PyTorch, Sentence-Transformers, FAISS, Transformers
- **Translation**: Deep-Translator
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (Vanilla)
- **Data Source**: OpenStreetMap (Overpass API)

## 📦 Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js (for frontend static serving or just use Python)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/pruthvirajtarode/AI-Health-Assistant.git
   cd AI-Health-Assistant
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Backend Server**:
   ```bash
   python server.py
   ```
   The backend will be available at `http://127.0.0.1:8000`.

5. **Run the Frontend**:
   You can serve the `frontend/` directory using any static server. For example:
   ```bash
   cd frontend
   python -m http.server 3000
   ```
   Open your browser at `http://localhost:3000`.

## 🌐 Deployment

For deployment instructions, please refer to the deployment guide provided in the initial setup. Recommended platforms include Vercel (Frontend) and Render/Railway (Backend).

## ⚠️ Medical Disclaimer

**This tool is for informational purposes only.** It does not provide medical advice, diagnosis, or treatment. Always consult with a qualified healthcare professional for medical concerns. In case of emergency, call your local emergency services immediately.
