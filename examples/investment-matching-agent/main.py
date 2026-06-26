"""Investment Matching Agent — pair investor mandates with parcels.

Runs locally with no API keys. Scoring and rationales are rules-based;
swap in a real model at the marked section for richer output.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
HF_BASE = "https://huggingface.co/datasets/eVoost/abu-dhabi-ai-proptech-challenge/resolve/main/"


def data_source(filename: str) -> str:
    """Local CSV when running inside the starter kit; Hugging Face otherwise."""
    local = DATA_DIR / filename
    return str(local) if local.exists() else HF_BASE + filename
TOP_MATCHES = 3
SAMPLE_INVESTORS = 3

# Sector → compatible land uses
SECTOR_LAND_USE = {
    "residential": {"residential", "mixed_use"},
    "commercial": {"commercial", "mixed_use"},
    "hospitality": {"hospitality", "mixed_use"},
    "mixed_use": {"mixed_use", "residential", "commercial"},
    "logistics": {"industrial"},
    "industrial": {"industrial"},
    "community": {"community", "residential"},
}

# Risk profile → how much undeveloped status is tolerated
RISK_STATUS_BONUS = {
    "conservative": {"developed": 15, "under_development": 5, "vacant": 0, "reserved": 0},
    "balanced": {"developed": 5, "under_development": 10, "vacant": 8, "reserved": 3},
    "aggressive": {"developed": 0, "under_development": 8, "vacant": 15, "reserved": 10},
}


def parse_capital_max_aed(capital_range: str) -> float:
    """'50M-200M' -> 200_000_000; '600M-2.5B' -> 2_500_000_000."""
    upper = capital_range.split("-")[-1].strip().upper()
    multiplier = 1_000_000_000 if upper.endswith("B") else 1_000_000
    return float(upper.rstrip("MB")) * multiplier


def match_score(investor: pd.Series, parcel: pd.Series) -> float:
    """Fit score in [0, 100] for one investor x parcel pair."""
    score = 0.0

    # Sector fit (0-35)
    compatible = SECTOR_LAND_USE.get(investor["preferred_sector"], set())
    if parcel["land_use"] in compatible:
        score += 35 if parcel["land_use"] == investor["preferred_sector"] else 25

    # District preference (0-20)
    if parcel["district"] == investor["preferred_district"]:
        score += 20

    # Capital fit (0-20): parcel must be affordable within the mandate
    if parcel["estimated_value_aed"] <= parse_capital_max_aed(investor["capital_range_aed"]):
        score += 20

    # Risk alignment (0-15)
    score += RISK_STATUS_BONUS[investor["risk_profile"]][parcel["current_status"]]

    # Quality signal (0-10)
    score += parcel["development_potential_score"] / 10

    return round(score, 1)


def explain_match(investor: pd.Series, parcel: pd.Series, score: float) -> str:
    """One-line rationale for a match.

    # --- CONNECT YOUR MODEL HERE ---
    # The high-value upgrade: generate a one-page deal memo per match.
    # Build a prompt from both records and call OpenAI / Anthropic /
    # Hugging Face / a local model — snippets in the land-intelligence-agent README.
    prompt = (
        f"Write a one-page investment memo matching this investor {investor.to_dict()} "
        f"with this parcel {parcel.to_dict()}. Include thesis, risks, and next steps."
    )
    """
    reasons = []
    if parcel["land_use"] == investor["preferred_sector"]:
        reasons.append("exact sector match")
    if parcel["district"] == investor["preferred_district"]:
        reasons.append("preferred district")
    if parcel["development_potential_score"] >= 80:
        reasons.append("high development potential")
    reason_text = ", ".join(reasons) if reasons else "broad mandate compatibility"
    return (
        f"{parcel['parcel_id']} ({parcel['district']}, {parcel['land_use']}, "
        f"AED {parcel['estimated_value_aed']:,}) — fit {score}/100: {reason_text}."
    )


def main() -> None:
    investors = pd.read_csv(data_source("sample_investors.csv"))
    parcels = pd.read_csv(data_source("sample_parcels.csv"))

    print("\n=== Investment Matching Agent ===")
    for _, investor in investors.head(SAMPLE_INVESTORS).iterrows():
        print(
            f"\n{investor['investor_id']} — {investor['investor_type']} | "
            f"sector: {investor['preferred_sector']} | capital: {investor['capital_range_aed']} | "
            f"risk: {investor['risk_profile']}"
        )
        scored = [
            (match_score(investor, parcel), parcel)
            for _, parcel in parcels.iterrows()
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        for score, parcel in scored[:TOP_MATCHES]:
            print(f"  • {explain_match(investor, parcel, score)}")
    print()


if __name__ == "__main__":
    main()
