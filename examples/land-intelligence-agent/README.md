# Land Intelligence Agent

Ranks land parcels by development opportunity and generates a plain-language recommendation for each — the "score + explain" pattern.

## Run it

```bash
# one-time setup, from the starter-kit root:
../../quickstart.sh
# then run this agent:
../../.venv/bin/python main.py
```

No API keys needed. Output: the top 5 parcels with composite opportunity scores and generated recommendations.

## How it works

1. Loads `sample_parcels.csv` and `sample_communities.csv` from `../../data/`
2. Joins them on `district` so land supply meets community demand
3. Computes a composite opportunity score (development potential + infrastructure + local service demand)
4. Generates a recommendation paragraph for each top parcel

Step 4 is rules-based by default so the example runs anywhere. Replace `generate_recommendation()` with a real model for far richer output.

## Connect a model

In `main.py`, find `# --- CONNECT YOUR MODEL HERE ---` and swap in your provider:

```python
# Anthropic
from anthropic import Anthropic
client = Anthropic()  # reads ANTHROPIC_API_KEY
msg = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=300,
    messages=[{"role": "user", "content": prompt}],
)
return msg.content[0].text

# OpenAI
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY
resp = client.chat.completions.create(
    model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
)
return resp.choices[0].message.content

# Local via Ollama
import requests
resp = requests.post("http://localhost:11434/api/generate",
                     json={"model": "llama3.2", "prompt": prompt, "stream": False})
return resp.json()["response"]
```

## Ideas to extend

- Let users ask in natural language ("waterfront parcels good for hospitality")
- Add a what-if mode: rescore parcels under a hypothetical new transit link
- Visualize scores on a map (the `project-template` dashboard is a good shell)
