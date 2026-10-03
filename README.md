# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and a disciplined private trading-research workspace.**

Cakrawala brings market, macro, positioning, event, model, and risk evidence into one workflow without pretending that one indicator or one AI model can explain the market. The project has two deliberately separate surfaces: a public research product and an owner-only decision-preparation environment.

**Public app:** `https://cakrawala-terminal.streamlit.app`

The Streamlit app is the public portfolio and education surface. Personal research is intentionally kept out of its navigation.

The public interface uses a compact corporate terminal system with grouped navigation,
visible source health, explicit runtime degradation, responsive mobile layouts, keyboard
focus states, and reduced-motion support. The design keeps operational evidence ahead of
decorative elements so users can understand the current state before reading an analysis.

The Vercel deployment is kept for personal use and is protected inside the application with a username and password. Its URL is not part of the public portfolio. The password itself is never stored in the repository or environment as plaintext. Vercel receives only a Werkzeug-compatible password hash plus a separate session secret.

## Why this project exists

Market decisions are usually made across fragmented tabs: price action in one place, macro releases somewhere else, positioning in a weekly report, and news without a clear risk framework. Cakrawala turns those pieces into an evidence-first sequence:

**context -> evidence quality -> scenario -> risk gate -> decision -> review -> improve**

The public side is useful for learning and transparent research. The private side is meant to help the owner prepare decisions more consistently. Neither side sends real-money orders.

## Public Streamlit terminal

The public terminal includes:

- **Overview** for source health, market movement, momentum, realized volatility, futures crowding, Indonesia context, and BMKG evidence.
- **AI Research Council** for a daily structured research brief with separate News, Macro, Market, Risk, Quant/Model, Indonesia, and Chief Editor roles.
- **News & Research** using official Federal Reserve, BIS, and ECB feeds where available.
- **Positioning** that keeps Binance crowding and CFTC institutional positioning conceptually separate.
- **Market Desk and Market Structure** for price and risk context.
- **Macro & Events** for Indonesia macro evidence and scheduled BLS event risk.
- **Research Desk, Risk Tools, Trader Toolkit, Tool Radar, and Execution Readiness** for transparent analysis and planning.

Public Streamlit does not expose the owner portfolio, private journal, private playbook, Personal Forex Desk, or AI Decision Lab.

Streamlit Community Cloud is retained because it is suitable for a public portfolio surface without mandatory hosting cost at the current MVP stage.

## Personal Vercel research surface

The owner workflow uses Vercel for personal research. It is not the public portfolio homepage and its URL should not be published in the CV, README project links, LinkedIn post, or portfolio site.

The zero-cost application boundary is:

```text
Vercel Hobby
   |
   +-- application credential gate
          |
          +-- username
          +-- password hash
          +-- secure server-side session policy
          |
          +-- Dash research terminal
          +-- /personal/ai-lab
          +-- /personal/forex
          +-- private storage only after provisioning
```

The credential gate protects the Dash layout, callback endpoints, assets, private research routes, and root application. `/healthz` remains unauthenticated so deployment health can be checked without exposing research content.

The login form has CSRF protection, `no-store` caching, `noindex` headers, secure and HTTP-only session cookies, and an optional seven-day remembered session. Missing authentication configuration fails closed instead of exposing the application.

Required Vercel environment variables are:

```text
PERSONAL_AUTH_USERNAME
PERSONAL_AUTH_PASSWORD_HASH
WEB_SESSION_SECRET
PERSONAL_OWNER_ID
```

`PERSONAL_OWNER_ID` can be omitted and will fall back to the username. It exists as a stable storage key so changing a display username later does not have to change private database ownership.

