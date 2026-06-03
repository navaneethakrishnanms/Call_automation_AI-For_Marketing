# Call Automation System (Marketing AI)

An AI-powered outbound and inbound call automation platform that leverages Retell AI, Twilio, and Large Language Models (LLMs) to conduct intelligent voice conversations with customers. 

This platform consists of three main components:
1. **Frontend (React + Vite)**: A modern, responsive web application for both Admins and Users.
2. **Backend (FastAPI)**: A Python-based API server handling the core business logic, webhooks, and database.
3. **Bulk Call Service (Node.js)**: A dedicated background service for handling high-volume outbound call batches from spreadsheet uploads.

---

## 🚀 Features

### 🏢 Admin Portal
The Admin portal is a comprehensive dashboard to manage campaigns, monitor calls, and qualify leads.
- **Dashboard**: Get a high-level overview of essential metrics like total calls, active campaigns, leads generated, and average call duration.
- **Campaigns Management**: Create and manage calling campaigns, specifying agents, phone numbers, and conversational contexts.
- **Calls Analytics**: View a detailed list of all outbound and inbound calls. 
  - Tracks status (Completed, Not Answered).
  - Logs call duration, detected language (English, Tamil, Tanglish), and accurate **Cost** per call (fetched directly from Retell API).
  - Detailed view includes the call transcript, recording audio playback, and AI-generated call summaries.
- **Lead Qualification**: AI automatically analyzes call transcripts to score and qualify leads (Hot, Warm, Cold) based on the customer's intent and interest level.
- **Bulk Calling System**: Upload Excel (`.xlsx`) or CSV files containing contacts. The dedicated Node.js service parses the spreadsheet and intelligently triggers Retell API calls in parallel batches to prevent rate limits.
- **User Feedback**: View feedback and ratings submitted by end-users.

### 👤 User Portal
The User portal provides interactive tools for end-users or customers.
- **Request a Call**: Users can manually request an AI agent to call their phone number instantly.
- **Web Voicebot**: Users can directly speak with the AI Assistant through their browser using their microphone—no phone needed! Features a clean, modern UI with a dynamic audio visualizer.
- **Feedback Submission**: Users can rate their experience and submit feedback that is immediately visible to the Admin.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React (Icons), React Router.
- **Backend Core**: Python, FastAPI, SQLAlchemy (Async), SQLite.
- **Background Worker (Bulk Calls)**: Node.js, Express, Multer (File Uploads), SheetJS (Excel Parsing).
- **AI & Telephony Services**:
  - **Retell AI**: Core conversational voice engine.
  - **Twilio**: Phone numbers and basic telephony routing.
  - **LLMs**: Support for OpenAI, Groq, and Ollama (Local LLMs) for transcript analysis, intent detection, and lead scoring.

---

## ⚙️ Setup & Installation

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend (React / Vite)
```bash
cd frontend
npm install
npm run dev
```
*The frontend will run on `http://localhost:5173/`*

### 3. Bulk Call Service (Node.js)
```bash
cd bulk-call-service
npm install
npm start
```
*The background service runs on `http://localhost:3001/`*

---

## 🗄️ Environment Variables

Each component has its own `.env` file that must be configured.

**Backend (`backend/.env`)**
- `DATABASE_URL` (SQLite)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `RETELL_API_KEY`, `RETELL_AGENT_ID`, `RETELL_PHONE_NUMBER`
- LLM API Keys (`GROQ_API_KEY`, etc.)

**Frontend (`frontend/.env`)**
- `VITE_API_URL` (usually `http://localhost:8000/api`)

**Bulk Call Service (`bulk-call-service/.env`)**
- `RETELL_API_KEY`, `RETELL_PHONE_NUMBER`
- `BATCH_SIZE` (default: 10), `BATCH_DELAY_MS` (default: 1000)

---

## 📝 Recent Updates
- Completely removed the "Pipeline Context" window from the Web Voicebot for a cleaner UI.
- Added Back buttons to the User Portal screens (Voicebot, Feedback) for easier navigation.
- Integrated accurate Call Cost extraction directly from the Retell AI API, dynamically displayed in the Admin Calls table as formatted currency (USD).
