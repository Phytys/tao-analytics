# 📈 **Bittensor Explorer – Road-map (living doc)**

_Last update_: 2025-07-01  
_Owners_:  
- **Product / UX** – ChatGPT (o3)  
- **Engineering (cursor agent)** – `cursor/`  
- **Project manager** – Gizmo  

---

## 0. Guiding principles
1. **Hook Bitcoiners** – assume they know BTC & PoW, are AI-curious, want signal not hype.  
2. **Show what nobody else shows** – blend on-chain SDK data, tao.app flow & GPT-4o narrative.  
3. **Progressive disclosure** – quick wins first, depth on demand.  
4. **Ship small, ship beta** – two-dev bandwidth, free-tier quotas.  
5. **Hard-cap TAO.app at 1 000 calls / month** – track per endpoint, abort gracefully.  

---

## 1. Page architecture & **beta-content blueprint**

| Page & Route | **What the user will actually see in beta** | Tech notes | Status |
|--------------|---------------------------------------------|------------|--------|
| **Landing** `/` | • Hero headline + 1-liner value prop<br>• Live TAO price & 24 h Δ (CoinGecko, cached 60 min)<br>• Network health chip (Root stake % vs Subnets live)<br>• Two CTAs **Learn** → /About, **Explore** → /Explorer | price → `services/coingecko.py` | 🟢 ready |
| **About** `/about` | 3 collapsible FAQ sections + SVG diagram:<br>1. _"What is Bittensor?"_ (PoW → PoI)<br>2. _"Why Bitcoiners care"_<br>3. _"How this site works (SDK + tao.app + GPT-4o)"_ | static HTML, no external calls | 🟡 copy todo |
| **Subnet Explorer** `/dash/explorer` | • Card/Table of 128 subnets (tao.app screener blob)<br>• Filters: Category ▾, Search, Price range slider<br>• Flags: _privacy/security_, confidence bar<br>• Collapsible Quick-start accordion | data = nightly screener JSON | 🟢 ready |
| **Subnet Detail** `/dash/subnet/<netuid>` | _Investor console_<br>**Metrics panel** (live or cached ≤ 24 h):<br>• Total stake TAO + HHI + **Stake Quality score**<br>• **Reserve Momentum** Δ 24 h (tao.app /aggregated)<br>• **Emission ROI** = Alpha APY vs TAO yield<br>• Alpha & TAO price Δ 24 h / 7 d (CoinGecko, cached)<br>• Holder concentration ⓘ (lazy /holders call, on click)<br>• Mini **TVI widget** → top-3 validators (placeholder until /tvi)<br>**GPT-4o insight** – 120-word summary (JSON metrics ⇒ prompt, cached 1 h)<br>Tabs: Overview | Holders | Validators | Docs | pulls 1 tao.app endpoint + SDK for stake | 🔄 in Sprint 5 |
| **Analytics Screener** `/dash/analytics` | • Heat-map: _(Alpha 7 d Δ − TAO 7 d Δ)_ per subnet<br>• "Top-5 upside" table: _Reserve Momentum × Stake Quality_ rank<br>• Stake-rotation chart: Root ↔ Subnets % (nightly snapshot)<br>• Filters: Category, MCap, Age slider | all from nightly `metrics_snap` | 🔄 Sprint 6 |
| **Validator Hub** `/dash/tvi` | Post-beta (TVI composite ranking) | depends on uptime scrape | 🔴 backlog |
| **System-info** `/dash/system-info` | Hidden admin view | auth required | 🟢 |
| **SDK-poc** `/dash/sdk-poc` | **DEV-only** – latency gauges & live charts | not linked in nav, prod-hidden | 🟢 |

_User flow_   `Landing → Explorer → Subnet Detail → Analytics (+ TVI later)`  

---

## 2. Beta launch checklist (🎯 target 2025-07-15)

### Must-have
- [ ] **About page copy & SVG diagram**
- [ ] **Subnet Detail v1** (metrics panel + GPT-4o brief)
- [ ] **Analytics Screener v1** (heat-map, upside table, rotation chart)
- [ ] **Nightly `cron_fetch.py`** – 3 tao.app calls + 128 SDK head-block calls
- [ ] **`quota_guard.py`** – persist monthly counts, raise `QuotaExceededError`
- [ ] **SQLite table `metrics_snap`** (+ simple index)

### Nice-to-have
- [ ] "Download CSV" on Holders tab
- [ ] Mobile tweak – Explorer card wrap
- [ ] Dark-mode toggle (CSS var switch)

---

## 3. Sprint timeline (≈ 1 week each)

