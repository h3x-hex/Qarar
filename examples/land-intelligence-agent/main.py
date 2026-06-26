"""Land Intelligence Agent — score parcels and explain the opportunity.

Runs locally with no API keys. The recommendation step is rules-based by
default; swap in a real model at the marked section below.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
HF_BASE = "https://huggingface.co/datasets/eVoost/abu-dhabi-ai-proptech-challenge/resolve/main/"


def data_source(filename: str) -> str:
    """Local CSV when running inside the starter kit; Hugging Face otherwise."""
    local = DATA_DIR / filename
    return str(local) if local.exists() else HF_BASE + filename
TOP_N = 5


def load_data() -> pd.DataFrame:
    """Join parcels with district-level community demand."""
    parcels = pd.read_csv(data_source("sample_parcels.csv"))
    communities = pd.read_csv(data_source("sample_communities.csv"))

    # Average community metrics per district (districts can have several communities)
    district_demand = (
        communities.groupby("district")[["service_demand_index", "mobility_score"]]
        .mean()
        .rename(columns={"service_demand_index": "avg_service_demand",
                         "mobility_score": "avg_mobility"})
    )
    return parcels.merge(district_demand, on="district", how="left").fillna(0)


def score_parcels(df: pd.DataFrame) -> pd.DataFrame:
    """Composite opportunity score in [0, 100].

    Weights are deliberately simple — tune them, or replace the whole thing
    with a learned model.
    """
    df = df.copy()
    df["opportunity_score"] = (
        0.40 * df["development_potential_score"]
        + 0.25 * df["infrastructure_score"]
        + 0.20 * df["avg_service_demand"]          # unmet demand nearby = opportunity
        + 0.15 * (df["current_status"] == "vacant") * 100  # vacant land is actionable now
    ).round(1)
    return df.sort_values("opportunity_score", ascending=False)


def generate_recommendation(parcel: pd.Series) -> str:
    """Turn a scored parcel into a plain-language recommendation.

    # --- CONNECT YOUR MODEL HERE ---
    # Build a prompt from the parcel fields and call your provider:
    #   - OpenAI / Anthropic / Hugging Face: see README.md for snippets
    #   - Local models: point at Ollama or llama.cpp
    # Keep the return type (str) and the rest of the script works unchanged.
    prompt = (
        f"You are a land development analyst. In 2-3 sentences, recommend how to "
        f"develop this parcel and why: {parcel.to_dict()}"
    )
    """
    drivers = []
    if parcel["development_potential_score"] >= 80:
        drivers.append("high modeled development potential")
    if parcel["infrastructure_score"] >= 85:
        drivers.append("strong surrounding infrastructure")
    if parcel["avg_service_demand"] >= 70:
        drivers.append("significant unmet service demand in the district")
    if parcel["current_status"] == "vacant":
        drivers.append("immediately available status")

    driver_text = "; ".join(drivers) if drivers else "a balanced profile across factors"
    return (
        f"Recommend advancing {parcel['parcel_id']} ({parcel['district']}, "
        f"{parcel['parcel_size_sqm']:,} sqm, zoned {parcel['zone']}) toward "
        f"{parcel['recommended_use'].replace('_', ' ')}. "
        f"Key drivers: {driver_text}. "
        f"Estimated value AED {parcel['estimated_value_aed']:,}."
    )


def main() -> None:
    df = score_parcels(load_data())
    print("\n=== Land Intelligence Agent — Top Opportunities ===\n")
    for _, parcel in df.head(TOP_N).iterrows():
        print(f"[{parcel['opportunity_score']:>5.1f}] {generate_recommendation(parcel)}\n")


if __name__ == "__main__":
    main()
