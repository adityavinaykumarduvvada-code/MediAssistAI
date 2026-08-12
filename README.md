# MediAssist AI

Turn confusing medical paperwork — blood reports, X-rays, MRI/CT reports,
prescriptions — into a plain-language explanation, grounded in trusted
medical reference material, with the exact questions to bring to your
next doctor's visit.

> **This is an educational tool, not a diagnostic device.** A dedicated
> Safety/Verification Agent reviews every generated report before it
> reaches the patient, softening any language that reads like a
> confirmed diagnosis and stripping references that weren't actually
> retrieved from the knowledge base.

---

## Architecture

```
        User / Doctor
              │
              ▼
     Multimodal Input (PDF / image upload)
              │
              ▼
     Agentic Orchestrator            classify + route each uploaded file
              │
    ┌─────────┼─────────┐
    ▼         ▼          ▼
Blood     Imaging     Drug Agent      parallel — each grounded in its own
Agent     Agent                       RAG collection (Blood/Imaging/Drug)
    │         │          │
    └─────────┼─────────┘
              ▼
     Patient Digital Twin      deterministic merge of everything
              │                extracted so far (no LLM call — can't fail)
              ▼
     Medical Knowledge Graph   links extracted entities (labs, meds,
              │                findings) to the reference passages that
              │                ground them (no LLM call — can't fail)
              ▼
     Clinical Reasoning Agent  LLM reasons over the twin + graph context
              │                to draft possible conditions + evidence
              ▼
     Safety / Verification     rule-based guardrails: hedges overclaiming
     Agent                     language, filters hallucinated citations,
              │                guarantees a follow-up question + disclaimer
              ▼
     Explainable Response + Evidence  →  React dashboard
```

Orchestration is a **LangGraph** graph (`backend/agents/graph.py`) with a
genuine parallel fan-out/fan-in: the Orchestrator routes to three domain
agents that run concurrently, which join into the Digital Twin, then flow
linearly through the Knowledge Graph → Clinical Reasoning → Safety stages.

**Every node is defensive.** A failure in any single agent (a bad API
response, an unreadable file, a network hiccup) is caught, logged to the
visible pipeline trace, and degrades gracefully — it never crashes the
whole request. The FastAPI app also has a global exception handler as a
final backstop, so any unexpected error returns clean JSON with the real
cause instead of an opaque `500`.

## Stack

| Layer            | Technology                                   |
|-------------------|-----------------------------------------------|
| Frontend          | React 18 + Vite + Tailwind CSS                |
| Backend            | FastAPI                                       |
| Agent orchestration| LangGraph                                     |
| LLM                | Google Gemini (free tier, text + vision) by default — Groq or Anthropic also supported |
| RAG / retrieval    | ChromaDB, one collection per domain (Blood / Imaging / Drug RAG) |
| PDF parsing        | PyMuPDF                                       |
| Session storage     | SQLite (SQLAlchemy)                          |

## Project layout

```
MediAssistAI/
  backend/
    app.py                        FastAPI entrypoint + global exception handler
    agents/
      orchestrator.py              file classification & routing
      blood_agent.py                blood/lab report extraction, grounded in Blood RAG
      drug_agent.py                 prescription extraction, grounded in Drug RAG
      imaging_agent.py              vision analysis of scans, grounded in Imaging RAG
      digital_twin.py               deterministic merge into one patient snapshot
      knowledge_graph.py            entity/reference graph builder
      clinical_reasoning_agent.py   LLM reasoning over the twin + graph
      safety_agent.py               rule-based guardrails on the final report
      graph.py                      LangGraph wiring (the diagram above)
    rag/
      knowledge_base/
        blood/ imaging/ drug/       seed reference docs, one folder per domain
      ingest.py                     chunks + embeds each domain into its own Chroma collection
      vector_store.py               Chroma client wrapper (multi-collection)
      retriever.py                  domain-scoped + cross-domain retrieval helpers
    core/
      config.py                     env-driven settings, provider selection
      llm_client.py                 Gemini / Groq / Anthropic wrapper (text + vision)
    models/schemas.py             Pydantic contracts shared across agents
    database/db.py                SQLite session/report persistence
    requirements.txt
    Dockerfile
    .env.example
  frontend/
    src/
      components/                  Header, Hero, UploadPanel, PipelineTracker (8 stages), LabValueTable...
      pages/Results.jsx             results dashboard, incl. Safety Agent transparency notes
      api/client.js                 backend API client
    Dockerfile
    nginx.conf
    .env.example
  docker-compose.yml
```

---