| Sprint | Theme | Key deliverables |
|--------|-------|------------------|
| **3 ✅** | SDK Spike | PoC page, latency numbers |
| **4 ▶** | **Data Pipeline MVP** | `cron_fetch.py`, `quota_guard.py`, `metrics_snap` |
| **5** | **Subnet Detail v1** | Metrics panel, GPT-4o brief, lazy holders |
| **6** | **Analytics Screener v1** | Heat-map, upside table, rotation chart |
| **7** | **Beta polish + deploy** | About copy, mobile tweaks, Heroku Procfile test |
| **8** | TVI / Validator hub | post-beta |

---

## 4. Data & infrastructure snapshot

| Layer | Source | Cadence | Quota notes |
|-------|--------|---------|-------------|
| **Prices** | CoinGecko (TAO/BTC) | hourly cache | free-tier; soft-monitor |
| **Subnet screener** | `/subnet_screener` | **nightly** (1 call) | part of 3/month |
| **Macro root flows** | `/analytics/macro/aggregated` | nightly (1 call) | part of 3/month |
| **Per-subnet aggregates** | `/analytics/subnets/aggregated?netuid=X` | on click (24 h cache) | tracked per-netuid |
| **Holders** | `/analytics/subnets/holders?netuid=X` | lazy; only when "Holders" tab opened (24 h cache) | tracked per-netuid |
| **SDK head metrics** | `bt.subtensor.metagraph(netuid)` | nightly loop 128 nets | local RPC, no quota |
| **GPT-4o** | `services/gpt_insight.py` | on Subnet Detail; 120-word summary, cached 1 h | cost capped in OpenAI dashboard |

**Quota enforcement** (`quota_guard.py`)  
```txt
if calls_this_month(endpoint) >= ENDPOINT_LIMIT:
    raise QuotaExceededError
else:
    increment_counter(endpoint)

TAO.app global cap = 1 000/month.
```

**Error handling for quota exceeded:**
```python
try: 
    data = fetch_or_cache(...)
except QuotaExceededError:
    if cache.exists(key):
        flash('Fresh data unavailable – showing last cached snapshot.', 'warning')
        data = cache.get(key)
    else:
        return dbc.Alert('Data temporarily unavailable, try again tomorrow', color='danger')
```

---

## 5. Immediate tickets (Sprint 4)

| # | Task | Est | Owner |
|---|------|-----|-------|
| 4-0 | `quota_guard.py` – SQLite table `api_quota` (id, month, count) + `--report` CLI flag | 2 h | cursor |
| 4-1 | `cron_fetch.py` skeleton + unit test (mock responses) + `fetch_prices()` helper | 4 h | cursor |
| 4-2 | `metrics_snap` schema (timestamp, netuid, stake_tao, reserve_mom, …) | 2 h | cursor |
| 4-3 | Wire nightly tao.app calls via quota guard | 3 h | cursor |
| 4-4 | SDK 128-net snapshot + CSV dump (optional) | 3 h | cursor |
| 4-5 | `services/gpt_insight.py` (wrap existing OpenAI util) | 2 h | cursor |
| 4-6 | Add Heroku Scheduler & GH Action (nightly) | 1 h | cursor |

**Dev-first**: run `cron_fetch.py` manually (`python scripts/cron_fetch.py --once`) during local testing.  
**Prod-ready**: same script invoked by Heroku Scheduler hourly; ensure no binaries or build-packs beyond `grpcio` wheels.

---

## 6. Design decisions (locked after feedback)

- **Hybrid cadence** – hourly CoinGecko, nightly tao.app + SDK, plus on-demand per-subnet.
- **Schema additive** – keep `screener_raw` / `subnet_meta` / `coingecko`; append `metrics_snap`. No migration needed.
- **SDK** – keep `/sdk-poc` for dev; nightly SDK loop for production metrics. Hide from production navigation.
- **Quota guard** – hard-fail with user-friendly message; log to `api_quota` table. Graceful fallback to cached data.
- **CoinGecko integration** – integrate into `cron_fetch.py` as `fetch_prices()` helper, runs every invocation.
- **SDK PoC visibility** – keep route `/dash/sdk-poc` for dev debugging, wrap registration in `if app.config['ENV'] != 'production'`.
- **SQLite → Postgres** – migrate only when `metrics_snap` > 1 M rows.
- **Deployment sanity** – nothing that breaks `gunicorn app:create_app()`, no OS-level deps.
- **Baseline analysis** – add `--report` flag to `quota_guard.py` to scan existing dev logs and establish pre-quota usage numbers.

---

_This roadmap auto-updates after each sprint review._  
_Next review: end of Sprint 4 (2025-07-07)._ 