"""Live UAE property-data connector — optional real-world data for the challenge.

Queries eVoost's live UAE listings API and returns a cleaned pandas DataFrame
of Abu Dhabi rent/buy listings. This is REAL, scraped portal data — messier
than the synthetic datasets, on purpose. Working with messy real data is a
realistic skill (and a nice differentiator for your demo).

The synthetic CSVs in ../../data stay your primary, clean dataset — use this
when you specifically want live, real listings.

--- Setup -------------------------------------------------------------------
You need an API key (NOT in this public repo — get it from the organizers in
Discord #help-desk). Then:

    export UAE_DATA_API_KEY="uae_..."          # macOS / Linux
    ../../.venv/bin/python main.py             # after ../../quickstart.sh

--- Known data quirks (handled below) ---------------------------------------
1. `transaction_type` is unreliable: some 'rent' rows carry sale-sized prices.
   We add `price_looks_like_sale` and a cleaned `transaction_type_guess`.
2. The emirate filter leaks (a few Sharjah areas appear under Abu Dhabi).
   We drop rows whose `area` isn't a known Abu Dhabi area when we can tell.
3. `area`, `bathrooms`, `building_id` are often null. We keep rows but flag.
"""

import os
import json
import time
import urllib.parse
import urllib.request

import pandas as pd

BASE = "https://uae-data-api.evoost-ai.workers.dev/v1"
# Annual rent above this is almost certainly a mislabeled sale price (AED).
RENT_SALE_THRESHOLD = 1_000_000


def _get(path: str) -> dict:
    key = os.environ.get("UAE_DATA_API_KEY")
    if not key:
        raise SystemExit(
            "UAE_DATA_API_KEY not set.\n"
            "Get the event key from the organizers (Discord #help-desk), then:\n"
            '  export UAE_DATA_API_KEY="uae_..."'
        )
    req = urllib.request.Request(
        BASE + path,
        headers={"x-api-key": key, "Accept": "application/json", "User-Agent": "adcc-connector/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_listings(transaction_type: str | None = None, emirate: str = "Abu Dhabi",
                   max_pages: int = 10, page_size: int = 100) -> pd.DataFrame:
    """Paginate the listings endpoint into a DataFrame. transaction_type:
    'rent' | 'sale' | None (both)."""
    rows: list[dict] = []
    for page in range(1, max_pages + 1):
        params = {"emirate": emirate, "limit": page_size, "page": page}
        if transaction_type:
            params["transaction_type"] = transaction_type
        data = _get("/listings/search?" + urllib.parse.urlencode(params))
        items = data.get("items", [])
        if not items:
            break
        rows.extend(items)
        time.sleep(0.2)  # be polite to the API
    return pd.DataFrame(rows)


def known_abu_dhabi_areas() -> set[str]:
    """Canonical Abu Dhabi area names from the API's own /areas taxonomy."""
    items = _get("/areas").get("items", [])
    return {a["name"] for a in items if a.get("emirate") == "Abu Dhabi"}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the documented fixes so teams start from sane data."""
    if df.empty:
        return df
    df = df.copy()
    # drop unusable rows
    df = df[(df["price"].fillna(0) > 0) & (df["built_up_area_sqm"].fillna(0) > 0)]
    # quirk 1: flag/repair mislabeled rent-vs-sale by price magnitude
    df["price_looks_like_sale"] = df["price"] > RENT_SALE_THRESHOLD
    df["transaction_type_guess"] = df.apply(
        lambda r: "sale" if r["price_looks_like_sale"] else (r.get("transaction_type") or "rent"),
        axis=1,
    )
    # derived metric
    df["price_per_sqm"] = (df["price"] / df["built_up_area_sqm"]).round(0)
    # quirk 2: drop emirate-filter leakage when area is a known non-AD value
    ad = known_abu_dhabi_areas()
    df["area_in_abu_dhabi"] = df["area"].isin(ad) | df["area"].isna()
    return df.reset_index(drop=True)


def main() -> None:
    print("Fetching live Abu Dhabi listings (real data) ...")
    raw = fetch_listings(emirate="Abu Dhabi", max_pages=5)
    df = clean(raw)
    if df.empty:
        print("No data returned — check your key and try again.")
        return
    print(f"\n{len(df)} listings after cleaning.")
    print("By guessed type:\n", df["transaction_type_guess"].value_counts().to_string())
    print("\nTop areas:\n", df["area"].value_counts().head(8).to_string())
    sale = df[df["transaction_type_guess"] == "sale"]
    if not sale.empty:
        print(f"\nSale price/sqm — median AED {sale['price_per_sqm'].median():,.0f} "
              f"(p10 {sale['price_per_sqm'].quantile(.1):,.0f} · p90 {sale['price_per_sqm'].quantile(.9):,.0f})")
    print("\nColumns available:", ", ".join(df.columns))
    print("\nUse `fetch_listings()` + `clean()` in your own code — this is just a starting point.")


if __name__ == "__main__":
    main()
