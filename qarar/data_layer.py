"""Deterministic pandas data layer — load, join, and gap metric."""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ESSENTIAL_CATEGORIES = {"healthcare", "education", "community"}


def _col(df: pd.DataFrame, *candidates: str) -> str | None:
    lookup = {c.lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.lower()
        if key in lookup:
            return lookup[key]
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    return df.rename(columns=renamed)


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")
    return _normalize_columns(pd.read_csv(path))


@functools.cache
def load_districts() -> pd.DataFrame:
    return _read_csv("districts.csv")


@functools.cache
def load_communities() -> pd.DataFrame:
    return _read_csv("sample_communities.csv")


@functools.cache
def load_amenities() -> pd.DataFrame:
    return _read_csv("osm_amenities.csv")


@functools.cache
def load_parcels() -> pd.DataFrame:
    return _read_csv("sample_parcels.csv")


@functools.cache
def load_investors() -> pd.DataFrame:
    return _read_csv("sample_investors.csv")


@functools.cache
def load_transactions() -> pd.DataFrame:
    return _read_csv("sample_transactions.csv")


@functools.cache
def load_listings() -> pd.DataFrame:
    return _read_csv("sample_listings.csv")


def _parse_capital_aed(value: str) -> tuple[float, float]:
    """Parse strings like '50M-200M' or '500M-2B' into AED bounds."""

    def _token(tok: str) -> float:
        tok = tok.strip().upper()
        m = re.match(r"^([\d.]+)\s*([KMB])?$", tok)
        if not m:
            return 0.0
        num = float(m.group(1))
        suffix = m.group(2) or ""
        mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
        return num * mult

    parts = value.split("-")
    if len(parts) != 2:
        return 0.0, float("inf")
    return _token(parts[0]), _token(parts[1])


def _capital_overlaps(range_str: str, capital: float) -> bool:
    lo, hi = _parse_capital_aed(range_str)
    return lo <= capital <= hi


def get_district_gaps() -> pd.DataFrame:
    """Rank districts worst-first by demand vs amenity supply gap (cached source)."""
    return _compute_gaps(load_communities(), load_amenities(), load_districts())


def _compute_gaps(
    communities: pd.DataFrame,
    amenities: pd.DataFrame,
    districts: pd.DataFrame,
) -> pd.DataFrame:
    """Pure gap computation over the given frames (no caching, no mutation)."""
    dist_c = _col(communities, "district")
    pop_c = _col(communities, "population_estimate")
    sdi_c = _col(communities, "service_demand_index")
    if not all([dist_c, pop_c, sdi_c]):
        raise ValueError("sample_communities.csv missing required columns")

    def _weighted_demand(group: pd.DataFrame) -> float:
        weights = group[pop_c].astype(float)
        if weights.sum() == 0:
            return float(group[sdi_c].mean())
        return float(np.average(group[sdi_c], weights=weights))

    demand = (
        communities.groupby(dist_c, as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "population_total": g[pop_c].sum(),
                    "service_demand": _weighted_demand(g),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    demand = demand.rename(columns={dist_c: "district"})

    adist = _col(amenities, "district")
    acat = _col(amenities, "category")
    if not adist:
        raise ValueError("osm_amenities.csv missing district column")

    supply = amenities.groupby(adist, as_index=False).size().rename(
        columns={"size": "amenity_count", adist: "district"}
    )

    if acat:
        essential = amenities[amenities[acat].isin(ESSENTIAL_CATEGORIES)]
        essential_supply = essential.groupby(adist, as_index=False).size().rename(
            columns={"size": "essential_amenity_count", adist: "district"}
        )
    else:
        essential_supply = pd.DataFrame(columns=["district", "essential_amenity_count"])

    gap = demand.merge(supply, on="district", how="left")
    gap = gap.merge(essential_supply, on="district", how="left")
    gap["amenity_count"] = gap["amenity_count"].fillna(0).astype(int)
    gap["essential_amenity_count"] = gap["essential_amenity_count"].fillna(0).astype(int)
    gap["amenity_per_capita"] = gap["amenity_count"] / gap["population_total"].clip(lower=1)

    # Continuous, correctly-signed gap score: high demand + low supply = high gap.
    def _norm(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        if hi - lo == 0:
            return pd.Series(0.5, index=s.index)
        return (s - lo) / (hi - lo)

    demand_n = _norm(gap["service_demand"])
    supply_n = _norm(gap["amenity_per_capita"])
    gap["gap_score"] = ((demand_n + (1 - supply_n)) / 2 * 100).round(1)
    # Ranks kept for reference: 1 = highest demand / lowest supply (worst).
    gap["demand_rank"] = gap["service_demand"].rank(ascending=False, method="min")
    gap["supply_rank"] = gap["amenity_per_capita"].rank(ascending=True, method="min")
    gap["unmet_demand"] = (demand_n - supply_n).round(3)

    ddist = _col(districts, "district")
    if ddist:
        gap = gap.merge(
            districts[[ddist, _col(districts, "latitude"), _col(districts, "longitude")]],
            left_on="district",
            right_on=ddist,
            how="left",
        )
        if ddist != "district":
            gap = gap.drop(columns=[ddist])

    return gap.sort_values(
        ["gap_score", "unmet_demand", "service_demand"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


# Amenities added when a parcel is developed, keyed by land use.
_PARCEL_DEVELOP_CATEGORY = {
    "residential": "community",
    "community": "community",
    "mixed_use": "community",
    "commercial": "retail",
    "hospitality": "retail",
    "industrial": "services",
}
_PARCEL_DEVELOP_AMENITIES = 8


def simulate(overrides: dict[str, Any]) -> pd.DataFrame:
    """Recompute district gaps after applying overrides to COPIES of the data.

    Supported overrides:
      - district: target district name (required for population/amenity overrides)
      - population_delta: int added to the district's population
      - add_amenities: {"category": str, "count": int}
      - develop_parcel: parcel_id (adds amenities in the parcel's district)
    Never mutates cached source data.
    """
    communities = load_communities().copy()
    amenities = load_amenities().copy()
    districts = load_districts()

    cdist = _col(communities, "district")
    cpop = _col(communities, "population_estimate")
    adist = _col(amenities, "district")
    acat = _col(amenities, "category")

    district = overrides.get("district")

    # --- population delta: scale the district's community rows proportionally ---
    delta = int(overrides.get("population_delta") or 0)
    if district and delta and cdist and cpop:
        mask = communities[cdist].str.lower() == district.lower()
        current = float(communities.loc[mask, cpop].sum())
        if current > 0:
            new_total = max(1.0, current + delta)
            factor = new_total / current
            communities.loc[mask, cpop] = (
                communities.loc[mask, cpop].astype(float) * factor
            ).round().astype(int)

    # --- explicit amenity additions ---
    def _add_amenities(target_district: str, category: str, count: int) -> None:
        nonlocal amenities
        if count <= 0 or not adist:
            return
        rows = []
        for i in range(count):
            row = {c: None for c in amenities.columns}
            row[adist] = target_district
            if acat:
                row[acat] = category
            rows.append(row)
        amenities = pd.concat([amenities, pd.DataFrame(rows)], ignore_index=True)

    add = overrides.get("add_amenities")
    if district and isinstance(add, dict):
        _add_amenities(district, add.get("category", "community"),
                       int(add.get("count") or 0))

    # --- develop a parcel: adds service capacity (amenities) in its district ---
    parcel_id = overrides.get("develop_parcel")
    if parcel_id:
        parcels = load_parcels()
        pid_c = _col(parcels, "parcel_id")
        pdist_c = _col(parcels, "district")
        puse_c = _col(parcels, "land_use")
        prow = parcels[parcels[pid_c].astype(str) == str(parcel_id)]
        if not prow.empty:
            pdist = prow.iloc[0][pdist_c]
            puse = str(prow.iloc[0][puse_c]).lower() if puse_c else "community"
            cat = _PARCEL_DEVELOP_CATEGORY.get(puse, "community")
            _add_amenities(pdist, cat, _PARCEL_DEVELOP_AMENITIES)

    return _compute_gaps(communities, amenities, districts)


def scenario_compare(overrides: dict[str, Any]) -> dict[str, Any]:
    """Return baseline vs scenario worst-district comparison (pure pandas)."""
    baseline = get_district_gaps()
    scenario = simulate(overrides)

    def _row(df: pd.DataFrame, district: str | None = None) -> dict:
        if district:
            m = df[df["district"].str.lower() == district.lower()]
            if not m.empty:
                r = m.iloc[0]
                return {"district": r["district"], "gap_score": float(r["gap_score"])}
        r = df.iloc[0]
        return {"district": r["district"], "gap_score": float(r["gap_score"])}

    focus = overrides.get("district")
    return {
        "baseline_worst": _row(baseline),
        "scenario_worst": _row(scenario),
        "focus_district": focus,
        "focus_before": _row(baseline, focus) if focus else None,
        "focus_after": _row(scenario, focus) if focus else None,
        "scenario_top": json.loads(
            scenario.head(5)[["district", "gap_score"]].to_json(orient="records")
        ),
    }


def get_city_overview() -> pd.DataFrame:
    """City-wide demand-vs-supply table built only from the gap ranking.

    Columns: district, service_demand, amenity_count, amenity_per_capita,
    gap_score, vacant_parcels, base_sale_aed_sqm, population_total. Worst-first.
    """
    gaps = get_district_gaps()

    parcels = load_parcels()
    pdist = _col(parcels, "district")
    pstatus = _col(parcels, "current_status")
    vacant = (
        parcels[parcels[pstatus].str.lower() == "vacant"]
        .groupby(pdist)
        .size()
        .rename("vacant_parcels")
    )

    districts = load_districts()
    ddist = _col(districts, "district")
    price_c = _col(districts, "base_sale_aed_sqm")

    out = gaps.merge(vacant, left_on="district", right_index=True, how="left")
    out["vacant_parcels"] = out["vacant_parcels"].fillna(0).astype(int)

    if price_c:
        price = districts[[ddist, price_c]].rename(
            columns={ddist: "district", price_c: "base_sale_aed_sqm"}
        )
        out = out.merge(price, on="district", how="left")
    else:
        out["base_sale_aed_sqm"] = None

    cols = [
        "district",
        "service_demand",
        "amenity_count",
        "amenity_per_capita",
        "gap_score",
        "vacant_parcels",
        "base_sale_aed_sqm",
        "population_total",
    ]
    cols = [c for c in cols if c in out.columns]
    return out[cols].reset_index(drop=True)


def get_district_profile(district: str) -> dict[str, Any]:
    """Return price, yield, infra, population, scores, and centroid for a district."""
    districts = load_districts()
    communities = load_communities()

    ddist = _col(districts, "district")
    row = districts[districts[ddist].str.lower() == district.lower()]
    if row.empty:
        raise ValueError(f"Unknown district: {district}")
    row = row.iloc[0]

    dist_c = _col(communities, "district")
    pop_c = _col(communities, "population_estimate")
    sdi_c = _col(communities, "service_demand_index")
    mob_c = _col(communities, "mobility_score")
    res_c = _col(communities, "resident_experience_score")

    comm = communities[communities[dist_c].str.lower() == district.lower()]
    population = int(comm[pop_c].sum()) if not comm.empty else 0

    def _wmean(col: str) -> float | None:
        if comm.empty or col is None:
            return None
        weights = comm[pop_c].astype(float)
        if weights.sum() == 0:
            return float(comm[col].mean())
        return float(np.average(comm[col], weights=weights))

    price_c = _col(districts, "base_sale_aed_sqm")
    yield_c = _col(districts, "gross_yield_pct")
    infra_c = _col(districts, "infrastructure_score")
    lat_c = _col(districts, "latitude")
    lon_c = _col(districts, "longitude")

    return {
        "district": row[ddist],
        "base_sale_aed_sqm": int(row[price_c]) if price_c else None,
        "gross_yield_pct": float(row[yield_c]) if yield_c else None,
        "infrastructure_score": int(row[infra_c]) if infra_c else None,
        "population": population,
        "service_demand_index": _wmean(sdi_c),
        "mobility_score": _wmean(mob_c),
        "resident_experience_score": _wmean(res_c),
        "latitude": float(row[lat_c]) if lat_c else None,
        "longitude": float(row[lon_c]) if lon_c else None,
    }


def get_amenities(district: str, category: str | None = None) -> pd.DataFrame:
    """Return OSM amenities for a district, optionally filtered by category."""
    amenities = load_amenities()
    adist = _col(amenities, "district")
    acat = _col(amenities, "category")

    mask = amenities[adist].str.lower() == district.lower()
    if category and acat:
        mask &= amenities[acat].str.lower() == category.lower()

    cols = [c for c in [adist, acat, _col(amenities, "subtype"), _col(amenities, "name"),
                        _col(amenities, "latitude"), _col(amenities, "longitude")] if c]
    return amenities.loc[mask, cols].reset_index(drop=True)


def find_vacant_parcels(district: str, min_potential: int = 70) -> pd.DataFrame:
    """Vacant parcels in a district above min development potential, best first."""
    return find_best_vacant_parcels(
        district=district, min_potential=min_potential
    )


def find_best_vacant_parcels(
    district: str | None = None,
    min_potential: int = 70,
    land_use: str | None = None,
) -> pd.DataFrame:
    """Best vacant parcels emirate-wide or in one district, highest potential first."""
    parcels = load_parcels()
    dist_c = _col(parcels, "district")
    status_c = _col(parcels, "current_status")
    pot_c = _col(parcels, "development_potential_score")
    use_c = _col(parcels, "land_use")

    mask = (parcels[status_c].str.lower() == "vacant") & (
        parcels[pot_c] >= min_potential
    )
    if district:
        mask &= parcels[dist_c].str.lower() == district.lower()
    if land_use and use_c:
        mask &= parcels[use_c].str.lower() == land_use.lower()

    return parcels.loc[mask].sort_values(pot_c, ascending=False).reset_index(drop=True)


def get_transaction_price_comparison(district: str) -> dict | None:
    """Compare recent transaction median price/sqm to the synthetic district baseline."""
    txns = load_transactions()
    dist_c = _col(txns, "district")
    price_c = _col(txns, "price_per_sqm")
    if not all([dist_c, price_c]):
        return None

    dtx = txns[txns[dist_c].str.lower() == district.lower()]
    if dtx.empty:
        return None

    txn_median = float(dtx[price_c].median())
    baseline = get_district_profile(district).get("base_sale_aed_sqm")
    if not baseline:
        return None

    pct_delta = round((txn_median - baseline) / baseline * 100, 1)
    return {
        "live_median": round(txn_median),
        "synthetic_baseline": int(baseline),
        "pct_delta": pct_delta,
        "n_listings": len(dtx),
        "n_mislabeled_rent_vs_sale": 0,
        "source": "sample_transactions.csv",
    }


def match_investors(sector: str, capital: float | None = None) -> pd.DataFrame:
    """Investors matching sector; optional capital-in-range filter."""
    investors = load_investors()
    sec_c = _col(investors, "preferred_sector")
    cap_c = _col(investors, "capital_range_aed")
    fit_c = _col(investors, "strategic_fit_score")

    mask = investors[sec_c].str.lower() == sector.lower()
    result = investors.loc[mask].copy()

    if capital is not None and cap_c:
        result = result[result[cap_c].apply(lambda r: _capital_overlaps(r, capital))]

    if fit_c:
        result = result.sort_values(fit_c, ascending=False)
    return result.reset_index(drop=True)


def land_use_to_sector(land_use: str) -> str:
    """Map parcel land_use to investor preferred_sector."""
    mapping = {
        "residential": "residential",
        "commercial": "commercial",
        "mixed_use": "mixed_use",
        "industrial": "industrial",
        "hospitality": "hospitality",
        "community": "community",
    }
    return mapping.get(land_use.lower(), land_use.lower())


def _stable_hash(text: str) -> int:
    """Process-stable hash (Python's built-in hash() is salted per run)."""
    import hashlib

    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)


def parcel_pin_coords(district: str, parcel_id: str) -> tuple[float, float]:
    """District centroid plus a small deterministic offset for a map pin."""
    profile = get_district_profile(district)
    lat = profile["latitude"] or 24.45
    lon = profile["longitude"] or 54.37
    h = _stable_hash(parcel_id) % 10000
    return lat + (h % 100 - 50) * 0.00025, lon + (h // 100 - 50) * 0.00025


def get_district_parcels(district: str) -> list[dict]:
    """All parcels in a district with deterministic map coordinates."""
    parcels = load_parcels()
    dist_c = _col(parcels, "district")
    pid_c = _col(parcels, "parcel_id")
    if not dist_c or not pid_c:
        return []

    sub = parcels[parcels[dist_c].str.lower() == district.lower()]
    if sub.empty:
        return []

    cols = {
        "parcel_id": pid_c,
        "land_use": _col(parcels, "land_use"),
        "current_status": _col(parcels, "current_status"),
        "parcel_size_sqm": _col(parcels, "parcel_size_sqm"),
        "development_potential_score": _col(parcels, "development_potential_score"),
        "estimated_value_aed": _col(parcels, "estimated_value_aed"),
        "recommended_use": _col(parcels, "recommended_use"),
    }

    out: list[dict] = []
    for _, row in sub.iterrows():
        pid = str(row[pid_c])
        lat, lon = parcel_pin_coords(district, pid)
        rec: dict[str, Any] = {"district": district, "latitude": lat, "longitude": lon}
        for key, src in cols.items():
            if not src:
                continue
            val = row[src]
            if pd.isna(val):
                rec[key] = None
            elif key in (
                "parcel_size_sqm",
                "development_potential_score",
                "estimated_value_aed",
            ):
                rec[key] = int(val)
            else:
                rec[key] = str(val)
        out.append(rec)
    return out
