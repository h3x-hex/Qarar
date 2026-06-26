# 🎁 Bonus: Live UAE Property-Data Connector

**Optional.** The six synthetic datasets in [`../../data`](../../data) are your primary, clean, guaranteed-available data — build on those first. This connector is for teams who want to go further and work with **real, live Abu Dhabi listings** pulled from eVoost's UAE data API.

Why bother? Real-world data is messy, and turning mess into signal is exactly the kind of thing the intelligence layer this challenge is about has to do. Pulling it off is a genuine differentiator in front of the judges.

## What it is

A small Python client (`main.py`) that queries the live `/listings/search` and `/areas` endpoints and returns a cleaned pandas DataFrame of Abu Dhabi rent/buy listings — `fetch_listings()` + `clean()` are yours to build on.

## Get a key (not in this repo)

The API key is **not committed here** (public repo). Grab the event key from the organizers — it's pinned in Discord **#resources / #help-desk**. Then:

```bash
# after running ../../quickstart.sh from the starter-kit root
export UAE_DATA_API_KEY="uae_..."        # macOS / Linux  (Windows: $env:UAE_DATA_API_KEY="uae_...")
../../.venv/bin/python main.py
```

## ⚠️ This is real scraped data — expect mess (that's the point)

We found these quirks; the connector handles them, but you should understand them:

1. **`transaction_type` is unreliable** — some `rent` rows carry sale-sized prices. `clean()` adds `price_looks_like_sale` and `transaction_type_guess` (price-based).
2. **The emirate filter leaks** — a few Sharjah areas (e.g. Aljada, Tilal City) show up under "Abu Dhabi". `clean()` adds an `area_in_abu_dhabi` flag.
3. **Sparse fields** — `area`, `bathrooms`, `building_id` are often null; ~80% of raw rows lack a price or built-up area and get dropped by `clean()`. Usable Abu Dhabi volume is a few hundred listings, skewed to the premium islands.
4. **Dev environment** — uptime and rate limits aren't guaranteed during the event. Cache what you pull; don't hammer it.

## Ideas

- Reconcile listing prices against the synthetic `sample_transactions` / `districts` to spot over/under-priced areas.
- Geocode + map listings against `sample_communities` demand.
- Build a "is this rent or sale, really?" classifier — the mislabeling is a fun supervised-learning toy.
- A data-quality agent that scores and repairs the feed (very on-theme).

Stuck or the API misbehaves? Ask in Discord **#help-desk** — and remember, **nothing here is required**; your synthetic-data prototype stands on its own.
