# Project Handover Guide (Voice RAG)

This document helps a new developer understand this codebase quickly and safely.

## 1. What this project is

This is a multilingual university assistant with:

- Text chat + voice input
- RAG retrieval from Qdrant vector database
- LLM response generation (Groq)
- TTS output (ElevenLabs primary, Edge TTS fallback)
- Conversation history in browser local storage

Main stack:

- Backend: FastAPI + Python
- Frontend: React + TypeScript + Vite
- Vector DB: Qdrant Cloud
- Embeddings: Sentence Transformers

## 2. Quick start for a new developer

### 2.1 Prerequisites

- Python 3.11
- Node.js (for frontend)
- A populated `.env` with required API keys/URLs

### 2.2 Local run

From project root:

```bash
# one-command start script
./start_gemini.sh
```

Manual run alternative:

```bash
# backend
source venv/bin/activate
PYTHONPATH=$PWD python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev
```

Stop services:

```bash
./stop_gemini.sh
```

## 3. Runtime architecture (high level)

1. Frontend sends user question to backend (`/api/query` or `/api/query-stream`).
2. Backend `RAGEngine` embeds query and searches Qdrant.
3. Retrieved context is passed to Groq for answer generation.
4. Backend returns final answer (or stream deltas for live typing).
5. Frontend optionally requests TTS (`/api/tts` or `/api/tts-synced`) and plays audio.
6. Conversations are persisted in browser localStorage.

## 4. Core code map (what each important file does)

## 4.1 Backend (`backend/`)

- `backend/main.py`
  - FastAPI app entrypoint.
  - Configures CORS and lazy initialization.
  - Hosts all HTTP endpoints:
    - `GET /api/health`
    - `POST /api/query`
    - `POST /api/query-stream`
    - `POST /api/voice-query`
    - `POST /api/tts`
    - `POST /api/tts-synced`
    - `POST /api/feedback`
    - `GET /api/feedback/stats`
    - `GET /api/elevenlabs-status`

- `backend/rag_engine.py`
  - Main RAG logic.
  - Initializes Groq client + embedding model + Qdrant client.
  - Contains query search/ranking, translation support, clarification handling, and conversation memory helpers.
  - Most likely file to edit for retrieval quality and answer logic.

- `backend/voice_processor.py`
  - Audio transcription utility (SpeechRecognition).
  - Used by `/api/voice-query` for uploaded audio transcription.

- `backend/elevenlabs_tts_service.py`
  - Primary TTS integration.
  - Supports regular TTS and timestamp-based TTS.
  - Includes subscription usage fetch.

- `backend/edge_tts_service.py`
  - Fallback TTS (free, no billing).
  - Supports async TTS and word timing estimation.

- `backend/tts_service.py`
  - Legacy Google Cloud TTS integration.
  - Kept for compatibility; not the default in `backend/main.py`.

- `backend/feedback_service.py`
  - Stores and summarizes user feedback in `feedback_data.json`.
  - Computes aggregate satisfaction stats.

- `backend/__init__.py`
  - Package marker.

## 4.2 Frontend (`frontend/src/`)

- `frontend/src/App.tsx`
  - Main UI orchestration.
  - Handles:
    - message state
    - backend health polling
    - streaming answer rendering
    - synced TTS queue integration
    - sidebar/new-chat/switch-chat behavior

- `frontend/src/main.tsx`
  - React root mount.

- `frontend/src/services/api.ts`
  - API client layer for backend calls.
  - Includes retry behavior and SSE streaming parser.
  - Base URL comes from `VITE_API_URL`.

- `frontend/src/services/storage.ts`
  - localStorage persistence for conversations.
  - Defines `Conversation` and `Message` models used by UI.

- `frontend/src/hooks/useConversations.ts`
  - Conversation state management hook.
  - Create/switch/update/delete/search conversation logic.

- `frontend/src/components/ChatInterface.tsx`
  - Message list rendering, typing indicator, auto-scroll.

- `frontend/src/components/ConversationSidebar.tsx`
  - Left sidebar (history grouped by date + new chat + delete chat).

- `frontend/src/components/TextInput.tsx`
  - Text prompt input + submit button.

- `frontend/src/components/VoiceInput.tsx`
  - Browser Web Speech API input for voice-to-text.

- `frontend/src/components/Message.tsx`
  - Message bubble component with optional feedback buttons.

- `frontend/src/utils/syncedAudio.ts`
  - Synced audio playback and word timing queue.
  - Uses `/api/tts-synced` and emits `tts-started` / `tts-ended` events.

- `frontend/src/utils/speech.ts`
  - Non-synced TTS helper (`/api/tts`) + browser TTS fallback.

- `frontend/src/utils/streaming.ts`
  - Older utility for word streaming and queue.
  - Contains hardcoded localhost TTS URL and may not be the current primary path.

- `frontend/src/App.css` + component CSS files
  - UI styles.

- `frontend/src/App.tsx.bak`, `frontend/src/App.tsx.broken`
  - Backup/experimental files (not part of active app build).

## 4.3 Data and model assets

- `rag_chunks_with_faculty.json`
  - Main knowledge chunks used for RAG embedding/search.
  - This is the source data to update for institutional facts.

- `feedback_data.json`
  - Persisted feedback records and computed stats.

- `models/vosk-model-small-en-us-0.15/`
  - Speech model asset folder (kept in repo).

