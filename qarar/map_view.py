"""Reusable choropleth builder for Abu Dhabi's districts.

Geometry fallback chain (never blocks, never crashes):
  a. qarar/data/ad_districts.geojson  -> filled polygons joined by name
  b. Voronoi tessellation of district centroids, clipped to a bbox
  c. graduated circle markers at each centroid

Produces a layer- and year-aware payload consumed by the frontend
ChoroplethMap component (MapLibre). Colors are applied client-side
(theme-aware white/gold) from the per-feature ``value_norm``.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import data_layer as dl

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GEOJSON_PATH = Path(__file__).resolve().parent / "data" / "ad_districts.geojson"

LAYERS: list[dict[str, Any]] = [
    {"id": "unmet_demand", "label": "Unmet demand", "year_aware": False},
    {"id": "price", "label": "Avg price /sqm", "year_aware": False},
    {"id": "transactions", "label": "Transactions", "year_aware": True},
    {"id": "rent", "label": "Rent /sqm", "year_aware": True},
    {"id": "supply", "label": "Supply", "year_aware": False},
]
AVAILABLE_YEARS = [2023, 2024, 2025, 2026]
DEFAULT_LAYER = "unmet_demand"


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #
def _centroids() -> dict[str, tuple[float, float]]:
    df = dl.load_districts()
    dcol = dl._col(df, "district")
    lat = dl._col(df, "latitude")
    lon = dl._col(df, "longitude")
    return {
        str(r[dcol]): (float(r[lon]), float(r[lat]))
        for _, r in df.iterrows()
        if pd.notna(r[lat]) and pd.notna(r[lon])
    }


def _voronoi_finite_polygons_2d(vor, radius: float):
    """Reconstruct infinite Voronoi regions into finite polygons (standard recipe)."""
    new_regions = []
    new_vertices = vor.vertices.tolist()
    center = vor.points.mean(axis=0)

    all_ridges: dict[int, list] = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue

        ridges = all_ridges.get(p1, [])
        new_region = [v for v in vertices if v >= 0]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue
            t = vor.points[p2] - vor.points[p1]
            t = t / np.linalg.norm(t)
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius
            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)].tolist()
        new_regions.append(new_region)

    return new_regions, np.asarray(new_vertices)


def _polygons_from_geojson() -> dict[str, list[list[float]]] | None:
    if not GEOJSON_PATH.exists():
        return None
    try:
        gj = json.loads(GEOJSON_PATH.read_text())
    except Exception:
        return None

    names = {n.lower(): n for n in _centroids()}
    out: dict[str, list[list[float]]] = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        raw = str(
            props.get("district")
            or props.get("name")
            or props.get("NAME")
            or ""
        ).lower()
        match = names.get(raw)
        if not match:
            continue
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates")
        if geom.get("type") == "Polygon" and coords:
            out[match] = coords[0]
        elif geom.get("type") == "MultiPolygon" and coords:
            biggest = max(coords, key=lambda poly: len(poly[0]))
            out[match] = biggest[0]
    return out or None


@functools.cache
def _voronoi_polygons() -> dict[str, list[list[float]]] | None:
    try:
        from scipy.spatial import Voronoi
        from shapely.geometry import Polygon, box

        cents = _centroids()
        names = list(cents.keys())
        pts = np.array([cents[n] for n in names])
        if len(pts) < 4:
            return None

        margin = 0.05
        bbox = box(
            pts[:, 0].min() - margin,
            pts[:, 1].min() - margin,
            pts[:, 0].max() + margin,
            pts[:, 1].max() + margin,
        )

        vor = Voronoi(pts)
        radius = float(np.ptp(pts, axis=0).max()) * 3
        regions, vertices = _voronoi_finite_polygons_2d(vor, radius)

        out: dict[str, list[list[float]]] = {}
        for i, region in enumerate(regions):
            poly = Polygon(vertices[region])
            if not poly.is_valid:
                poly = poly.buffer(0)
            clipped = poly.intersection(bbox)
            if clipped.is_empty:
                continue
            if clipped.geom_type == "MultiPolygon":
                clipped = max(clipped.geoms, key=lambda g: g.area)
            ring = [[round(x, 6), round(y, 6)] for x, y in clipped.exterior.coords]
            out[names[i]] = ring
        return out or None
    except Exception:
        return None


def district_polygons() -> tuple[str, dict[str, list[list[float]]]]:
    """Return (mode, polygons). mode is 'polygon' or 'circle'."""
    geo = _polygons_from_geojson()
    if geo:
        return "polygon", geo
    vor = _voronoi_polygons()
    if vor:
        return "polygon", vor
    return "circle", {}


# --------------------------------------------------------------------------- #
# Layer values
# --------------------------------------------------------------------------- #
def _layer_values(layer: str, year: int | None) -> tuple[dict[str, float], dict[str, str], str]:
    """Return (district->value, district->label, unit) for a layer/year."""
    if layer == "unmet_demand":
        gaps = dl.get_district_gaps()
        vals = {str(r["district"]): float(r["gap_score"]) for _, r in gaps.iterrows()}
        labels = {d: f"{v:.0f}" for d, v in vals.items()}
        return vals, labels, "gap"

    if layer == "price":
        df = dl.load_districts()
        dcol = dl._col(df, "district")
        pcol = dl._col(df, "base_sale_aed_sqm")
        vals = {str(r[dcol]): float(r[pcol]) for _, r in df.iterrows() if pd.notna(r[pcol])}
        labels = {d: f"{v / 1000:.1f}k" for d, v in vals.items()}
        return vals, labels, "AED/sqm"

    if layer == "transactions":
        df = dl.load_transactions().copy()
        dcol = dl._col(df, "district")
        dt = dl._col(df, "date")
        df["_y"] = pd.to_datetime(df[dt]).dt.year
        if year:
            df = df[df["_y"] == year]
        counts = df.groupby(dcol).size()
        vals = {str(k): float(v) for k, v in counts.items()}
        labels = {d: f"{int(v)}" for d, v in vals.items()}
        return vals, labels, "deals"

    if layer == "rent":
        df = dl.load_listings().copy()
        dcol = dl._col(df, "district")
        ltype = dl._col(df, "listing_type")
        pcol = dl._col(df, "price_per_sqm_aed")
        ld = dl._col(df, "listed_date")
        df = df[df[ltype].str.lower() == "rent"]
        if year and ld:
            df = df[pd.to_datetime(df[ld]).dt.year == year]
        med = df.groupby(dcol)[pcol].median()
        vals = {str(k): float(v) for k, v in med.items() if pd.notna(v)}
        labels = {d: f"{v:.0f}" for d, v in vals.items()}
        return vals, labels, "AED/sqm/yr"

    if layer == "supply":
        parcels = dl.load_parcels()
        amen = dl.load_amenities()
        pc = parcels.groupby(dl._col(parcels, "district")).size()
        ac = amen.groupby(dl._col(amen, "district")).size()
        districts = {str(k) for k in pc.index} | {str(k) for k in ac.index}
        vals = {
            d: float(int(pc.get(d, 0)) + int(ac.get(d, 0))) for d in districts
        }
        labels = {d: f"{int(v)}" for d, v in vals.items()}
        return vals, labels, "parcels + amenities"

    return {}, {}, ""


def _norm(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    if hi - lo == 0:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


# --------------------------------------------------------------------------- #
# Public builder
# --------------------------------------------------------------------------- #
def build_choropleth(
    layer: str = DEFAULT_LAYER,
    year: int | None = None,
    highlight_district: str | None = None,
) -> dict[str, Any]:
    if layer not in {l["id"] for l in LAYERS}:
        layer = DEFAULT_LAYER

    layer_meta = next(l for l in LAYERS if l["id"] == layer)
    if not layer_meta["year_aware"]:
        year = None

    mode, polygons = district_polygons()
    cents = _centroids()
    values, labels, unit = _layer_values(layer, year)
    norms = _norm(values)

    hl = (highlight_district or "").lower()

    features = []
    for district, (lon, lat) in cents.items():
        has_value = district in values
        feat = {
            "type": "Feature",
            "properties": {
                "district": district,
                "value": values.get(district),
                "value_norm": norms.get(district, 0.0),
                "has_value": 1 if has_value else 0,
                "label": labels.get(district, "—"),
                "is_highlight": 1 if district.lower() == hl else 0,
                "centroid": [lon, lat],
            },
            "geometry": (
                {"type": "Polygon", "coordinates": [polygons[district]]}
                if mode == "polygon" and district in polygons
                else {"type": "Point", "coordinates": [lon, lat]}
            ),
        }
        features.append(feat)

    # center / zoom
    if highlight_district and highlight_district in cents:
        lon, lat = cents[highlight_district]
        center = {"longitude": lon, "latitude": lat, "zoom": 12.2}
    else:
        arr = np.array(list(cents.values()))
        center = {
            "longitude": float(arr[:, 0].mean()),
            "latitude": float(arr[:, 1].mean()),
            "zoom": 9.6,
        }

    legend = {
        "title": layer_meta["label"],
        "unit": unit,
        "min": min(values.values()) if values else None,
        "max": max(values.values()) if values else None,
        "year_aware": layer_meta["year_aware"],
    }

    return {
        "geometry_mode": mode,
        "layer": layer,
        "year": year,
        "feature_collection": {"type": "FeatureCollection", "features": features},
        "legend": legend,
        "center": center,
        "highlight_district": highlight_district,
        "layers": LAYERS,
        "available_years": AVAILABLE_YEARS,
    }
