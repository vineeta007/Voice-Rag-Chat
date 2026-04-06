# Streaming TTS Implementation Plan

## Goal

Enable true real-time behavior where the assistant starts speaking while text is still being generated, instead of waiting for the full response.

## Current State

- Text generation is request/response (full answer arrives first).
- TTS starts only after full text is available.
- Word highlighting has been disabled by request while voice remains enabled.

## Architecture Target

- Backend streams text deltas (SSE).
- Frontend renders deltas as they arrive.
- Backend/Frontend perform sentence chunking for incremental TTS.
- Frontend plays chunked audio queue continuously.

## Phase Plan

### Phase 0: Stability Baseline (in progress)

- [x] Fix Render startup/port/CORS issues.
- [x] Move heavy query work off event loop.
- [x] Increase frontend timeout and add retry for transient 502/timeout.
- [x] Reduce health polling aggressiveness on Render.

### Phase 1: Stream Text Deltas

Backend:

- [x] Add SSE endpoint `POST /api/query-stream`.
- [x] Add streaming generation method in RAG layer (yield token/delta events).
- [x] Send SSE events: `meta`, `delta`, `sentence`, `done`, `error`.

Frontend:

- [x] Add stream consumer in API layer.
- [x] Update chat message progressively with incoming `delta` chunks.
- [x] Keep existing non-stream endpoint as fallback.

Definition of done:

- [x] User sees text appear token-by-token in UI.

### Phase 2: Incremental TTS Queue (Speak While Generating)

Backend/Frontend:

- [x] Chunk text by punctuation and max length threshold.
- [x] Trigger TTS for each completed chunk (sentence-like unit).
- [x] Push audio chunks into queue while more text is still arriving.

Audio pipeline:

- [ ] Maintain 1-2 chunk prebuffer for smooth playback.
- [x] Preserve stop button behavior to cancel queue and pending chunks.

Definition of done:

- [x] AI starts speaking before final response text completes.

### Phase 2 Notes (Current)

- SSE `sentence` events now emit on punctuation and length threshold fallback.
- Frontend queues TTS per incoming sentence chunk during stream.
- Existing stop button continues to cancel active queue/playback.
- Prebuffer tuning is intentionally left for Phase 3 hardening.

### Phase 3: Production Hardening

- [x] Add timeout/cancellation handling for stream + TTS requests.
- [x] Add retries for chunk TTS transient failures.
- [x] Add lightweight telemetry logs for stream start/end and chunk timings.
- [x] Add graceful fallback to full-response TTS if stream path fails.

Definition of done:

- [ ] Stream path stable under Render free-tier cold starts and occasional 502.

### Phase 3 Notes (Current)

- Stream path now supports abort signals, global timeout, and inactivity timeout.
- Chunked TTS now retries transient failures and applies per-request timeout.
- Backend stream lifecycle telemetry (`start`, `done`, `error`) added with timings.
- Frontend falls back to non-stream query + full-response TTS when streaming fails.

## Event Contract (Draft)

SSE events from backend:

- `meta`: query metadata and language
- `delta`: incremental text chunk
- `sentence`: complete sentence/chunk boundary
- `done`: final aggregated answer
- `error`: error message

## Rollout Strategy

1. Deploy Phase 1 behind feature flag `VITE_STREAMING_TEXT=true`.
2. Validate in local + Render.
3. Enable Phase 2 chunked TTS on selected environment.
4. Keep old `/api/query` path as fallback until stable.

## Risks and Mitigations

- Render cold-start and instance churn:
  - Use retries and longer timeout.
- SSE through proxies:
  - Keep heartbeat comments and conservative reconnect policy.
- TTS latency spikes:
  - Use chunk queue with prebuffer and fallback mode.

## Verification Checklist

- [ ] Text starts appearing before full answer complete.
- [ ] Voice starts before full answer complete.
- [ ] Stop button interrupts immediately.
- [ ] No UI freeze or repeated offline flicker during normal usage.
- [ ] Fallback non-stream mode remains functional.
