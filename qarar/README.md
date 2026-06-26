# Qarar

Qarar is a Decision Intelligence copilot for the Abu Dhabi AI PropTech Challenge. It ranks districts by community demand vs OSM amenity supply, surfaces vacant parcels and matched investors, and renders an interactive map with a structured decision brief — all from the challenge datasets. The project is a **Next.js + TypeScript frontend** (`web/`) talking to a **FastAPI backend** (`qarar/`) that runs the deterministic pandas pipeline, with an optional LLM multi-hop tool-calling path and live price reconciliation.

## Architecture

```
web/      Next.js + TypeScript + Tailwind UI (MapLibre map + decision brief)
qarar/    FastAPI backend wrapping the Python decision pipeline
data/     Challenge CSV datasets (+ real OSM amenities)
```

The browser calls `POST /api/answer { question }` and the backend returns a `Brief` (headline, reasoning steps, recommended parcel, matched investors, map layers, sources). The pipeline runs **with no API keys** (deterministic); setting `LLM_PROVIDER` + a key enables the agentic path.

## Run it (two terminals)

**1. Backend** (Python 3.10+):

```bash
pip install -r qarar/requirements.txt
uvicorn api:app --app-dir qarar --port 8000
```

**2. Frontend** (Node 18+):

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

The frontend defaults to the backend at `http://localhost:8000` (override with `NEXT_PUBLIC_QARAR_API` in `web/.env.local`).

## Environment variables (backend)

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `none` (default), `anthropic`, or `openai` |
| `LLM_MODEL` | Override default model |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | LLM keys (enable the agentic path) |
| `UAE_DATA_API_KEY` | eVoost live listings API key (enables price reconciliation) |
| `QARAR_CORS_ORIGINS` | Extra allowed origins (any localhost port is allowed by default) |

## Inspect data

```bash
python qarar/inspect_data.py
```
