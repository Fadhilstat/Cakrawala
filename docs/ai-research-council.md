# AI Research Council

Cakrawala can use ChatGPT as an external research layer without embedding a paid OpenAI API call in
every Streamlit session. The web application reads a small validated JSON brief from the repository,
while a scheduled ChatGPT task performs the fresh-source research outside the app.

## Roles

The daily council separates seven responsibilities:

1. **News Analyst** reviews policy, regulatory, macro, and market headlines.
2. **Macro Analyst** reviews inflation, growth, rates, liquidity, and scheduled event risk.
3. **Market Analyst** reviews price structure, breadth, volatility, positioning, and regime evidence.
4. **Risk Analyst** looks for concentration, crowding, event, liquidity, and execution risks.
5. **Quant and Model Steward** checks whether model evidence is healthy enough to be trusted.
6. **Indonesia Analyst** focuses on Indonesia-relevant economic, market, weather, and disaster context.
7. **Chief Research Editor** reconciles consensus, disagreements, caveats, and follow-up checks.

Each role must report confidence, evidence, and risks. The editor can publish only `RISK ON`,
`CAUTIOUS`, `RISK OFF`, `MIXED`, or `INSUFFICIENT EVIDENCE` as a research stance.

## Security and decision boundary

The council is not part of the execution policy. It cannot create BUY, SELL, LONG, SHORT, targets,
or order instructions. It cannot replace model-health, freshness, authorization, risk, or signal
gates. If current source verification is weak, the correct outcome is `INSUFFICIENT EVIDENCE`.

The scheduled task may update only `data/ai_briefs/latest.json`. It must use a GitHub feature branch,
validate the JSON schema and HTTPS citations, and merge only a data-only pull request whose changed
file list contains exactly that file. It must never modify dependencies or application code during
a research update.

A brief with status `ready` must include at least one analyst role and one unique HTTPS citation.
Every citation records when the source was checked, and that verification must be no more than 48
hours older than the generated brief. `source_count` must match the number of unique citation URLs.
Placeholder, failed, zero-source, duplicate-source, and internally inconsistent briefs remain
visible as unavailable context and cannot be labelled fresh research.

## Cost model

This design does not require an OpenAI API key in Streamlit and does not create per-page OpenAI API
usage. It relies on the user's existing ChatGPT task capability plus free or already-approved public
sources. ChatGPT product-plan availability is separate from OpenAI API billing, so the project does
not claim that the OpenAI API itself is free.

## Freshness

The UI treats a council brief older than 36 hours as stale. A stale brief remains visible only as
historical context and is not presented as current research. The web terminal continues to operate
with deterministic analytics when no valid AI brief is available.

