"""
FastAPI Backend for Multilingual Voice RAG System
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import tempfile
import shutil
import json
import re
import uuid
import hmac
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import os
PORT = int(os.environ.get("PORT", 10000))

# Load environment variables
load_dotenv()

# from backend.tts_service import tts_service  # Google Cloud TTS (requires billing)
from edge_tts_service import edge_tts_service
from elevenlabs_tts_service import elevenlabs_tts_service
from feedback_service import feedback_service  # Feedback system


# Prefer ElevenLabs if configured, otherwise fallback to Edge TTS.
tts_service = elevenlabs_tts_service if elevenlabs_tts_service.enabled else edge_tts_service


# Initialize FastAPI app
app = FastAPI(
    title="Multilingual Voice RAG API",
    description="RAG system for university data with voice and text input",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",  # ⭐ VERY IMPORTANT
        "http://localhost:3000",
        "https://voice-rag-chat.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/api/health")
def health():
    return {"status": "ok"}

# Initialize RAG engine and voice processor
rag_engine = None
voice_processor = None
DATA_PATH = Path(__file__).resolve().parent.parent / "rag_chunks_with_faculty.json"

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

SESSION_COOKIE_NAME = "vr_user"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 180  # 180 days
SESSION_DB_PATH = Path("chat_sessions.db")
SESSION_SIGNING_KEY = os.getenv("SESSION_SIGNING_KEY", "dev-insecure-change-me")
IS_PRODUCTION = os.getenv("RENDER", "").lower() == "true" or os.getenv("ENV", "").lower() == "production"

if SESSION_SIGNING_KEY == "dev-insecure-change-me":
    print("⚠️ SESSION_SIGNING_KEY not set. Set it in production for secure signed cookies.")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sign_user_id(user_id: str) -> str:
    digest = hmac.new(SESSION_SIGNING_KEY.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{user_id}.{digest}"


def _verify_user_token(token: str) -> Optional[str]:
    if not token or "." not in token:
        return None

    user_id, provided_sig = token.rsplit(".", 1)
    expected_sig = hmac.new(SESSION_SIGNING_KEY.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(provided_sig, expected_sig):
        return user_id
    return None


def _get_or_create_user_identity(request: Request) -> tuple[str, Optional[str]]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user_id = _verify_user_token(token) if token else None
    if user_id:
        return user_id, None

    user_id = str(uuid.uuid4())
    signed_token = _sign_user_id(user_id)
    return user_id, signed_token


def _attach_user_cookie(response: Response, signed_token: Optional[str]) -> None:
    if not signed_token:
        return

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        path="/",
    )


class ChatSessionStore:
    """Maps user-scoped client conversation keys to server-owned session IDs."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    client_conversation_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, client_conversation_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions (user_id)")
            conn.commit()

    @staticmethod
    def _normalize_session_id(session_id: Optional[str]) -> Optional[str]:
        if not session_id or session_id == "default_session":
            return None
        return session_id

    @staticmethod
    def _normalize_client_conv_id(client_conversation_id: Optional[str]) -> Optional[str]:
        if not client_conversation_id:
            return None
        return client_conversation_id.strip() or None

    def resolve_session_id(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        client_conversation_id: Optional[str] = None,
    ) -> str:
        normalized_session_id = self._normalize_session_id(session_id)
        normalized_client_id = self._normalize_client_conv_id(client_conversation_id)
        now = _utc_now_iso()

        with self._lock, self._connect() as conn:
            if normalized_session_id:
                row = conn.execute(
                    "SELECT user_id FROM chat_sessions WHERE session_id = ?",
                    (normalized_session_id,),
                ).fetchone()
                if row is None or row["user_id"] != user_id:
                    raise PermissionError("Session does not belong to authenticated user")

                conn.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                    (now, normalized_session_id),
                )
                conn.commit()
                return normalized_session_id

            if normalized_client_id:
                existing = conn.execute(
                    "SELECT session_id FROM chat_sessions WHERE user_id = ? AND client_conversation_id = ?",
                    (user_id, normalized_client_id),
                ).fetchone()

                if existing:
                    sid = existing["session_id"]
                    conn.execute(
                        "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                        (now, sid),
                    )
                    conn.commit()
                    return sid

            sid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, client_conversation_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, user_id, normalized_client_id, now, now),
            )
            conn.commit()
            return sid

    def resolve_existing_session_id(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        client_conversation_id: Optional[str] = None,
    ) -> Optional[str]:
        normalized_session_id = self._normalize_session_id(session_id)
        normalized_client_id = self._normalize_client_conv_id(client_conversation_id)

        with self._lock, self._connect() as conn:
            if normalized_session_id:
                row = conn.execute(
                    "SELECT user_id FROM chat_sessions WHERE session_id = ?",
                    (normalized_session_id,),
                ).fetchone()
                if row is None:
                    return None
                if row["user_id"] != user_id:
                    raise PermissionError("Session does not belong to authenticated user")
                return normalized_session_id

            if normalized_client_id:
                row = conn.execute(
                    "SELECT session_id FROM chat_sessions WHERE user_id = ? AND client_conversation_id = ?",
                    (user_id, normalized_client_id),
                ).fetchone()
                return row["session_id"] if row else None

        return None


