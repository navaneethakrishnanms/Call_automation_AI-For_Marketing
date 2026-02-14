# 🎯 AI-Powered Call Automation & Voice FAQ Chatbot for Marketing

An intelligent voice chatbot platform that automates marketing calls with multilingual support (English, Tamil, Tanglish), real-time FAQ retrieval, and automated lead qualification.

## ✨ Features

- **🎤 Voice AI Chatbot**: Browser-based real-time voice interaction
- **🌐 Multilingual Support**: English, Tamil, and Tanglish (Tamil in English script)
- **📚 Smart FAQ Retrieval**: FAISS-powered semantic search for campaign-specific answers
- **📊 Lead Qualification**: Automatic Hot/Warm/Cold lead scoring based on conversation
- **📞 Twilio Integration**: Automated outbound calling with voice AI
- **🔄 Campaign Management**: Create and manage multiple marketing campaigns
- **📈 Analytics Dashboard**: Real-time call metrics and conversion tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│                    (Phone / Browser)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    TWILIO VOICE API                              │
│                 (Call Control & Audio)                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   FASTAPI BACKEND                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Whisper    │  │  LLaMA 3.1  │  │  Sarvam AI / XTTS v2    │  │
│  │  (STT)      │→ │  (LLM)      │→ │  (TTS)                  │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────────┘  │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │   FAISS     │                                │
│                   │ (FAQ RAG)   │                                │
│                   └─────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React + Vite | Dashboard & Voice Chat UI |
| **Backend** | FastAPI + SQLAlchemy | REST API & Business Logic |
| **Database** | PostgreSQL / SQLite | Campaign, Lead, Call storage |
| **STT (Primary)** | Whisper Large v3 Turbo | Speech-to-Text (via Groq) |
| **LLM** | LLaMA 3.1 8B | Response generation (via Ollama) |
| **TTS (Primary)** | Sarvam AI Bulbul v3 | Text-to-Speech (all languages) |
| **TTS (Fallback)** | XTTS v2 | English voice (local) |
| **Embeddings** | all-MiniLM-L6-v2 | Sentence embeddings for FAQ search |
| **Vector Search** | FAISS | Semantic FAQ retrieval |
| **Telephony** | Twilio Voice API | Outbound call automation |

## 🔀 Routing Rules

```
┌─────────────────────────────────────────────────────────┐
│                    STT ROUTING                          │
├─────────────────────────────────────────────────────────┤
│  Audio Input                                            │
│       ↓                                                 │
│  Whisper Large v3 Turbo (Groq) ← PRIMARY                │
│       ↓                                                 │
│  [Low confidence + Tamil?] → Sarvam STT (fallback)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    TTS ROUTING                          │
├─────────────────────────────────────────────────────────┤
│  All Languages → Sarvam Bulbul v3 (PRIMARY)             │
│       ↓                                                 │
│  [Sarvam fails + English?] → XTTS v2 (FALLBACK)         │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama (for local LLM)
- API keys for Groq, Sarvam AI, Twilio

### 1. Clone Repository

```bash
git clone https://github.com/navaneethakrishnanms/Call_automation_AI-For_Marketing.git
cd Call_automation_AI-For_Marketing
```

### 2. Environment Setup

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Frontend
cp frontend/.env.example frontend/.env
```

Required environment variables:
```env
# backend/.env
GROQ_API_KEY=your_groq_api_key
SARVAM_API_KEY=your_sarvam_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### 3. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 4. Pull Ollama Model

```bash
ollama pull llama3.1:8b
```

### 5. Run Application

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access:
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

Access:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

## 📁 Project Structure

```
Marketing_AI/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # API endpoints
│   │   │   ├── campaigns.py     # Campaign CRUD
│   │   │   ├── calls.py         # Call management
│   │   │   ├── leads.py         # Lead management
│   │   │   ├── voice_chat.py    # Voice/Text chat
│   │   │   └── twilio_webhook.py # Twilio integration
│   │   ├── services/            # Business logic
│   │   │   ├── stt_service.py   # Speech-to-Text
│   │   │   ├── tts_service.py   # Text-to-Speech
│   │   │   ├── llm_service.py   # LLM responses
│   │   │   ├── faq_retrieval.py # FAISS RAG
│   │   │   └── lead_qualifier.py # Lead scoring
│   │   ├── models/              # Database models
│   │   ├── schemas/             # Pydantic schemas
│   │   └── utils/               # Utilities
│   │       ├── prompts.py       # LLM prompts
│   │       └── tts_normalizer.py ## TTS text normalization
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # React pages
│   │   │   ├── VoiceChatPage.jsx   # Voice chatbot
│   │   │   ├── CampaignsPage.jsx   # Campaign management
│   │   │   ├── LeadsPage.jsx       # Lead tracking
│   │   │   ├── CallsPage.jsx       # Call history
│   │   │   └── AnalyticsPage.jsx   # Analytics
│   │   ├── components/          # Reusable components
│   │   └── services/            # API services
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/campaigns` | GET/POST | List/Create campaigns |
| `/api/campaigns/{id}` | GET/PUT/DELETE | Campaign operations |
| `/api/campaigns/{id}/faqs` | POST | Add FAQs to campaign |
| `/api/voice/chat/audio` | POST | Voice chat (audio input) |
| `/api/voice/chat/text` | POST | Text chat |
| `/api/leads` | GET/POST | List/Create leads |
| `/api/calls` | GET/POST | List/Create calls |
| `/api/calls/{id}/start` | POST | Start outbound call |
| `/api/twilio/voice` | POST | Twilio webhook |
| `/api/analytics/dashboard` | GET | Dashboard metrics |

## 📱 Screenshots

### Voice Chatbot
Real-time voice conversation with AI in multiple languages.

### Campaign Management
Create campaigns with custom FAQs for intelligent responses.

### Lead Dashboard
Track qualified leads with Hot/Warm/Cold scoring.

## 🎯 Use Cases

1. **College Admissions**: Answer prospective student queries about courses, fees, placements
2. **Real Estate**: Handle property inquiries and schedule site visits
3. **E-commerce**: Customer support and order tracking
4. **Healthcare**: Appointment booking and general inquiries

## 📄 License

MIT License

## 👥 Team

**Auralytics** - IMPACT-AI-THON 2026

---

Built with ❤️ using FastAPI, React, LLaMA, Whisper, and Sarvam AI