- `uploads/`
  - Temporary uploaded audio files.

- `logs/`
  - Backend/frontend runtime logs for local scripts.

## 4.4 Build, deployment, and environment files

- `requirements.txt`
  - Python dependencies.

- `frontend/package.json`
  - Frontend dependencies and scripts (`dev`, `build`, `preview`).

- `render.yaml`
  - Render deployment config for backend and static frontend.

- `runtime.txt`
  - Python runtime pin.

- `.env` (not committed)
  - Secrets and runtime variables.

## 4.5 Utility scripts

- `upload_to_qdrant.py`
  - Recreates collection and uploads vectorized chunks to Qdrant.

- `filter_uit_data.py`
  - Filters chunk dataset to UIT-relevant content.

- `check_models.py`
  - Lists available Gemini models for API key validation.

- `check_python_compatibility.py`
  - Checks package Python version compatibility via PyPI metadata.

- `cleanup_unused_files.sh`
  - Repo cleanup helper script.

- `test_faculty_demo.sh`
  - Faculty demo testing helper script.

- `test_audio.html`
  - Simple browser page for audio behavior checks.

## 4.6 Documentation files

This repo includes many docs. Most useful for handover and operations:

- `README.md`: full overview, architecture, setup, and research framing.
- `DEPLOYMENT.md`, `GOOGLE_CLOUD_SETUP.md`, `render.yaml`: deployment/runtime setup.
- `TEAM_GUIDE.md`, `QUICK_REFERENCE.md`: day-to-day team usage docs.
- `DATASET_AND_METHODOLOGY.md`, `RAG_MATHEMATICS.md`, `RAG_FLOWCHART.md`: RAG design details.
- `FACULTY_TESTING_GUIDE.md`, `FACULTY_REVIEW_SCENARIOS.md`, `FINAL_TEST_RESULTS.md`: testing/review references.
- `STREAMING_TTS_PLAN.md`: streaming TTS architecture notes.

## 5. Environment variables (minimum expected)

Backend expects these values in `.env` (or deployment secrets):

- `GROQ_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `ELEVENLABS_API_KEY` (optional but recommended)
- `ELEVENLABS_MODEL_ID` (optional)
- `ELEVENLABS_VOICE_ID_EN` (optional)
- `ELEVENLABS_VOICE_ID_HI` (optional)
- `FRONTEND_URL` (optional CORS extension)

Frontend important env:

- `VITE_API_URL`
- `VITE_STREAMING_TEXT`
- `VITE_STREAMING_TTS`

## 6. Common change tasks (where to edit)

### 6.1 Add or update university knowledge

1. Edit `rag_chunks_with_faculty.json`.
2. Re-upload vectors with `upload_to_qdrant.py`.
3. Verify search quality from UI/API.

### 6.2 Improve retrieval or answer quality

1. Edit search/ranking/prompt logic in `backend/rag_engine.py`.
2. Test via `/api/query` and `/api/query-stream`.
3. Validate multilingual behavior and clarification flow.

### 6.3 Add a new API endpoint

1. Add endpoint in `backend/main.py`.
2. Add typed client function in `frontend/src/services/api.ts`.
3. Wire UI usage in `frontend/src/App.tsx` or component layer.

### 6.4 Change voice behavior

1. Browser voice input: `frontend/src/components/VoiceInput.tsx`.
2. Backend transcription: `backend/voice_processor.py`.
3. TTS service preference/fallback: `backend/main.py` and TTS service files.
4. Synced speech playback: `frontend/src/utils/syncedAudio.ts`.

### 6.5 Change chat/conversation behavior

1. UI/message flow: `frontend/src/App.tsx`.
2. Conversation state logic: `frontend/src/hooks/useConversations.ts`.
3. Local persistence behavior: `frontend/src/services/storage.ts`.

## 7. Testing and validation checklist before shipping

- Backend health endpoint returns healthy.
- Text query works for English and Hindi.
- Streaming query renders progressively.
- Voice input captures and sends transcript.
- TTS works (ElevenLabs when configured, fallback otherwise).
- Conversation switching and persistence work.
- No CORS issues between frontend/backend URLs.
- Key queries from faculty/demo scenarios still return correct answers.

## 8. Known caveats and cleanup opportunities

- There are legacy/backup files (`App.tsx.bak`, `App.tsx.broken`) that can confuse new contributors.
- `frontend/src/utils/streaming.ts` appears older and uses hardcoded localhost TTS URL; avoid using it as primary reference unless intentionally refactoring.
- Some scripts/docs still mention Gemini while current core generation path is Groq in backend runtime.

## 9. Suggested onboarding sequence for your friend

1. Read `README.md` for architecture and context.
2. Run project locally using `start_gemini.sh`.
3. Inspect `backend/main.py` and `frontend/src/App.tsx` first.
4. Test one text query, one voice query, and one feedback action.
5. Make one small change (for example prompt tuning in `backend/rag_engine.py`) and verify end-to-end.

## 10. Ownership suggestion (optional)

If multiple contributors work in parallel:

- Contributor A: `backend/rag_engine.py` + data quality (`rag_chunks_with_faculty.json`)
- Contributor B: frontend UX and conversation flow (`frontend/src/App.tsx`, components)
- Contributor C: voice/TTS reliability (`backend/*tts*`, `frontend/src/utils/syncedAudio.ts`)

This split reduces merge conflicts and keeps responsibility clear.
