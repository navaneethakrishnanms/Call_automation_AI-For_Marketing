# Marketing AI - Voice Chatbot & Call Automation Platform

An AI-powered voice chatbot for marketing with multilingual capabilities (English, Tamil, and Tanglish).

## 🚀 Features

- **Voice AI Chatbot**: Browser-based voice interaction
- **Multilingual Support**: English, Tamil, and Tanglish
- **AI-Powered Conversations**: Natural responses using Llama 3.1 8B
- **FAQ Retrieval**: Semantic search with FAISS
- **Lead Qualification**: Automatic hot/warm/cold scoring
- **Call Automation**: Twilio integration (optional)

## 🤖 AI Stack

| Component | Model | Provider |
|-----------|-------|----------|
| **STT** | Whisper Large v3 Turbo | Groq API |
| **Embeddings** | all-MiniLM-L6-v2 | Sentence-Transformers |
| **LLM** | Llama 3.1 8B | Ollama (local) |
| **TTS** | Bulbul v3 (kavitha) | Sarvam AI |

## 🎯 System Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                 VOICE CHATBOT PIPELINE                       │
└─────────────────────────────────────────────────────────────┘

  User Speaks (Microphone)
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  1. SPEECH-TO-TEXT                                      │
  │     Model: Whisper Large v3 Turbo (Groq)                │
  │     Features: 30s timeout, retry, debounce (<500ms)     │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  2. LANGUAGE DETECTION                                  │
  │     Languages: English | Tamil | Tanglish               │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  3. FAQ RETRIEVAL (RAG)                                 │
  │     Embedding: all-MiniLM-L6-v2                         │
  │     Vector DB: FAISS                                    │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  4. LLM RESPONSE                                        │
  │     Model: Llama 3.1 8B (Ollama)                        │
  │     Output: 1-2 sentences, conversational               │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  5. LEAD QUALIFICATION                                  │
  │     Scores: Hot | Warm | Cold                           │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  6. TEXT-TO-SPEECH                                      │
  │     Model: Bulbul v3 (Sarvam AI)                        │
  │     Speaker: kavitha                                    │
  └─────────────────────────────────────────────────────────┘
       │
       ▼
  User Hears Response (Audio)
```

## 🔧 Setup

### 1. Environment Variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
GROQ_API_KEY=your_groq_key
SARVAM_API_KEY=your_sarvam_key
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### 2. Pull Ollama Model

```bash
ollama pull llama3.1:8b
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Access

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 💻 Local Development

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
Marketing_AI/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── services/
│   │   │   ├── stt_service.py      # Whisper STT
│   │   │   ├── llm_service.py      # Llama 3.1 8B
│   │   │   ├── tts_service.py      # Sarvam TTS
│   │   │   ├── faq_retrieval.py    # FAISS RAG
│   │   │   └── lead_qualifier.py   # Lead scoring
│   │   └── main.py
│   └── faqs/
├── frontend/
│   └── src/
│       └── pages/
│           └── VoiceChatPage.jsx   # Voice UI
└── docker-compose.yml
```

## 🔌 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/voice/chat/audio` | Voice chat (audio input) |
| `POST /api/voice/chat/text` | Text chat |
| `GET /api/campaigns` | List campaigns |
| `GET /api/leads` | List leads |
| `GET /api/analytics/overview` | Dashboard stats |

## 📝 License

MIT License
