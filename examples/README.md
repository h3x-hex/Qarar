# Example Agents

Three small, runnable examples — one per major pattern you might build during the challenge. Each runs **locally with no API keys** using a transparent rules-based engine, and each marks exactly where to swap in a real model (OpenAI, Anthropic, Hugging Face, or local).

| Example | Pattern | Track |
|---|---|---|
| [`land-intelligence-agent/`](land-intelligence-agent/) | Score + explain: rank parcels by development potential | Land Intelligence |
| [`investment-matching-agent/`](investment-matching-agent/) | Match + rank: pair investor mandates with parcels | Investment Intelligence |
| [`decision-copilot/`](decision-copilot/) | Q&A over data: answer questions across all four datasets | Decision Intelligence |
| 🎁 [`live-data-connector/`](live-data-connector/) | **Bonus** — pull real, live Abu Dhabi listings from eVoost's API (messy real-world data) | Investment Intelligence · Future Communities |

## Running an example

```bash
# one-time setup, from the starter-kit root:
./quickstart.sh
# then run any example:
.venv/bin/python examples/land-intelligence-agent/main.py
```

Each `main.py` reads from `../../data/`, so run from inside the example's folder.

## Upgrading to a real model

Every example has a function marked `# --- CONNECT YOUR MODEL HERE ---`. The rules-based version returns structured output; replace it with an LLM call and keep the same return shape. Provider snippets are in each example's README.

These are starting points, not solutions — fork the pattern, not the code.