## Run it locally

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set GEMINI_API_KEY=... (get one free, no card, at
# https://aistudio.google.com/app/apikey)

python -m rag.ingest        # embeds the domain knowledge bases into ChromaDB
uvicorn app:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (docs at `/docs`).

### Choosing an LLM provider (free vs paid)

Set `LLM_PROVIDER` in `backend/.env` — everything else is one env var away,
no code changes:

| Provider | Cost | Text | Vision (X-ray/MRI) | Get a key |
|---|---|---|---|---|
| `gemini` (default) | Free, no credit card | ✅ | ✅ | https://aistudio.google.com/app/apikey |
| `groq` | Free, no credit card | ✅ (very fast) | ❌ — falls back to Gemini, so set `GEMINI_API_KEY` too | https://console.groq.com/keys |
| `anthropic` | Paid (small free trial credit) | ✅ | ✅ | https://console.anthropic.com |

Free tiers are rate-limited (requests per minute/day), which is fine for
personal use and demos but not for production traffic — see the Deploying
section below.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env       # defaults to /api via the Vite dev proxy — usually no edits needed
npm run dev
```

Visit `http://localhost:5173`.

---

## Run it with Docker (recommended for deployment)

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set your GEMINI_API_KEY (or switch LLM_PROVIDER)

docker compose up --build
```

- Frontend served on `http://localhost` (port 80), proxying `/api` to the backend container.
- Backend on `http://localhost:8000`.
- Uploaded files, the Chroma vector store, and the SQLite DB persist in named Docker volumes across restarts.

### Deploying to the cloud

This is a standard two-service app, so it fits any of the usual paths:

- **Render / Railway / Fly.io**: deploy `backend/` as a Docker web service
  and `frontend/` as a static site (or its own Docker service pointed at
  the backend's public URL via `VITE_API_URL`).
- **A single VM**: `docker compose up -d --build` behind an nginx/Caddy
  reverse proxy with TLS.
- **Kubernetes**: the two Dockerfiles map directly to two Deployments +
  Services; mount the same three volumes (uploads, chroma_store,
  database) as a PVC on the backend pod.

Either way, only one secret is required (`GEMINI_API_KEY` by default).

---

## Extending the knowledge base

Drop more `.md`/`.txt` files (ideally paraphrased/summarized WHO, NIH, or
licensed textbook content — check licensing before ingesting copyrighted
material verbatim) into `backend/rag/knowledge_base/<domain>/`, where
`<domain>` is `blood`, `imaging`, or `drug`, then run:

```bash
python -m rag.ingest
```

It's idempotent (content-hash based upsert), so re-running after adding
files only embeds what's new. Adding a new domain (e.g. `cardiology`)
means: create the folder, add it to `DOMAIN_COLLECTIONS` in
`backend/rag/vector_store.py`, and point whichever agent should use it
at `retrieve_for_topics("cardiology", ...)`.

## Swapping models

- **Text/vision LLM**: switch `LLM_PROVIDER` in `.env` between `gemini`,
  `groq`, and `anthropic` — no code changes needed. To add a different
  provider entirely (OpenAI, local Ollama, etc.), add one function to
  `backend/core/llm_client.py`; every agent calls only through that file.
- **Vision for imaging**: for higher clinical fidelity than a general
  vision-language model, point `imaging_agent.py` at a dedicated medical
  imaging model (e.g. a fine-tuned Florence-2 or Qwen2.5-VL endpoint)
  behind the same `analyze_image()` interface.
- **Embeddings**: swap the embedding function in `backend/rag/vector_store.py`.
- **Medical Knowledge Graph**: `backend/agents/knowledge_graph.py` currently
  builds a lightweight in-memory entity/reference graph per request. It's
  structured as the single integration point for a real graph database
  (e.g. Neo4j over UMLS/SNOMED-CT) later — only that file would need to
  change; the Clinical Reasoning Agent just consumes `KnowledgeGraphContext`.

## Safety notes baked into the design

- The Imaging Agent's system prompt explicitly forbids asserting a
  confirmed diagnosis and requires hedged language.
- The Clinical Reasoning Agent is instructed to reason **only** from the
  Digital Twin + Knowledge Graph context — not from unconstrained model
  knowledge.
- The **Safety/Verification Agent** is a separate, deterministic
  (non-LLM) pass that: softens any overclaiming language that slips
  through, strips citations that weren't actually retrieved, and
  guarantees a follow-up question and disclaimer are always present. It
  records what it changed in `safety_notes`, shown in the UI for
  transparency.
- Every generated report carries a visible, non-removable disclaimer
  banner in the UI.
- Every agent node catches its own failures and logs them to the visible
  pipeline trace rather than crashing the request; a global FastAPI
  exception handler is the final backstop.

This project is a strong educational/demo-grade system. Before any real
clinical use, it would need: licensed guideline sources (not the sample
seed docs included here), a real persisted medical knowledge graph, a
HIPAA/GDPR-compliant storage and auth layer, audit logging, and clinical
validation — none of which are in scope for this build.
