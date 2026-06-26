"""Callable tools with JSON schemas for the agent."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

import data_layer
import live_data


def _df_to_records(df: pd.DataFrame, limit: int = 50) -> list[dict]:
    if df.empty:
        return []
    return json.loads(df.head(limit).to_json(orient="records"))


def _tool_query_community_demand(district: str | None = None) -> dict:
    gaps = data_layer.get_district_gaps()
    if district:
        gaps = gaps[gaps["district"].str.lower() == district.lower()]
    return {"districts": _df_to_records(gaps, limit=20)}


def _tool_query_amenity_supply(district: str, category: str | None = None) -> dict:
    df = data_layer.get_amenities(district, category=category)
    return {
        "district": district,
        "category": category,
        "count": len(df),
        "amenities": _df_to_records(df, limit=100),
    }


def _tool_find_vacant_parcels(district: str, min_potential: int = 70) -> dict:
    df = data_layer.find_vacant_parcels(district, min_potential=min_potential)
    return {"district": district, "parcels": _df_to_records(df, limit=20)}


def _tool_match_investors(sector: str, capital: float | None = None) -> dict:
    df = data_layer.match_investors(sector, capital=capital)
    return {"sector": sector, "investors": _df_to_records(df, limit=20)}


def _tool_get_district_profile(district: str) -> dict:
    return data_layer.get_district_profile(district)


def _tool_cross_check_live_prices(district: str) -> dict:
    result = live_data.cross_check_live_prices(district)
    return {"district": district, "reconciliation": result}


def _tool_run_scenario(
    district: str | None = None,
    population_delta: int = 0,
    add_amenity_category: str | None = None,
    add_amenity_count: int = 0,
    develop_parcel: str | None = None,
) -> dict:
    overrides: dict = {}
    if district:
        overrides["district"] = district
    if population_delta:
        overrides["population_delta"] = int(population_delta)
    if add_amenity_count and add_amenity_category:
        overrides["add_amenities"] = {
            "category": add_amenity_category,
            "count": int(add_amenity_count),
        }
    if develop_parcel:
        overrides["develop_parcel"] = develop_parcel
    return data_layer.scenario_compare(overrides)


TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_community_demand",
        "description": (
            "Rank Abu Dhabi districts by unmet community demand vs amenity supply. "
            "Returns gap_score (higher = more underserved), population, service demand."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {
                    "type": "string",
                    "description": "Optional district name to filter; omit for full ranking.",
                },
            },
            "required": [],
        },
        "callable": _tool_query_community_demand,
    },
    {
        "name": "query_amenity_supply",
        "description": (
            "Get real OSM amenity POIs for a district with lat/lon. "
            "Optionally filter by category: healthcare, education, community, retail, services, mobility."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "District name."},
                "category": {
                    "type": "string",
                    "description": "Optional amenity category filter.",
                },
            },
            "required": ["district"],
        },
        "callable": _tool_query_amenity_supply,
    },
    {
        "name": "find_vacant_parcels",
        "description": (
            "Find vacant land parcels in a district with development potential above threshold."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "District name."},
                "min_potential": {
                    "type": "integer",
                    "description": "Minimum development_potential_score (0-100). Default 70.",
                    "default": 70,
                },
            },
            "required": ["district"],
        },
        "callable": _tool_find_vacant_parcels,
    },
    {
        "name": "match_investors",
        "description": "Match investor mandates by preferred sector and optional capital (AED).",
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Target sector: residential, commercial, mixed_use, hospitality, community, industrial, logistics.",
                },
                "capital": {
                    "type": "number",
                    "description": "Optional deployable capital in AED to filter capital_range_aed.",
                },
            },
            "required": ["sector"],
        },
        "callable": _tool_match_investors,
    },
    {
        "name": "get_district_profile",
        "description": (
            "District profile: base sale price/sqm, yield, infrastructure, population, "
            "service demand, mobility, resident experience, centroid lat/lon."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "District name."},
            },
            "required": ["district"],
        },
        "callable": _tool_get_district_profile,
    },
    {
        "name": "cross_check_live_prices",
        "description": (
            "Optional live listings reconciliation: median sale price/sqm vs synthetic baseline. "
            "Returns None in reconciliation if no live cache/API."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "District name."},
            },
            "required": ["district"],
        },
        "callable": _tool_cross_check_live_prices,
    },
    {
        "name": "run_scenario",
        "description": (
            "Simulate a 'what if' planning scenario and compare district gap rankings "
            "before vs after. Apply a population change, add amenities of a category, "
            "and/or develop a vacant parcel. Returns baseline_worst, scenario_worst, "
            "and the focus district's gap score before/after."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "Target district for the scenario."},
                "population_delta": {
                    "type": "integer",
                    "description": "Change in population for the district (can be negative).",
                },
                "add_amenity_category": {
                    "type": "string",
                    "description": "Category of amenities to add (e.g. healthcare, education, community).",
                },
                "add_amenity_count": {
                    "type": "integer",
                    "description": "How many amenities of that category to add.",
                },
                "develop_parcel": {
                    "type": "string",
                    "description": "Parcel id to develop (adds service capacity in its district).",
                },
            },
            "required": [],
        },
        "callable": _tool_run_scenario,
    },
]

TOOL_BY_NAME = {t["name"]: t for t in TOOLS}


def tool_schemas_for_llm() -> list[dict]:
    return [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in TOOLS
    ]


def execute_tool(name: str, arguments: dict | None) -> str:
    tool = TOOL_BY_NAME.get(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    args = arguments or {}
    try:
        result = tool["callable"](**args)
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