chat_session_store = ChatSessionStore(SESSION_DB_PATH)


# Pydantic models
class TextQuery(BaseModel):
    question: str
    language: Optional[str] = "English"
    session_id: Optional[str] = None
    client_conversation_id: Optional[str] = None


class StreamQueryRequest(BaseModel):
    question: str
    language: Optional[str] = "English"
    session_id: Optional[str] = None
    client_conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    language: str
    sources: List[Dict[str, Any]]
    trust_score: Optional[float] = None
    evidence: Optional[List[Dict[str, Any]]] = None


class VoiceQueryResponse(BaseModel):
    original_text: str
    english_text: str
    detected_language: str
    answer: str
    sources: List[Dict[str, Any]]
    trust_score: Optional[float] = None
    evidence: Optional[List[Dict[str, Any]]] = None


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "English"


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str
    query: str
    response: str
    language: str
    session_id: Optional[str] = None
    category: Optional[str] = None
    comment: Optional[str] = None


class SessionClearRequest(BaseModel):
    session_id: Optional[str] = None
    client_conversation_id: Optional[str] = None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"\W+", (text or "").lower()) if t]


def _compute_trust_and_evidence(answer: str, sources: List[Dict[str, Any]], top_n: int = 3) -> tuple[float, List[Dict[str, Any]]]:
    """Compute an intuitive confidence score and evidence payload from retrieved sources."""
    safe_sources = sources or []
    top_sources = safe_sources[:top_n]

    if not top_sources:
        return 20.0, []

    raw_scores = [float(src.get("distance", 0.0) or 0.0) for src in top_sources]
    # Qdrant similarity is generally [0, 1], so keep source confidence absolute instead of relative.
    source_confidences = [_clamp(score, 0.0, 1.0) for score in raw_scores]
    top_confidence = source_confidences[0]
    avg_confidence = sum(source_confidences) / len(source_confidences)

    answer_tokens = set(_tokenize(answer))
    context_tokens = set(_tokenize(" ".join((src.get("content") or "") for src in top_sources)))
    if not answer_tokens or not context_tokens:
        coverage = 0.0
    else:
        coverage = len(answer_tokens.intersection(context_tokens)) / max(len(answer_tokens), 1)

    agreement = sum(1 for s in source_confidences if s >= 0.6) / max(len(source_confidences), 1)

    # Prioritize top result confidence while still accounting for corroboration and grounding.
    trust_0_1 = (0.55 * top_confidence) + (0.25 * avg_confidence) + (0.15 * coverage) + (0.05 * agreement)
    trust_score = round(_clamp(trust_0_1, 0.0, 1.0) * 100.0, 2)

    evidence: List[Dict[str, Any]] = []
    for idx, src in enumerate(top_sources):
        content = (src.get("content") or "").strip()
        snippet = content[:280] + ("..." if len(content) > 280 else "")
        evidence.append(
            {
                "rank": idx + 1,
                "score": round(source_confidences[idx] * 100.0, 2),
                "raw_score": round(raw_scores[idx], 6),
                "snippet": snippet,
                "metadata": src.get("metadata") or {},
            }
        )

    return trust_score, evidence


