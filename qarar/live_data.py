"""Cached wrapper over the eVoost live listings connector."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd

from data_layer import get_district_profile, load_transactions

REPO_ROOT = Path(__file__).resolve().parent.parent
CONNECTOR_PATH = REPO_ROOT / "examples" / "live-data-connector" / "main.py"
CACHE_DIR = Path(__file__).resolve().parent / "cache"
SNAPSHOT_PATH = CACHE_DIR / "live_listings.parquet"


def _load_connector():
    spec = importlib.util.spec_from_file_location("live_connector", CONNECTOR_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load connector from {CONNECTOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["live_connector"] = module
    spec.loader.exec_module(module)
    return module


def _fetch_and_snapshot() -> pd.DataFrame | None:
    if not os.environ.get("UAE_DATA_API_KEY"):
        return None
    try:
        connector = _load_connector()
        raw = connector.fetch_listings(emirate="Abu Dhabi", max_pages=5)
        df = connector.clean(raw)
        if df.empty:
            return None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(SNAPSHOT_PATH, index=False)
        return df
    except Exception:
        return None


def get_live_listings() -> pd.DataFrame | None:
    """Read cached snapshot; fetch once if key present and no cache."""
    if SNAPSHOT_PATH.exists():
        try:
            return pd.read_parquet(SNAPSHOT_PATH)
        except Exception:
            pass
    return _fetch_and_snapshot()


def _district_matches_area(district: str, area: str | None) -> bool:
    if area is None or (isinstance(area, float) and pd.isna(area)):
        return False
    d = district.lower().strip()
    a = str(area).lower().strip()
    return d in a or a in d or d.split()[0] in a or a.split()[0] in d


def cross_check_live_prices(district: str) -> dict | None:
    """Reconcile live sale price/sqm against synthetic baseline."""
    try:
        df = get_live_listings()
        if df is None or df.empty:
            return None

        area_col = "area" if "area" in df.columns else None
        if area_col is None:
            return None

        subset = df[df[area_col].apply(lambda a: _district_matches_area(district, a))]
        if subset.empty:
            return None

        if "transaction_type_guess" in subset.columns:
            subset = subset[subset["transaction_type_guess"] == "sale"]
        if "area_in_abu_dhabi" in subset.columns:
            subset = subset[subset["area_in_abu_dhabi"] == True]  # noqa: E712
        if subset.empty or "price_per_sqm" not in subset.columns:
            return None

        live_median = float(subset["price_per_sqm"].median())
        profile = get_district_profile(district)
        synthetic_baseline = profile.get("base_sale_aed_sqm")

        if synthetic_baseline is None:
            txns = load_transactions()
            dist_c = "district" if "district" in txns.columns else None
            if dist_c:
                dtx = txns[txns[dist_c].str.lower() == district.lower()]
                if not dtx.empty and "price_per_sqm" in dtx.columns:
                    synthetic_baseline = float(dtx["price_per_sqm"].median())

        if synthetic_baseline is None or synthetic_baseline == 0:
            return None

        pct_delta = round((live_median - synthetic_baseline) / synthetic_baseline * 100, 1)
        n_mislabeled = 0
        if "price_looks_like_sale" in df.columns:
            district_all = df[df[area_col].apply(lambda a: _district_matches_area(district, a))]
            n_mislabeled = int(district_all["price_looks_like_sale"].sum())

        return {
            "live_median": round(live_median),
            "synthetic_baseline": int(synthetic_baseline),
            "pct_delta": pct_delta,
            "n_listings": len(subset),
            "n_mislabeled_rent_vs_sale": n_mislabeled,
        }
    except Exception:
        return None
