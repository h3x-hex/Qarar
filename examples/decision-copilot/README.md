# Decision Copilot

Answers natural-language questions across all four datasets — the "Q&A over data" pattern behind decision copilots and automated briefings.

## Run it

```bash
# one-time setup, from the starter-kit root:
../../quickstart.sh
# then run this agent:
../../.venv/bin/python main.py
```

No API keys needed. It runs three sample questions and prints sourced answers; pass your own question as an argument:

```bash
../../.venv/bin/python main.py "Which district has the most unmet service demand?"
```

## How it works

1. Loads all four CSVs from `../../data/`
2. Routes the question to a handler using keyword intent matching
3. Each handler queries the data with pandas and returns an answer **with the numbers that back it**

The router is intentionally the weakest part — it's the piece an LLM replaces best. With a real model you can do tool-calling: let the LLM choose which pandas query to run, then narrate the result.

## Connect a model

In `main.py`, find `# --- CONNECT YOUR MODEL HERE ---`. Two upgrade paths:

1. **Narration:** keep the handlers, have the LLM turn their structured output into an executive answer.
2. **Tool calling:** expose the handlers as tools and let the model route and compose them — the real copilot architecture. Provider snippets in the [land-intelligence-agent README](../land-intelligence-agent/README.md).

## Ideas to extend

- A morning-briefing mode: one command produces a cross-dataset daily summary
- Scenario questions: "if Zayed City adds 5,000 residents, what's the service gap?"
- Wrap it in the `project-template` dashboard for a demo-ready UI
- Add citations: every claim links to the rows it came from