def get_rag_engine():
    """Lazily initialize the RAG engine with the workspace dataset."""
    global rag_engine

    if rag_engine is None:
        from backend.rag_engine import RAGEngine
        print("⏳ Initializing RAG Engine...")
        rag_engine = RAGEngine(data_path=str(DATA_PATH))
        print("✅ RAG Engine ready!")

    return rag_engine


def get_voice_processor():
    """Lazily initialize voice processing for audio queries."""
    global voice_processor

    if voice_processor is None:
        from backend.voice_processor import VoiceProcessor
        voice_processor = VoiceProcessor()

    return voice_processor


@app.on_event("startup")
async def startup_event():
    """Fast startup - models load on first request"""
    print("🚀 Server starting (models will load on first request)...")
    print("✅ Server ready!")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multilingual Voice RAG API",
        "status": "running",
        "endpoints": {
            "text_query": "/api/query",
            "voice_query": "/api/voice-query",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_engine": "initialized" if rag_engine else "not initialized",
        "voice_processor": "initialized" if voice_processor else "not initialized",
        "tts_service": "initialized" if tts_service and tts_service.enabled else "not available",
        "data_path": str(DATA_PATH.name)
    }


@app.post("/api/query", response_model=QueryResponse)
async def text_query(query: TextQuery, request: Request, response: Response):
    """Handle text-based queries with conversation memory"""
    try:
        engine = await run_in_threadpool(get_rag_engine)

        user_id, signed_token = _get_or_create_user_identity(request)
        _attach_user_cookie(response, signed_token)

        try:
            session_id = chat_session_store.resolve_session_id(
                user_id=user_id,
                session_id=query.session_id,
                client_conversation_id=query.client_conversation_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        
        # Process query with conversation memory
        result = await run_in_threadpool(
            engine.query,
            query.question,
            query.language,
            session_id,
        )

        trust_score, evidence = _compute_trust_and_evidence(result.get('answer', ''), result.get('sources', []))
        
        return QueryResponse(
            question=result['question'],
            answer=result['answer'],
            language=result['language'],
            sources=result['sources'],
            trust_score=trust_score,
            evidence=evidence,
        )
    
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query-stream")
async def text_query_stream(request: StreamQueryRequest, http_request: Request):
    """Stream text query response as Server-Sent Events (SSE)."""
    try:
        engine = await run_in_threadpool(get_rag_engine)
        user_id, signed_token = _get_or_create_user_identity(http_request)
        try:
            session_id = chat_session_store.resolve_session_id(
                user_id=user_id,
                session_id=request.session_id,
                client_conversation_id=request.client_conversation_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        def event_stream():
            try:
                for event in engine.stream_query(request.question, request.language or "English", session_id=session_id):
                    event_type = event.get("event", "message")
                    payload = {k: v for k, v in event.items() if k != "event"}

                    if event_type == "done":
                        trust_score, evidence = _compute_trust_and_evidence(
                            payload.get("answer", ""),
                            payload.get("sources", []),
                        )
                        payload["trust_score"] = trust_score
                        payload["evidence"] = evidence

                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield "event: error\n"
                yield f"data: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

        stream_response = StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        _attach_user_cookie(stream_response, signed_token)
        return stream_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice-query", response_model=VoiceQueryResponse)
async def voice_query(
    request: Request,
    response: Response,
    audio: UploadFile = File(...),
    language: Optional[str] = Form("auto"),
    session_id: Optional[str] = Form(None),
    client_conversation_id: Optional[str] = Form(None),
):
    """Handle voice-based queries"""
    # Save uploaded audio file
    temp_path = None
    try:
        engine = await run_in_threadpool(get_rag_engine)
        processor = await run_in_threadpool(get_voice_processor)
        user_id, signed_token = _get_or_create_user_identity(request)
        _attach_user_cookie(response, signed_token)

        try:
            resolved_session_id = chat_session_store.resolve_session_id(
                user_id=user_id,
                session_id=session_id,
                client_conversation_id=client_conversation_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        # Create temporary file
        suffix = Path(audio.filename).suffix or '.wav'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(audio.file, temp_file)
        
        # Process voice
        original_text, english_text, detected_lang = await run_in_threadpool(
            processor.process_voice_query,
            temp_path,
            language,
        )
        
        # Use detected language if auto
        query_language = detected_lang if language == "auto" else language
        
        # Query RAG system with English text
        result = await run_in_threadpool(
            engine.query,
            english_text,
            query_language,
            resolved_session_id,
        )

        trust_score, evidence = _compute_trust_and_evidence(result.get('answer', ''), result.get('sources', []))
        
        return VoiceQueryResponse(
            original_text=original_text,
            english_text=english_text,
            detected_language=detected_lang,
            answer=result['answer'],
            sources=result['sources'],
            trust_score=trust_score,
            evidence=evidence,
        )
    
    except Exception as e:
        print(f"Error processing voice query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.get("/api/languages")
async def get_supported_languages():
    """Get list of supported languages (only those with excellent voice support)"""
    return {
        "languages": [
            {"code": "en", "name": "English", "nativeName": "English"},
            {"code": "hi", "name": "Hindi", "nativeName": "हिंदी"}
        ]
    }


class ChatSessionRequest(BaseModel):
    client_conversation_id: Optional[str] = None


@app.post("/api/chat/session")
async def create_or_resolve_chat_session(payload: ChatSessionRequest, request: Request, response: Response):
    """Create (or resolve) a server-owned session ID scoped to the authenticated user."""
    try:
        user_id, signed_token = _get_or_create_user_identity(request)
        _attach_user_cookie(response, signed_token)
        session_id = chat_session_store.resolve_session_id(
            user_id=user_id,
            client_conversation_id=payload.client_conversation_id,
        )
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.post("/api/session/clear")
async def clear_session_memory(request: SessionClearRequest, http_request: Request, response: Response):
    """Clear backend conversation memory for a specific client session."""
    try:
        user_id, signed_token = _get_or_create_user_identity(http_request)
        _attach_user_cookie(response, signed_token)

        engine = await run_in_threadpool(get_rag_engine)
        try:
            resolved_session_id = chat_session_store.resolve_existing_session_id(
                user_id=user_id,
                session_id=request.session_id,
                client_conversation_id=request.client_conversation_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        if not resolved_session_id:
            return {"success": True, "session_id": None}

        await run_in_threadpool(engine.clear_conversation, resolved_session_id)
        return {"success": True, "session_id": resolved_session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session memory: {str(e)}")


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using Microsoft Edge TTS (FREE)
    Returns base64-encoded MP3 audio
    """
    if not tts_service or not tts_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Using browser TTS fallback."
        )
    
    try:
        # Use async version of synthesize_speech
        audio_base64 = await tts_service.synthesize_speech_async(
            text=request.text,
            language=request.language
        )
        
        if not audio_base64:
            raise HTTPException(status_code=500, detail="TTS generation failed")
        
        return {
            "audio": audio_base64,
            "format": "mp3"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@app.post("/api/tts-synced")
async def text_to_speech_synced(request: TTSRequest):
    """
    Convert text to speech with word-level timing information
    Returns base64-encoded MP3 audio + word timings for synchronized playback
    Perfect for highlighting words as they're spoken!
    """
    if not tts_service or not tts_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available"
        )
    
    try:
        # Use the new synced method
        result = await tts_service.synthesize_speech_with_timings_async(
            text=request.text,
            language=request.language
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Synced TTS generation failed")
        
        return result  # Returns { audio, timings, format }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synced TTS error: {str(e)}")

# Feedback endpoints
@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback"""
    try:
        feedback_record = feedback_service.submit_feedback(
            message_id=request.message_id,
            rating=request.rating,
            query=request.query,
            response=request.response,
            language=request.language,
            session_id=request.session_id,
            category=request.category,
            comment=request.comment
        )
        return {"success": True, "feedback_id": feedback_record["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics"""
    try:
        return feedback_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/elevenlabs-status")
async def get_elevenlabs_status():
    """Get ElevenLabs account subscription and character usage"""
    try:
        if elevenlabs_tts_service.enabled:
            status = elevenlabs_tts_service.get_subscription_status()
            if status:
                return {"success": True, "status": status}
            else:
                return {"success": False, "error": "Could not fetch subscription status"}
        else:
            return {"success": False, "error": "ElevenLabs not configured"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

