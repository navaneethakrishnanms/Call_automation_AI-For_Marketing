# Marketing AI - Call Automation Platform

An AI-powered call automation platform for marketing with multilingual support (English, Tamil, and Tanglish).

## 🚀 Features

- **Multilingual Support**: Automatic language detection for English, Tamil, and Tanglish
- **AI-Powered Conversations**: Natural, friendly responses using Mistral-7B via Ollama
- **FAQ Retrieval**: Semantic search with Sentence-Transformers + FAISS
- **Lead Qualification**: Automatic hot/warm/cold lead scoring
- **Speech Processing**: Whisper for STT, ElevenLabs & Sarvam AI for TTS
- **Telephony Integration**: Twilio for voice calls
- **Analytics Dashboard**: Real-time call and lead analytics

## 📋 Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.10+ (for local development)
- Ollama with Mistral-7B model (for LLM)

## 🔧 Environment Setup

1. Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```

2. Configure your API keys in `backend/.env`:
```env
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# AI Services
GROQ_API_KEY=your_groq_api_key        # For Whisper Large v3 Turbo STT
ELEVENLABS_API_KEY=your_elevenlabs_key  # English TTS
SARVAM_API_KEY=your_sarvam_key          # Tamil TTS

# Ollama (local LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct
```

3. Pull the Ollama model:
```bash
ollama pull mistral:7b-instruct
```

## 🐳 Running with Docker

### Start All Services
```bash
docker-compose up --build
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Stop Services
```bash
docker-compose down
```

## 💻 Local Development

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
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
│   │   ├── api/routes/       # REST endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # AI services
│   │   │   ├── call_orchestrator.py   # Main call flow
│   │   │   ├── language_detector.py   # Language detection
│   │   │   ├── faq_retrieval.py       # FAISS retrieval
│   │   │   ├── llm_service.py         # Mistral via Ollama
│   │   │   ├── stt_service.py         # Whisper STT
│   │   │   ├── tts_service.py         # ElevenLabs/Sarvam TTS
│   │   │   └── lead_qualifier.py      # Lead scoring
│   │   └── main.py
│   ├── faqs/                 # Campaign FAQs
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # React pages
│   │   ├── components/       # UI components
│   │   └── api/              # API client
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🔌 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/campaigns` | List all campaigns |
| `POST /api/campaigns` | Create a campaign |
| `GET /api/calls` | List call history |
| `POST /api/calls/initiate` | Start outbound call |
| `GET /api/leads` | List leads |
| `GET /api/analytics/overview` | Dashboard stats |
| `POST /api/webhooks/twilio/voice` | Twilio webhook |

## 🎯 Call Flow

```
Incoming Call → Twilio Webhook
     ↓
Speech Recognition (Whisper)
     ↓
Language Detection (English/Tamil/Tanglish)
     ↓
FAQ Retrieval (Sentence-Transformers + FAISS)
     ↓
Response Generation (Mistral-7B via Ollama)
     ↓
Text-to-Speech (ElevenLabs or Sarvam AI)
     ↓
Audio Response to Caller
```

## 🔒 Security Notes

- Store all API keys in environment variables
- Never commit `.env` files to version control
- Use `SECRET_KEY` for session management
- Configure CORS origins appropriately for production

## 📝 License

MIT License
