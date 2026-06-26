"""Decision loop: deterministic fallback + optional LLM multi-hop tool calling."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

import data_layer
import live_data
import llm
from tools import execute_tool, tool_schemas_for_llm

HERO_QUESTION = "Where is Abu Dhabi most underserved, and what should we do about it?"
MAX_TOOL_ITERATIONS = 8

SOURCES = [
    "sample_communities.csv · service_demand_index",
    "sample_communities.csv · population_estimate",
    "osm_amenities.csv · district",
    "osm_amenities.csv · category",
    "districts.csv · base_sale_aed_sqm",
    "districts.csv · latitude",
    "sample_parcels.csv · development_potential_score",
    "sample_parcels.csv · current_status",
    "sample_investors.csv · preferred_sector",
]


@dataclass
class Brief:
    headline: str
    district: str
    reasoning_steps: list[str]
    recommended_parcel: dict | None
    matched_investors: list[dict]
    map_layers: dict
    sources: list[str]
    live_reconciliation: dict | None = None
    mode: str = "deterministic"
    tool_call_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _parcel_to_dict(row: pd.Series) -> dict:
    out: dict = {}
    for k, v in row.items():
        if pd.isna(v):
            out[k] = None
        elif k.endswith(("_aed", "_score", "_sqm")) or k in ("parcel_size_sqm", "development_potential_score"):
            out[k] = int(v)
        else:
            out[k] = v
    return out


def _build_map_layers(
    district: str,
    amenities: pd.DataFrame,
    parcel: dict | None,
) -> dict:
    profile = data_layer.get_district_profile(district)
    centroid = {
        "latitude": profile["latitude"],
        "longitude": profile["longitude"],
        "district": district,
    }

    amenity_points = []
    lat_c = "latitude" if "latitude" in amenities.columns else None
    lon_c = "longitude" if "longitude" in amenities.columns else None
    if lat_c and lon_c and not amenities.empty:
        sample = amenities.head(500)
        for _, row in sample.iterrows():
            amenity_points.append(
                {
                    "latitude": float(row[lat_c]),
                    "longitude": float(row[lon_c]),
                    "name": str(row.get("name", "")),
                    "category": str(row.get("category", "")),
                }
            )

    parcel_pin = None
    if parcel and "parcel_id" in parcel:
        plat, plon = data_layer.parcel_pin_coords(district, str(parcel["parcel_id"]))
        parcel_pin = {
            "latitude": plat,
            "longitude": plon,
            "parcel_id": parcel["parcel_id"],
        }

    return {
        "centroid": centroid,
        "amenities": amenity_points,
        "parcel_pin": parcel_pin,
    }


def map_layers_for(district: str, parcel: dict | None = None) -> dict:
    """Public helper: build map layers (centroid, amenities, optional pin) for a district."""
    amenities = data_layer.get_amenities(district)
    return _build_map_layers(district, amenities, parcel)


def compose_brief(
    district: str,
    gap_row: pd.Series | dict,
    amenities: pd.DataFrame,
    parcel: dict | None,
    investors: list[dict],
    live_reconciliation: dict | None,
    mode: str = "deterministic",
    tool_call_count: int = 0,
    headline: str | None = None,
    intro_step: str | None = None,
) -> Brief:
    if isinstance(gap_row, pd.Series):
        gap = gap_row.to_dict()
    else:
        gap = gap_row

    gap_score = gap.get("gap_score", gap.get("service_demand", "N/A"))
    service_demand = gap.get("service_demand", "N/A")
    amenity_count = gap.get("amenity_count", len(amenities))
    amenity_per_capita = gap.get("amenity_per_capita")
    population = gap.get("population_total", gap.get("population", "N/A"))

    pop_str = f"{int(population):,}" if isinstance(population, (int, float)) else str(population)
    demand_str = f"{service_demand:.1f}" if isinstance(service_demand, (int, float)) else str(service_demand)
    step_one = intro_step or (
        f"Ranked all districts by community demand vs OSM amenity supply — "
        f"{district} scores gap {gap_score}/100 (worst-first)."
    )
    steps = [
        step_one,
        f"Population {pop_str} with weighted service demand index {demand_str}.",
        (
            f"Only {amenity_count} OSM amenities ({amenity_per_capita:.6f} per capita) — supply lags demand."
            if amenity_per_capita is not None
            else f"Found {amenity_count} OSM amenities in {district}."
        ),
    ]

    if parcel:
        steps.append(
            f"Top vacant parcel {parcel.get('parcel_id')}: {parcel.get('land_use')} land, "
            f"development potential {parcel.get('development_potential_score')}, "
            f"estimated value AED {parcel.get('estimated_value_aed', 0):,}."
        )
    else:
        steps.append("No vacant parcels above development potential threshold in this district.")

    if investors:
        ids = ", ".join(i.get("investor_id", "?") for i in investors[:3])
        steps.append(f"Matched {len(investors)} investors for sector — top: {ids}.")
    else:
        steps.append("No investor mandates matched the recommended sector.")

    if live_reconciliation:
        steps.append(
            f"Live price check: median AED {live_reconciliation['live_median']:,}/sqm vs "
            f"synthetic baseline AED {live_reconciliation['synthetic_baseline']:,}/sqm "
            f"({live_reconciliation['pct_delta']:+.1f}%), "
            f"{live_reconciliation['n_mislabeled_rent_vs_sale']} mislabeled rent/sale rows."
        )

    if headline is None:
        headline = (
            f"Invest in {district}: highest amenity gap ({gap_score}/100) — "
            f"deploy community infrastructure on vacant land"
        )
        if parcel:
            headline = (
                f"{district} is Abu Dhabi's most underserved district — "
                f"develop {parcel.get('parcel_id')} ({parcel.get('land_use')}) to close the gap"
            )

    return Brief(
        headline=headline,
        district=district,
        reasoning_steps=steps,
        recommended_parcel=parcel,
        matched_investors=investors,
        map_layers=_build_map_layers(district, amenities, parcel),
        sources=SOURCES,
        live_reconciliation=live_reconciliation,
        mode=mode,
        tool_call_count=tool_call_count,
    )


_SECTOR_KEYWORDS = {
    "residential": ["residential", "housing", "homes", "apartment", "living"],
    "commercial": ["commercial", "office", "retail", "shop", "mall"],
    "hospitality": ["hospitality", "hotel", "tourism", "resort", "leisure"],
    "logistics": ["logistics", "warehouse", "distribution", "freight"],
    "industrial": ["industrial", "factory", "manufacturing"],
    "mixed_use": ["mixed use", "mixed-use", "mixed_use"],
    "community": ["community", "school", "education", "clinic", "health",
                  "hospital", "nursery", "social", "amenity", "amenities"],
}


def _question_district(question: str) -> str | None:
    """Return the longest district name mentioned in the question, if any."""
    q = question.lower()
    names = data_layer.load_districts()
    dcol = "district" if "district" in names.columns else names.columns[0]
    matches = [d for d in names[dcol].astype(str) if d.lower() in q]
    return max(matches, key=len) if matches else None


def _question_sector(question: str) -> str | None:
    q = question.lower()
    for sector, keywords in _SECTOR_KEYWORDS.items():
        if any(k in q for k in keywords):
            return sector
    return None


def _question_intent(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ["investor", "capital", "fund", "finance", "backer", "deploy capital", "match"]):
        return "investors"
    if any(k in q for k in ["price", "prices", "overpriced", "underpriced", "compare", "reconcile", "live"]):
        return "prices"
    if any(k in q for k in ["vacant", "parcel", "plot", "land", "build", "develop", "site"]):
        return "parcels"
    return "gap"


def _asks_for_ranking(question: str) -> bool:
    q = question.lower()
    return any(
        k in q
        for k in ["districts", "which district", "where are", "most unmet", "rank", "highest demand"]
    )


def _price_reconciliation(district: str) -> dict | None:
    live = live_data.cross_check_live_prices(district)
    if live:
        live["source"] = "live_listings"
        return live
    return data_layer.get_transaction_price_comparison(district)


def _district_for_price_focus(gaps: pd.DataFrame, asked_district: str | None) -> str:
    if asked_district:
        return asked_district
    best_district = gaps.iloc[0]["district"]
    best_delta = -1.0
    for district in gaps["district"]:
        rec = _price_reconciliation(str(district))
        if rec and abs(rec["pct_delta"]) > best_delta:
            best_delta = abs(rec["pct_delta"])
            best_district = str(district)
    return best_district


def _format_ranking(gaps: pd.DataFrame, n: int = 5) -> str:
    parts = [
        f"{row['district']} ({row['gap_score']}/100)"
        for _, row in gaps.head(n).iterrows()
    ]
    return ", ".join(parts)


def _pipeline_gap(
    question: str,
    gaps: pd.DataFrame,
    asked_district: str | None,
    asked_sector: str | None,
) -> Brief:
    if asked_district:
        match = gaps[gaps["district"].str.lower() == asked_district.lower()]
        gap_row = match.iloc[0] if not match.empty else gaps.iloc[0]
        district = gap_row["district"]
        intro_step = (
            f"Focused on {district} as requested — gap score "
            f"{gap_row.get('gap_score')}/100 vs the emirate ranking."
        )
        headline = (
            f"{district}: gap score {gap_row.get('gap_score')}/100 — "
            "priority for community infrastructure investment."
        )
    else:
        gap_row = gaps.iloc[0]
        district = gap_row["district"]
        if _asks_for_ranking(question):
            intro_step = (
                f"Ranked all districts by community demand vs OSM amenity supply — "
                f"top unmet demand: {_format_ranking(gaps)}."
            )
            headline = (
                f"{district} leads unmet service demand at {gap_row.get('gap_score')}/100 — "
                f"followed by {_format_ranking(gaps.iloc[1:], 2)}"
            )
        else:
            intro_step = (
                f"Ranked all districts by community demand vs OSM amenity supply — "
                f"{district} scores gap {gap_row.get('gap_score')}/100 (worst-first)."
            )
            headline = None

    amenities = data_layer.get_amenities(district)
    parcels_df = data_layer.find_vacant_parcels(district, min_potential=70)
    parcel_dict, sector, capital = _pick_parcel(parcels_df, asked_sector)
    investors = _match_investors_list(sector, capital)
    live_rec = _price_reconciliation(district)

    if headline is None and parcel_dict:
        headline = (
            f"{district} is Abu Dhabi's most underserved district — "
            f"develop {parcel_dict.get('parcel_id')} ({parcel_dict.get('land_use')}) to close the gap"
        )

    return compose_brief(
        district=district,
        gap_row=gap_row,
        amenities=amenities,
        parcel=parcel_dict,
        investors=investors,
        live_reconciliation=live_rec,
        mode="deterministic",
        headline=headline,
        intro_step=intro_step,
    )


def _pipeline_parcels(
    question: str,
    gaps: pd.DataFrame,
    asked_district: str | None,
    asked_sector: str | None,
) -> Brief:
    parcels_df = data_layer.find_best_vacant_parcels(
        district=asked_district,
        min_potential=70,
        land_use=asked_sector,
    )
    if parcels_df.empty and asked_sector:
        parcels_df = data_layer.find_best_vacant_parcels(
            district=asked_district, min_potential=70
        )

    if parcels_df.empty:
        return _pipeline_gap(question, gaps, asked_district, asked_sector)

    parcel_dict = _parcel_to_dict(parcels_df.iloc[0])
    district = str(parcel_dict.get("district", asked_district or gaps.iloc[0]["district"]))
    match = gaps[gaps["district"].str.lower() == district.lower()]
    gap_row = match.iloc[0] if not match.empty else gaps.iloc[0]
    sector = asked_sector or data_layer.land_use_to_sector(
        str(parcel_dict.get("land_use", "community"))
    )
    capital = parcel_dict.get("estimated_value_aed")
    investors = _match_investors_list(sector, capital)

    scope = f"in {asked_district}" if asked_district else "across Abu Dhabi"
    intro_step = (
        f"Scanned vacant parcels {scope} (potential ≥ 70) — "
        f"top site is {parcel_dict.get('parcel_id')} in {district} "
        f"({parcel_dict.get('land_use')}, score {parcel_dict.get('development_potential_score')}/100)."
    )
    headline = (
        f"Develop {parcel_dict.get('parcel_id')} in {district}: "
        f"{parcel_dict.get('land_use')} land, potential "
        f"{parcel_dict.get('development_potential_score')}/100."
    )

    return compose_brief(
        district=district,
        gap_row=gap_row,
        amenities=data_layer.get_amenities(district),
        parcel=parcel_dict,
        investors=investors,
        live_reconciliation=_price_reconciliation(district),
        mode="deterministic",
        headline=headline,
        intro_step=intro_step,
    )


def _pipeline_investors(
    question: str,
    gaps: pd.DataFrame,
    asked_district: str | None,
    asked_sector: str | None,
) -> Brief:
    sector = asked_sector or "commercial"
    investors_df = data_layer.match_investors(sector)
    investors = _match_investors_list(sector, None, investors_df)

    if asked_district:
        district = asked_district
    elif not investors_df.empty and "preferred_district" in investors_df.columns:
        district = str(investors_df.iloc[0]["preferred_district"])
    else:
        district = gaps.iloc[0]["district"]

    match = gaps[gaps["district"].str.lower() == district.lower()]
    gap_row = match.iloc[0] if not match.empty else gaps.iloc[0]
    parcels_df = data_layer.find_vacant_parcels(district, min_potential=70)
    parcel_dict, parcel_sector, capital = _pick_parcel(parcels_df, asked_sector)
    if not investors:
        investors = _match_investors_list(parcel_sector, capital)

    n = len(investors_df)
    intro_step = (
        f"Matched {n} {sector} investor mandates"
        + (f" for {district}" if district else "")
        + (
            f" — top fit {investors[0]['investor_id']} "
            f"({investors[0].get('strategic_fit_score', '?')}% strategic fit)."
            if investors
            else "."
        )
    )
    headline = (
        f"{n} investor mandates fit {sector} in {district} — "
        f"top match {investors[0]['investor_id']}."
        if investors
        else f"No {sector} investor mandates currently fit {district}."
    )

    return compose_brief(
        district=district,
        gap_row=gap_row,
        amenities=data_layer.get_amenities(district),
        parcel=parcel_dict,
        investors=investors,
        live_reconciliation=_price_reconciliation(district),
        mode="deterministic",
        headline=headline,
        intro_step=intro_step,
    )


def _pipeline_prices(
    question: str,
    gaps: pd.DataFrame,
    asked_district: str | None,
) -> Brief:
    district = _district_for_price_focus(gaps, asked_district)
    match = gaps[gaps["district"].str.lower() == district.lower()]
    gap_row = match.iloc[0] if not match.empty else gaps.iloc[0]
    live_rec = _price_reconciliation(district)

    if live_rec:
        source = live_rec.get("source", "live_listings")
        source_label = (
            "live listings"
            if source == "live_listings"
            else "sample_transactions.csv (2023–2026)"
        )
        intro_step = (
            f"Compared {source_label} sale price/sqm in {district} vs the synthetic "
            f"district baseline — median AED {live_rec['live_median']:,}/sqm vs "
            f"AED {live_rec['synthetic_baseline']:,}/sqm ({live_rec['pct_delta']:+.1f}%)."
        )
        headline = (
            f"{district} trades at {live_rec['pct_delta']:+.1f}% vs synthetic baseline "
            f"(AED {live_rec['live_median']:,}/sqm median from {source_label})."
        )
    else:
        intro_step = f"Could not build a price comparison for {district} — insufficient transaction data."
        headline = f"No reliable price comparison available for {district}."

    return compose_brief(
        district=district,
        gap_row=gap_row,
        amenities=data_layer.get_amenities(district),
        parcel=None,
        investors=[],
        live_reconciliation=live_rec,
        mode="deterministic",
        headline=headline,
        intro_step=intro_step,
    )


def _pick_parcel(
    parcels_df: pd.DataFrame,
    asked_sector: str | None,
) -> tuple[dict | None, str, float | None]:
    if parcels_df.empty:
        return None, "community", None
    chosen = parcels_df
    if asked_sector:
        use_c = "land_use" if "land_use" in parcels_df.columns else None
        if use_c:
            by_use = parcels_df[parcels_df[use_c].str.lower() == asked_sector.lower()]
            if not by_use.empty:
                chosen = by_use
    parcel_dict = _parcel_to_dict(chosen.iloc[0])
    sector = data_layer.land_use_to_sector(str(parcel_dict.get("land_use", "community")))
    capital = parcel_dict.get("estimated_value_aed")
    return parcel_dict, sector, capital


def _match_investors_list(
    sector: str,
    capital: float | None,
    investors_df: pd.DataFrame | None = None,
) -> list[dict]:
    if investors_df is None:
        investors_df = data_layer.match_investors(sector, capital=capital)
    if investors_df.empty:
        return []
    return json.loads(investors_df.head(20).to_json(orient="records"))


def _deterministic_pipeline(question: str = "") -> Brief:
    gaps = data_layer.get_district_gaps()
    asked_district = _question_district(question)
    asked_sector = _question_sector(question)
    intent = _question_intent(question)

    if intent == "parcels":
        return _pipeline_parcels(question, gaps, asked_district, asked_sector)
    if intent == "investors":
        return _pipeline_investors(question, gaps, asked_district, asked_sector)
    if intent == "prices":
        return _pipeline_prices(question, gaps, asked_district)
    return _pipeline_gap(question, gaps, asked_district, asked_sector)


def _extract_context_from_tool_results(tool_results: list[dict]) -> dict[str, Any]:
    """Rebuild brief inputs from accumulated tool call results."""
    context: dict[str, Any] = {
        "district": None,
        "gap_row": {},
        "amenities": pd.DataFrame(),
        "parcel": None,
        "investors": [],
        "live_reconciliation": None,
    }

    for tr in tool_results:
        name = tr.get("name")
        data = tr.get("result", {})
        if name == "query_community_demand":
            districts = data.get("districts", [])
            if districts and not context["district"]:
                context["gap_row"] = districts[0]
                context["district"] = districts[0].get("district")
        elif name == "get_district_profile" and data.get("district"):
            if not context["district"]:
                context["district"] = data["district"]
        elif name == "query_amenity_supply":
            context["amenities"] = pd.DataFrame(data.get("amenities", []))
            if data.get("district"):
                context["district"] = data["district"]
        elif name == "find_vacant_parcels":
            parcels = data.get("parcels", [])
            if parcels:
                context["parcel"] = parcels[0]
            if data.get("district"):
                context["district"] = data["district"]
        elif name == "match_investors":
            context["investors"] = data.get("investors", [])
        elif name == "cross_check_live_prices":
            context["live_reconciliation"] = data.get("reconciliation")

    if context["district"] and not context["gap_row"]:
        gaps = data_layer.get_district_gaps()
        match = gaps[gaps["district"].str.lower() == context["district"].lower()]
        if not match.empty:
            context["gap_row"] = match.iloc[0].to_dict()

    if context["district"] and context["amenities"].empty:
        context["amenities"] = data_layer.get_amenities(context["district"])

    return context


def _llm_pipeline(question: str) -> Brief:
    import os

    provider = os.environ.get("LLM_PROVIDER", "none").lower()
    system = (
        "You are Qarar, a Decision Intelligence copilot for Abu Dhabi PropTech. "
        "Use the provided tools to investigate the user's question step by step. "
        "Choose tools dynamically based on prior results — do not assume a fixed order. "
        "After gathering evidence, respond with a concise summary. "
        "Focus on underserved districts, vacant parcels, and investor matches."
    )
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    schemas = tool_schemas_for_llm()
    tool_results: list[dict] = []
    tool_call_count = 0

    for _ in range(MAX_TOOL_ITERATIONS):
        response = llm.complete_with_tools(messages, schemas)
        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            break

        if provider == "anthropic":
            assistant_content: list[dict] = []
            if response.get("text"):
                assistant_content.append({"type": "text", "text": response["text"]})
            tool_result_blocks: list[dict] = []
            for tc in tool_calls:
                tool_call_count += 1
                result_str = execute_tool(tc["name"], tc.get("arguments", {}))
                result_data = json.loads(result_str)
                tool_results.append({"name": tc["name"], "result": result_data})
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc.get("arguments", {}),
                    }
                )
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": result_str,
                    }
                )
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_result_blocks})
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": response.get("text"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("arguments", {})),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                tool_call_count += 1
                result_str = execute_tool(tc["name"], tc.get("arguments", {}))
                result_data = json.loads(result_str)
                tool_results.append({"name": tc["name"], "result": result_data})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_str,
                    }
                )

    ctx = _extract_context_from_tool_results(tool_results)
    if not ctx["district"]:
        return _deterministic_pipeline(question)

    gap_row = ctx["gap_row"] or {}
    return compose_brief(
        district=ctx["district"],
        gap_row=gap_row,
        amenities=ctx["amenities"],
        parcel=ctx["parcel"],
        investors=ctx["investors"],
        live_reconciliation=ctx["live_reconciliation"],
        mode="ai_agent",
        tool_call_count=tool_call_count,
    )


def answer(question: str) -> Brief:
    """Answer a decision question; always returns a Brief."""
    try:
        if llm.is_llm_available():
            return _llm_pipeline(question)
    except Exception:
        pass
    return _deterministic_pipeline(question)
