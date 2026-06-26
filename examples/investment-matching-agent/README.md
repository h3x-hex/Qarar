# Investment Matching Agent

Pairs investor mandates with land parcels and explains each match — the "match + rank" pattern.

## Run it

```bash
# one-time setup, from the starter-kit root:
../../quickstart.sh
# then run this agent:
../../.venv/bin/python main.py
```

No API keys needed. Output: the top parcel matches for each of three sample investors, with fit scores and one-line rationales.

## How it works

1. Loads `sample_investors.csv` and `sample_parcels.csv` from `../../data/`
2. Scores every investor × parcel pair on sector fit, district preference, capital fit, and risk alignment
3. Ranks matches and generates a rationale per pair

The scoring and rationale are rules-based so the example runs anywhere. The natural upgrade: have an LLM write a proper one-page deal memo per match.

## Connect a model

In `main.py`, find `# --- CONNECT YOUR MODEL HERE ---`. Provider snippets (OpenAI, Anthropic, Hugging Face, Ollama) are in the [land-intelligence-agent README](../land-intelligence-agent/README.md) — the integration is identical.

## Ideas to extend

- Generate full deal memos with an LLM (asset case, risks, comparable transactions from `sample_transactions.csv`)
- Add a two-sided view: best investors *for a parcel*, not just parcels for an investor
- Use transaction history to add momentum/pricing signals to the fit score
- Build embeddings over mandates and parcels for semantic matching
