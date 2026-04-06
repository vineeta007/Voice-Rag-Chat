# Trust Score + Evidence Panel

This document describes the Trust Score + Evidence Panel feature end-to-end so teammates can reuse the content in:

- research writeups
- internal reports
- demo narratives
- methodology sections in papers

## 1. Feature Goal

The feature makes Retrieval-Augmented Generation (RAG) outputs more transparent by attaching:

- a single confidence value for the final answer
- ranked supporting evidence snippets from retrieved context
- explicit separation of strong support vs weak context in the UI

It is designed to answer this question for users and reviewers:

"How strongly is this answer supported by retrieved university data?"

## 2. Why This Matters for Research

RAG systems are often evaluated only by final answer quality. This feature adds a lightweight confidence/explainability layer that supports:

- interpretability in user-facing deployments
- error analysis during model/retrieval iteration
- trust calibration analysis in research reporting
- reproducible evidence presentation in demo and faculty review

## 3. Scope and Current Behavior

The implementation currently includes:

- backend computation of trust_score and evidence for text and voice responses
- backend inclusion of trust_score and evidence in streaming final events
- frontend rendering of confidence chip + evidence panel
- frontend grouping of evidence into:
  - strong evidence: score >= 20
  - weak context: score < 20

## 4. Implementation Map

### Backend

- File: backend/main.py
- Key function: \_compute_trust_and_evidence(answer, sources, top_n=3)
- Applied in endpoints:
  - POST /api/query
  - POST /api/voice-query
  - POST /api/query-stream (done event payload)

### Frontend

- API contracts: frontend/src/services/api.ts
- Message wiring: frontend/src/App.tsx
- Panel rendering: frontend/src/components/ChatInterface.tsx
- Panel styling: frontend/src/components/ChatInterface.css

## 5. Mathematical Definition

Let top-k retrieved sources be S = {s1, s2, ..., sk}, where k <= 3.

For each source si:

- raw retrieval score: ri (from vector search)
- normalized source confidence:

ci = clamp(ri, 0, 1)

### 5.1 Intermediate Components

- Top confidence:

c_top = c1

- Average confidence:

c_avg = (1/k) \* sum(ci)

- Answer-context token coverage:

coverage = |tokens(answer) ∩ tokens(concatenated_context)| / |tokens(answer)|

- Agreement ratio:

agreement = (number of sources with ci >= 0.6) / k

### 5.2 Final Trust Score

trust_0_1 = 0.55*c_top + 0.25*c_avg + 0.15*coverage + 0.05*agreement

trust_score = round(100 \* clamp(trust_0_1, 0, 1), 2)

### 5.3 Evidence Item Score

evidence_score_i = round(100 \* ci, 2)

Each evidence item also includes:

- rank
- raw_score
- snippet (truncated context)
- metadata

## 6. API Contract

### Query/Voice Response

Additional fields in response payload:

- trust_score: number (0 to 100)
- evidence: array of objects

Evidence object schema:

- rank: integer
- score: number (percentage)
- raw_score: number
- snippet: string
- metadata: object

### Streaming Response

On SSE done event, payload includes:

- trust_score
- evidence

This keeps streamed and non-streamed behavior consistent.

## 7. UI Semantics (Current)

The UI presents:

- Answer Confidence: X%
- View Evidence (N): only strong evidence count
- Evidence summary line:
  - "A strong sources, B weak sources"
- Weak Context section (collapsible): shows low-score items separately

This avoids showing weak context as if it were equally strong evidence.

## 8. Interpretation Guidance

### Recommended wording for reports

- High confidence: answer strongly aligns with top retrieved context.
- Medium confidence: answer is partially grounded; verify details if high-stakes.
- Low confidence: weak retrieval grounding or low context agreement; treat as tentative.

### Important caveat

Trust score is a grounding/confidence proxy, not a proof of factual correctness.

A high score means strong alignment with retrieved context, which itself may still contain stale or incomplete information.

## 9. Suggested Research Reporting Template

Use this structure in your paper/report.

### 9.1 Feature Description

"We augment RAG outputs with a confidence-weighted evidence panel. Confidence is computed from top-source strength, average source support, lexical answer-context grounding, and source agreement."

### 9.2 Evaluation Questions

- Does trust_score correlate with human-rated answer correctness?
- Does evidence visibility reduce user over-trust in weak responses?
- Does weak-context separation improve reviewer interpretability?

### 9.3 Metrics to Include

- calibration correlation (trust_score vs human correctness)
- bucket accuracy (0-40, 40-70, 70-100)
- acceptance/revision rate by confidence bucket
- hallucination rate by confidence bucket

### 9.4 Ablation Table (recommended)

Compare:

- full formula (all components)
- without coverage term
- without agreement term
- top-confidence only baseline

## 10. Reproducibility Checklist

Before final report submission:

1. Confirm backend returns trust_score and evidence for all query modes.
2. Confirm stream done event includes trust metadata.
3. Confirm UI separates strong evidence and weak context.
4. Verify at least 20-30 representative queries across categories.
5. Log examples with:
   - user question
   - final answer
   - trust_score
   - evidence list
   - reviewer judgment

## 11. Known Limitations

- Confidence uses token overlap coverage, which is lexical and may miss semantic paraphrases.
- Absolute source confidence depends on retrieval score quality/calibration.
- Weak evidence threshold (20) is heuristic and currently static.
- No per-domain dynamic calibration yet.

## 12. Next-Step Improvements (Optional)

- semantic coverage via embedding overlap instead of token overlap
- confidence calibration per category/domain
- confidence interval reporting (not only point estimate)
- user-facing tooltip explaining confidence components
- offline calibration study using human labels

## 13. One-Paragraph Summary for Team Use

The Trust Score + Evidence Panel provides a transparent confidence layer on top of RAG answers by combining retrieval strength, context coverage, and source agreement into a 0-100 score, while exposing ranked support snippets. The UI now distinguishes strong evidence from weak context, improving interpretability and reducing misleading "all evidence is equally strong" perception. This feature supports both product trust and research reporting by making answer grounding measurable, inspectable, and reproducible.