Generate the password hash locally and store only the resulting hash in Vercel. One example is:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash(input('Password: ')))"
```

Use a long unique password. Never commit the password, its generated environment file, or the session secret.

See `docs/private-public-split.md`.

## Personal Forex Desk

The owner-only Forex Desk combines free and traceable evidence for daily preparation:

- EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, and EURGBP reference boards;
- official ECB daily reference-rate context and multi-horizon changes;
- CFTC TFF positioning for major currency futures;
- upcoming BLS event risk;
- official Federal Reserve, BIS, and ECB headlines;
- Asia, London, and New York session context;
- a pre-trade discipline checklist.

ECB values are clearly treated as reference rates, not executable broker prices. CFTC TFF is weekly evidence, not live institutional order flow.

## AI Decision Lab

The owner-only `/personal/ai-lab` adds a deterministic preparation layer before any AI narrative is considered.

For each supported FX pair it evaluates the 1D, 5D, and 20D reference-rate direction, source freshness, and nearby official event risk. The result is an evidence state such as:

- `ALIGNED`
- `MIXED`
- `WAIT_EVENT`
- `INSUFFICIENT`

This matrix is not a BUY or SELL signal. Its purpose is to stop weak, stale, or event-sensitive evidence from being presented as a confident trade idea.

The private Daily Forex Council then adds a separate multi-role interpretation layer. Its Risk Manager is explicitly required to challenge directional views and to prefer waiting when evidence is weak.

## AI and model research radar

Cakrawala studies AI trading and financial-research projects as references, not as shortcuts to profitable trading.

Current research candidates include:

| Candidate | Use | License status | Cakrawala status |
| --- | --- | --- | --- |
| TradingAgents | Multi-agent research and debate patterns | Apache-2.0 | Architecture reference |
| FinRL | Reinforcement-learning research | MIT | Sandbox candidate |
| Microsoft Qlib | Reproducible quantitative research architecture | MIT | Architecture reference |
| Amazon Chronos-Bolt | Probabilistic time-series forecasting | Apache-2.0 | Sandbox candidate |
| IBM Granite TinyTimeMixer R2.1 | Compact time-series forecasting | Apache-2.0 | Sandbox candidate |
| ProsusAI FinBERT | Financial sentiment tagging | Verify before integration | Observe only |

The radar is stored in `configs/ai_research_radar.yaml` and is rechecked by scheduled research automation. A model card or README performance claim is never treated as evidence of trading edge.

Heavy models are deliberately kept out of the Vercel request path. They belong in scheduled GitHub Actions or a local research sandbox so the owner app stays responsive and no paid compute service becomes mandatory.

The first Chronos-Bolt Tiny FX validation also failed its research gate against a simple last-value benchmark. It remains research-only. That result is documented rather than tuned away.

See `docs/ai-trading-research.md` and `docs/fx-foundation-model.md`.

## Model promotion policy

A model remains research-only until it passes all applicable gates:

1. point-in-time features and targets;
2. completed observations only;
3. rolling or expanding walk-forward evaluation;
4. a simple benchmark comparison;
5. probability calibration metrics when probabilities are produced;
6. documented transaction-cost assumptions for strategy diagnostics;
7. no future news, revised macro data, or finalized event leakage;
8. reproducible model revision and source provenance;
9. model-health and freshness checks;
10. independent risk review.

The first trained BTC direction baseline, `logistic_direction_v1`, did not beat its probability benchmark. It therefore remains `research_only` and is not connected to the production direction role. That rejection is expected behavior, not a failure of the project.

## Data sources

The current evidence layer prefers public or official interfaces that do not require a paid subscription for the portfolio workflow.

| Evidence | Provider |
| --- | --- |
| Indonesia statistics | BPS where configured |
| Weather and earthquakes | BMKG |
| Global macro | World Bank |
| Macro series | FRED where configured |
| Spot market structure | Binance public market data |
| Futures crowding | Binance USD-M Futures public endpoints |
| Currency reference context | European Central Bank |
| Institutional positioning | CFTC TFF Futures-Only |
| Scheduled U.S. releases | BLS official calendar |
| Central-bank and policy news | Federal Reserve, BIS, ECB |

Every external response is treated as untrusted at the network boundary. Provider code uses the controls appropriate to each source, including HTTPS, host allowlists, bounded timeouts and retries, response-size limits, content-type checks, schema validation, provenance, and explicit failure handling.

If a source is unavailable, Cakrawala shows it as unavailable. It does not create synthetic replacement data to make the dashboard look healthy.

See `docs/sources.md`.

## Architecture

```text
app/streamlit_app.py            public Streamlit entrypoint
app/dash_app.py                 private Dash research application
main.py                         native Vercel WSGI bridge
src/cakrawala/data/             provider adapters, validation, provenance
src/cakrawala/intelligence/     research, risk, models, decision-prep policy
src/cakrawala/web/              credential gate and owner research routes
src/cakrawala/personal/         private storage access
configs/                        source, signal, model, tool, and AI research policies
data/ai_briefs/                 validated scheduled public AI brief
migrations/personal/            private database migrations
tests/                          regression, security, data, and runtime tests
.github/workflows/              CI, source health, and model validation
```

Public evidence may use bounded shared caching. Private owner rows never enter that cache.

## Personal storage boundary

Stored Personal Mode features remain fail-closed until real infrastructure is configured:

```text
PERSONAL_AUTH_USERNAME
PERSONAL_AUTH_PASSWORD_HASH
WEB_SESSION_SECRET
PERSONAL_OWNER_ID
DATABASE_PERSONAL_URL
```

Private portfolio, trade plans, journal, and playbook records require a separate PostgreSQL connection and the personal migrations. No placeholder credential is committed to the repository.

The Forex Desk and AI Decision Lab can operate before the private database exists because their source evidence is public. The whole Vercel application still requires the personal credential session.

## Automation

Cakrawala currently uses guardrailed scheduled workflows for:

- daily private Forex Council research;
- daily public AI Research Council research;
- weekly trading-framework, AI-model, and Hugging Face research;
- recurring public source-health checks;
- weekly BTC model backtesting;
- weekly FX foundation-model backtesting;
- external deployment and privacy health monitoring.

The weekly research process reviews TradingAgents, FinRL, Qlib, Chronos-Bolt, TinyTimeMixer, financial NLP models, and newly relevant tools. It verifies license, activity, model size or runtime burden where available, intended use, leakage risk, security risk, and free-runtime fit before updating the radar through a pull request.

Automation cannot install a trading bot directly into production, connect a broker, expose credentials, enable withdrawals, purchase infrastructure, or promote a model automatically.

## CI quality gate

Every code change is expected to pass:

```text
Python compile
Python no-em-dash policy
Streamlit import smoke test
Dash health smoke test
native Vercel WSGI smoke test
deployment wheel build
runtime-resource verification
installed-wheel smoke test
Ruff
pytest
```

The Python no-em-dash policy is enforced automatically. Comments, docstrings, UI strings, and code are written naturally rather than mechanically replacing punctuation.

## Local QA

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m compileall -q src scripts app api main.py
python scripts/check_no_em_dash.py
python -m build --wheel
ruff check .
pytest
```

Run the public Streamlit app locally:

```bash
pip install -e '.[streamlit]'
streamlit run app/streamlit_app.py
```

Run Dash locally after setting the personal authentication environment variables:

```bash
python app/dash_app.py
```

## Limits that stay visible

Cakrawala is decision support, not a guarantee of returns. Public providers can fail, market structure can change, historical relationships can break, model quality can decay, and execution prices can differ materially from reference data.

There is no automatic real-money order execution. AI output cannot override deterministic freshness, model-health, authorization, or risk policy. A compelling AI explanation is still only an explanation until the underlying evidence survives validation.

The project continues to prioritize free services for the portfolio and personal-research stage. If a provider changes its free tier or begins requiring a paid add-on, Cakrawala should fail visibly or use a defensible free alternative rather than silently enabling billing.

BMKG attribution must remain visible wherever BMKG data is displayed.

This product uses the FRED API where configured but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## License

MIT. See `LICENSE`.
