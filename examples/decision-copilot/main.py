"""Decision Copilot — answer questions across all four city datasets.

Runs locally with no API keys. Intent routing is keyword-based by default —
exactly the part a real LLM (via tool calling) replaces best.

Usage:
    python main.py                          # runs three sample questions
    python main.py "your question here"     # asks your own
"""

import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
HF_BASE = "https://huggingface.co/datasets/eVoost/abu-dhabi-ai-proptech-challenge/resolve/main/"


def data_source(filename: str) -> str:
    """Local CSV when running inside the starter kit; Hugging Face otherwise."""
    local = DATA_DIR / filename
    return str(local) if local.exists() else HF_BASE + filename


def load_all() -> dict[str, pd.DataFrame]:
    return {
        "parcels": pd.read_csv(data_source("sample_parcels.csv")),
        "investors": pd.read_csv(data_source("sample_investors.csv")),
        "transactions": pd.read_csv(data_source("sample_transactions.csv"), parse_dates=["date"]),
        "communities": pd.read_csv(data_source("sample_communities.csv")),
    }


# --- Handlers: each answers one kind of question, with sources -------------

def answer_service_demand(data: dict) -> str:
    by_district = (
        data["communities"].groupby("district")["service_demand_index"].mean().sort_values(ascending=False)
    )
    top = by_district.head(3)
    lines = [f"  - {district}: avg demand index {value:.0f}/100" for district, value in top.items()]
    return (
        "Highest unmet service demand (avg across communities):\n" + "\n".join(lines)
        + "\n  Source: sample_communities.csv, service_demand_index"
    )


def answer_price_trends(data: dict) -> str:
    tx = data["transactions"]
    by_district = tx.groupby("district")["price_per_sqm"].mean().sort_values(ascending=False)
    top = by_district.head(3)
    lines = [f"  - {district}: AED {value:,.0f}/sqm" for district, value in top.items()]
    return (
        "Highest average transaction prices:\n" + "\n".join(lines)
        + f"\n  Source: sample_transactions.csv, {len(tx)} transactions "
        + f"({tx['date'].min():%b %Y} – {tx['date'].max():%b %Y})"
    )


def answer_development_opportunity(data: dict) -> str:
    parcels = data["parcels"]
    vacant = parcels[parcels["current_status"] == "vacant"]
    top = vacant.nlargest(3, "development_potential_score")
    lines = [
        f"  - {row.parcel_id} ({row.district}): potential {row.development_potential_score}/100, "
        f"suggested {row.recommended_use.replace('_', ' ')}"
        for row in top.itertuples()
    ]
    return (
        "Top vacant parcels by development potential:\n" + "\n".join(lines)
        + "\n  Source: sample_parcels.csv, filtered to current_status == 'vacant'"
    )


def answer_capital_supply(data: dict) -> str:
    investors = data["investors"]
    by_sector = investors["preferred_sector"].value_counts().head(3)
    lines = [f"  - {sector}: {count} active mandates" for sector, count in by_sector.items()]
    return (
        "Where investor capital is pointed (by mandate count):\n" + "\n".join(lines)
        + f"\n  Source: sample_investors.csv, {len(investors)} investor profiles"
    )


# --- Router -----------------------------------------------------------------

INTENTS = [
    ({"service", "demand", "school", "clinic", "community", "resident"}, answer_service_demand),
    ({"price", "prices", "transaction", "market", "expensive", "sqm"}, answer_price_trends),
    ({"parcel", "land", "develop", "development", "vacant", "build"}, answer_development_opportunity),
    ({"investor", "capital", "invest", "fund", "mandate"}, answer_capital_supply),
]


def route(question: str, data: dict) -> str:
    """Pick the handler whose keywords best overlap the question.

    # --- CONNECT YOUR MODEL HERE ---
    # This keyword router is the weakest link by design. Two upgrades:
    #  1. Narration: call a handler, then have an LLM (OpenAI / Anthropic /
    #     Hugging Face / local) rewrite its output as an executive answer.
    #  2. Tool calling: register each handler as a tool and let the model
    #     route, compose, and cite — the real copilot architecture.
    # Provider snippets: ../land-intelligence-agent/README.md
    """
    words = set(question.lower().replace("?", "").split())
    best_handler, best_overlap = None, 0
    for keywords, handler in INTENTS:
        overlap = len(words & keywords)
        if overlap > best_overlap:
            best_handler, best_overlap = handler, overlap
    if best_handler is None:
        return (
            "I couldn't route that question. Try asking about service demand, "
            "market prices, land development, or investor capital."
        )
    return best_handler(data)


def main() -> None:
    data = load_all()
    questions = (
        [" ".join(sys.argv[1:])]
        if len(sys.argv) > 1
        else [
            "Which districts have the most unmet service demand?",
            "Where are transaction prices highest?",
            "Which vacant land should we develop first?",
        ]
    )
    print("\n=== Decision Copilot ===")
    for question in questions:
        print(f"\nQ: {question}\n{route(question, data)}")
    print()


if __name__ == "__main__":
    main()
