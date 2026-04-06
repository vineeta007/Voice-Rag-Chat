# VoiceRAG Implementation Guide

This document details the exact technical execution and implementation of the VoiceRAG system based on the underlying codebase. It covers the environment setup, core module development, third-party API integration, and the orchestration of the frontend and backend microservices.

The implementation follows a decoupled architecture, ensuring that the Voice/UI layer, text-processing layer, and LLM-retrieval layers operate asynchronously for optimal performance.

---

## 1. Project Setup and Environment Configuration

Establishing a consistent and isolated development environment is critical for managing dependencies and resolving cross-platform compatibility issues. The project utilizes a fully decoupled modern stack: a Python-based FastAPI backend for heavy computational tasks (RAG, Vector DB querying) and a Node.js/React-based frontend for the user interface and voice capture.

### Prerequisites and Installation

The foundational requirement for the backend is **Python 3.10+**, chosen for robust support for modern AI libraries and asynchronous operations.

- **Python Installation:** A virtual environment (`venv`) is initialized to encapsulate the project's dependencies, preventing conflicts with system-wide packages.
- **Node.js Installation:** Node.js and `npm` manage the frontend React application powered by Vite, which drastically reduces build times and improves Hot Module Replacement (HMR) during development.

### Repository Management

The source code is hosted on a secure Git repository. The local setup process begins with cloning the repository:

```bash
git clone <repository_url>
cd voicerag
```

### Dependency Management

Dependencies are strictly version-controlled.

- **Backend:** Dependencies are listed in `requirements.txt`. Execution of `pip install -r requirements.txt` installs crucial packages such as `fastapi`, `qdrant-client`, `sentence-transformers`, `groq`, and `uvicorn`.
- **Frontend:** Within the `frontend/` directory, executing `npm install` resolves dependencies enumerated in `package.json`, including `react`, `react-dom`, and TypeScript configurations.

### Environment Variables

A `.env` file must be established at the root to securely hold secret credentials. Key variables include:

- `GROQ_API_KEY`: For fast inference using Llama 3 on the Groq engine.
- `QDRANT_URL` and `QDRANT_API_KEY`: For remote vector database access.

---

## 2. System Modules Architecture

The system is logically partitioned into discrete modules, each handling a specific segment of the Voice-in, Voice-out conversational pipeline.

### 2.1 Voice Input Module

The Voice Input Module is the primary interface between the user and the system, residing on the client-side (frontend) inside the `VoiceInput.tsx` component.

**Microphone Recording and Audio Context:**
When a user initiates an interaction, the UI requests microphone permissions. To provide a premium user experience, the raw audio stream is piped into an `AudioContext`. An `AnalyserNode` performs Fast Fourier Transforms (FFT) on the incoming audio signal, converting the time-domain audio wave into frequency-domain data (`getByteFrequencyData`). The resulting array of frequency magnitudes is mapped to a real-time visualizer (Voice Waveform UI), providing immediate visual feedback that the user's voice is being registered.

### 2.2 Speech-to-Text (STT) Module

Unlike legacy systems that offload raw audio blobs to a backend server, this application maximizes speed and privacy by utilizing browser-native capabilities on the frontend.

**Web Speech API Integration:**
Within `VoiceInput.tsx` (and `speech.ts` utilities), the app leverages the natively available `SpeechRecognition` (or `webkitSpeechRecognition`) interface natively built into modern browsers.

1. As the user speaks, the browser's internal acoustic engine captures the audio.
2. It processes the speech in real-time, emitting `onresult` events holding intermediate and final transcription transcripts.
3. This completely bypasses the need for large local models or slow backend STT network calls, emitting a finalized text string instantly when the user stops speaking.

_(Note: While legacy `vosk` model files may reside in the repository structure for historical testing, production STT execution leverages the highly optimized native Web Speech API)._

### 2.3 Document Processing Module

This offline/administrative pipeline converts raw institutional documents into searchable vectors before runtime.

