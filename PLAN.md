Below is an **updated PLAN.md (v0.3-draft)** that folds in every new requirement and the specialist-review improvements.
Hand this block verbatim to the cursor agent (or paste into `PLAN.md`) and commit as “bump PLAN.md → v0.3”.

```markdown
# TAO-Analytics – Master Plan (v0.3 draft)
> Updated 2025-06-22 by ChatGPT after specialist QA review  
> **Legend** P0 = critical • P1 = high • P2 = nice-to-have

---

## 0 · Snapshot
| Item | Status |
|------|--------|
| Subnets in DB | **124** raw • **94** enriched |
| Categories    | **12** live (0 “Other”) |
| Mean confidence | **91.2** |
| Dashboard     | Explorer + System Info (auth) |
| Deployment    | Heroku Procfile committed – Postgres-ready |

---

## 1 · Newly Completed (v0.2)
* Admin auth system + System-Info page  
* Landing → Tesla UI, nav hides admin links when logged-out  
* Cache/stat service & session security  
* README / structure fully documented

---

## 2 · **Immediate Backlog (v0.3)**

### **P0 · Data Coverage & DB Portability**
1. **Auto-fallback enrichment (`--fallback`)**  
   *Enrich the 30 empty rows using model-only prompt →*  
   `primary_category : "Unknown – Needs manual research"`  
   `confidence : 5` • `provenance : "model-only-empty"`
2. **DB JSON helper** `services/db_utils.json_field(col,key)`  
   *SQLite* → `func.json_extract(col, '$.'||key)`  
   *Postgres* → `col.op('->>')(key)`  
   Replace all raw `json_extract` usage.

### **P0 · Context Quality Boost**
3. **Raise MIN_CONTEXT_TOKENS → 100** in `config.py`
4. **prepare_context.py**  
   * increase web truncation to 3 000 chars  
   * prioritise `<h1>/<h2>` and README sections **About / Features** before truncation

### **P0 · Prompt Upgrade**
5. **prompt/enrich_template.txt**  
   * Add a 1-line “Bittensor cheat-sheet” in system message  
   * Insert **2 few-shot examples** (good categorisation)  
   * Retain JSON-only response rule.

---

### **P1 · Dashboard Polish & Scoring**

6. **LRU TTL cache (10 s)** around `services.db.load_subnet_frame`
7. **Card ribbons & icons**  
   * top-border colour: ≥90 green / 50-89 amber / <50 red  
   * provenance emoji prefix: 📝 context • 🧠 model • 🔒 privacy flag
8. **Landing-page KPIs** via `Flask-Caching` SimpleCache(60 s)
9. **Extended taxonomy** in `config.PRIMARY_CATEGORIES`
```

* split Dev-Tooling → SDKs / Dashboards / Validators
* add Cross-Chain & Social
* sub-modalities noted in docstring (LLM-Inference/Text ...)

```
10. **Composite quality score** in `enrich_with_openai.py`  
 `quality = orig_conf × source_weight × token_weight`  
 *source_weight*: GitHub 1.0 > Web 0.9 > Wayback 0.8 > Model 0.5

### **P1 · Enhanced System-Info**
11. Add request-latency & error-rate graphs  
12. Data-export button (CSV of current filter)  
13. Enrichment trend chart (daily accuracy vs gold-set)

---

### **P2 · QA & UX**

14. **Gold-set framework** (`scripts/build_gold_set.py`, `validate_against_gold.py`)  
 * 50 manually labelled rows → accuracy report
15. **Re-ask loop**: if `confidence < 70` queue row in `subnet_review_queue`
16. **Quick-filter chips** (Privacy, Trading) via `dbc.Checklist`
17. **Lazy favicon fetcher** `/favicon/<netuid>.ico` → returns placeholder then async fetch
18. Mobile tweaks for admin dashboard

---

## 3 · Implementation Order (safe-merge)

1. `db_utils.json_field` + swap queries  
2. `--fallback` path in `batch_enrich.py` → run once & push DB to 124/124  
3. Config bump (token floor, taxonomy list)  
4. Prompt file update (cheat-sheet + few-shot)  
5. Context extractor upgrade (3 000 chars & header emphasis)  
6. LRU cache decorator  
7. Card ribbons & provenance icons  
8. Landing KPI cache  
9. Composite quality score calc  
10. Docs: README, PLAN.md → v0.3

---

## 4 · Low-Effort Wins (can ship in same PR)

* Add `pip install Flask-Caching` to **requirements.txt**  
* Update landing `<meta description>` + Jinja stats variables  
* Colour map dictionary in `dash_app/assets/custom.css`

---

### ✅ End-of-file – keep this PLAN.md in repo root and bump version tags when items ship.
```

---

If everything looks good, tell the cursor agent:

> **“Replace PLAN.md with the v0.3-draft above, commit as `docs: update PLAN to v0.3-draft`.”**

(Or tweak anything first and let me know.)
