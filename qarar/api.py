"""FastAPI backend for Qarar — serves the deterministic/LLM decision pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load qarar/.env (and the repo root .env) so keys like UAE_DATA_API_KEY,
# ANTHROPIC_API_KEY, or OPENAI_API_KEY are available without exporting them.
try:
    from dotenv import load_dotenv

    _here = Path(__file__).resolve().parent
    load_dotenv(_here / ".env")
    load_dotenv(_here.parent / ".env")
except ModuleNotFoundError:
    pass

import data_layer
import llm
import map_view
from agent import HERO_QUESTION, answer, map_layers_for

app = FastAPI(title="Qarar API", version="1.0.0")

_extra_origins = os.environ.get("QARAR_CORS_ORIGINS", "")

app.add_middleware(
    CORSMiddleware,
    # Allow any localhost port in dev (Next may use 3000, 3001, …)
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_origins=[o.strip() for o in _extra_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerRequest(BaseModel):
    question: str = HERO_QUESTION


class SimulateRequest(BaseModel):
    district: str | None = None
    population_delta: int = 0
    build_parcel: bool = False
    add_amenity_category: str | None = None
    add_amenity_count: int = 0


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_available": llm.is_llm_available(),
        "provider": os.environ.get("LLM_PROVIDER", "none"),
    }


@app.get("/api/hero-question")
def hero_question() -> dict:
    return {"question": HERO_QUESTION}


@app.get("/api/districts")
def districts() -> dict:
    df = data_layer.load_districts()
    dcol = "district" if "district" in df.columns else df.columns[0]
    return {"districts": sorted(df[dcol].astype(str).tolist())}


@app.get("/api/parcels")
def parcels(district: str) -> dict:
    return {
        "district": district,
        "parcels": data_layer.get_district_parcels(district),
    }


@app.get("/api/overview")
def overview() -> dict:
    import json as _json

    df = data_layer.get_city_overview()
    rows = _json.loads(df.to_json(orient="records"))
    worst = rows[0] if rows else None
    return {"rows": rows, "worst": worst}


@app.get("/api/map")
def map_choropleth(
    layer: str = map_view.DEFAULT_LAYER,
    year: int | None = None,
    highlight: str | None = None,
) -> dict:
    return map_view.build_choropleth(
        layer=layer, year=year, highlight_district=highlight
    )


@app.post("/api/answer")
def post_answer(req: AnswerRequest) -> dict:
    brief = answer(req.question)
    return brief.to_dict()


@app.post("/api/simulate")
def post_simulate(req: SimulateRequest) -> dict:
    overrides: dict = {}
    if req.district:
        overrides["district"] = req.district
    if req.population_delta:
        overrides["population_delta"] = int(req.population_delta)
    if req.add_amenity_count and req.add_amenity_category:
        overrides["add_amenities"] = {
            "category": req.add_amenity_category,
            "count": int(req.add_amenity_count),
        }

    parcel_pin = None
    if req.build_parcel and req.district:
        parcels = data_layer.find_vacant_parcels(req.district, min_potential=0)
        if not parcels.empty:
            pid = str(parcels.iloc[0]["parcel_id"])
            overrides["develop_parcel"] = pid

    result = data_layer.scenario_compare(overrides)

    # Re-render map for the focus district (or the new worst district).
    focus = req.district or result["scenario_worst"]["district"]
    if req.build_parcel and "develop_parcel" in overrides:
        parcel_row = data_layer.find_vacant_parcels(focus, min_potential=0)
        if not parcel_row.empty:
            r = parcel_row.iloc[0]
            lat, lon = data_layer.parcel_pin_coords(focus, str(r["parcel_id"]))
            parcel_pin = {"latitude": lat, "longitude": lon, "parcel_id": str(r["parcel_id"])}

    result["map_layers"] = map_layers_for(focus)
    if parcel_pin:
        result["map_layers"]["parcel_pin"] = parcel_pin
    result["focus_used"] = focus
    return result