- **Text Chunking Pipeline:** The system utilizes `upload_to_qdrant.py` to ingest pre-compiled datasets (such as `rag_chunks_with_faculty.json`). This ensures that large university datasets are broken down into logical paragraph-sized segments. Detailed chunking schemas overlap context so that semantic meaning is preserved across chunk boundaries.

### 2.4 Vector Database Creation

Standard relational databases search by exact keyword matches, which is insufficient for AI. We require semantic search (matching by meaning).

- **Embedding Generation:** The system utilizes the **SentenceTransformers** library running the `all-mpnet-base-v2` model locally to create embeddings. This model iterates over the text chunks and maps their semantic meaning into a high-dimensional (768-dimension) dense vector space locally.
- **Vector Storage:** These pre-computed embeddings, alongside their metadata, are ingested remotely into **Qdrant**, an advanced open-source vector search engine. Vectors are organized using HNSW algorithms within a designated Qdrant collection, allowing the system to find nearest mathematical neighbors in milliseconds.

### 2.5 Query Processing Module

When the native frontend STT finalized a text transcript, it is sent to the FastAPI backend (`backend/rag_engine.py`), where the Query Processing Module intercepts the string.

1. **Query Vectorization:** The user's plaintext query is passed through the same `SentenceTransformer` (`all-mpnet-base-v2`) inside the `RAGEngine` class. This converts the conversational question into a 768-D query vector format.
2. **Semantic Search (Similarity Matching):** The query vector is dispatched to Qdrant via `QdrantClient`. Qdrant calculates semantic similarity matches between the user's query and the stored university dataset.
3. **Context Retrieval:** The top matched vectors are returned. The `RAGEngine` extracts the exact textual payloads of these vectors, representing the exact context required to answer the user's query.

### 2.6 Response Generation Module

The system utilizes the blazing-fast **Groq API**—housing the sophisticated **Llama-3.3-70b-versatile** model—to synthesize human-like answers. Gemini/Google APIs were previously tested but superseded by Groq for lower latency.

**Prompt Engineering and Synthesis:**
The retrieved chunks, combined with conversation history (managed by the `ConversationMemory` class), and the user query are injected into a meticulously engineered prompt template:

- _System Directive:_ "You are an intelligent, helpful voice AI assistant..."
- _Injected Context:_ [Appended chunks from Qdrant]
- _User Query:_ [The STT transcription]

By utilizing this Retrieval-Augmented Generation (RAG) methodology, the Llama-3 model relies strictly on validated institutional facts, severely curtailing hallucination risks.

### 2.7 Text-to-Speech (TTS) Module

Once the Llama-3 model generates a textual response, the TTS Module operates to convert this text back into audible speech.

1. **TTS Routing:** The backend coordinates TTS. Scripts for robust integrations like Edge TTS (`edge_tts_service.py`), ElevenLabs (`elevenlabs_tts_service.py`), and Google Cloud TTS exist depending on load and tier.
2. **Audio Synthesis Pipeline:** The `speech.ts` utility on the frontend intercepts the LLM's text stream and executes an API call to the TTS orchestration endpoint.
3. **Fallback Architecture:** If API-based TTS experiences rate limiting or connectivity bounds, the system gracefully falls back to the local browser's `SpeechSynthesisUtterance` interface, ensuring zero-downtime voice delivery to the user.

### 2.8 API Implementation

The backend exposes its functionalities through a robust RESTful API built on **FastAPI**.

**Endpoint Architecture:**

- `POST /api/chat`: The central multimodal orchestrator. Accepts text payloads, securely interfaces with the `RAGEngine`, updates memory strings, hits Qdrant, calls the Groq Llama-3 model, and streams the response backward.
- `POST /api/tts`: Specifically fields raw text strings generated by the LLM and contacts configured TTS sub-services to stream back `.mp3` bytes directly to the frontend's `Audio` API.

**CORS and Async Handling:**
`CORSMiddleware` is strictly bound to the FastAPI instance to allow secure interfacing. Endpoints actively leverage asynchronous programming (`async def`) extensively. Since database calls (Qdrant) and LLM processes (Groq API) are high-latency I/O operations, `async` ensures that other system health checks or concurrent users do not face blocked server threads.
