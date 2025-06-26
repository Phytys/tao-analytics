# 📈 Bittensor Explorer – Road-map (living doc)

_Last update_: 2025-01-27  
_Owners_:  
- **Product / UX** – ChatGPT (o3)  
- **Engineering (cursor agent)** – `cursor/`  
- **Project manager** – Gizmo  

---

## 0. Guiding principles
1. **Hook Bitcoiners** – assume they know BTC & PoW, are AI-curious, want signal not hype.  
2. **Show what nobody else shows** – combine on-chain SDK data + LLM enrichment = unique lens.  
3. **Progressive disclosure** – quick wins first, depth on demand.  
4. **Own the data pipeline** – supplement tao.app screener with SDK data for enhanced insights.

---

## 1. High-level page architecture

| Page | Purpose | Status | Owner | Notes |
|------|---------|--------|-------|-------|
| `/` **Landing** | Snapshot of network health + CTA to explorer | 🟢 existing, needs polish | UX / cursor | Light hero, key stats, two CTAs ("Learn" & "Explore") |
| `/about` **What is Bittensor?** | 3-scroll explainer with diagrams | 🟡 placeholder exists | UX → cursor | Collapsible sections, SEO friendly |
| `/dash/explorer` **Subnet Explorer** | Browse + compare subnets | 🟢 ✅ Sprint 1 complete | cursor | Quick Start guide, tooltips, improved UX |
| `/dash/subnet/<netuid>` **Subnet Detail** | Deep dive (metrics, team, TVI) | 🔴 new | cursor | Server-side pre-fetch via SDK |
| `/dash/tvi` **Validator Intelligence** | Best validators to stake to | 🔴 new | cursor | TVI scoring, validator rankings |
| `/dash/analytics` **Network Analytics** | Macro charts, category growth | 🟡 planned | cursor | Power-user tab |
| `/dash/system-info` | Dev tools (already hidden) | 🟢 | cursor | N/A |

### UX Flow
```
Landing → Explorer → Subnet Detail → Validator List / TVI
   ↓         ↓           ↓              ↓
About    Quick Start   Deep Dive    Stake Guide
```

---

## 2. Feature roadmap (by sprint – locked next 2)

> **Each sprint ≈ 1 week**.  ✅ = quick win, 🔄 = iterative, 🛠 = infra/data

| Sprint | Theme / Goals | Key tasks | Status |
|-------|---------------|-----------|--------|
| **0 – Hardening (DONE)** | • SDK connectivity (finney = main-net) <br>• Enrichment crawl | ✅ Pin `bittensor==9.7.*` w/ `grpcio` wheels <br>✅ `bt_endpoints.py` constants <br>✅ `sdk_smoketest.py` & logs | ✅ **COMPLETE** |
| **1 – UX Quick Wins (DONE)** | • Lightweight onboarding in Explorer <br>• Tool-tips & hover defs | ✅ Collapsible "Quick Start Guide" box <br>✅ Metric tool-tips for market cap, category, confidence <br>✅ About page navigation <br>✅ Category dropdown cleanup | ✅ **COMPLETE** |
| **2 – Subnet cards v2** | • Add flags: `privacy_security_flag`, confidence bar <br>• Click-thru to detail page stub | cursor: extend card component <br>UX: style guidelines | 🔄 **NEXT** |
| **3 – SDK Exploration Spike** | **Goal:** validate SDK viability in 3 days <br>• Stable RPC list <br>• p95 latency / error rate <br>• mini PoC chart in Dash <br>• Green/Yellow/Red write-up | 🛠 spike | 🔄 **PLANNED** |
| **4 – Subnet Detail page (API-only)** | Build on proven tao.app data | cursor | 🔄 **PLANNED** |
| **5 – Conditional SDK integration** | Execute **only** if Spike = Green/Yellow | cursor | 🔄 **PLANNED** |
| **6 – TVI / Validator hub** | Data source flexible | cursor | 🔄 **PLANNED** |
| **7 – Analytics dashboard** | Power-user charts | cursor | 🔄 **PLANNED** |
| **8 – Polish & SEO** | Lighthouse, meta, OG | UX / cursor | 🔄 **PLANNED** |

*(Road-map will evolve; we lock only the next two sprints.)*

---

## 3. Data & Infrastructure

### 3.1 SDK usage
| Task | Detail |
|------|--------|
| Connection helper | `SubtensorClient(endpoint=BT.MAIN_RPC, netuid=0)` |
| Cached metagraph | `redis.setex(f"mg:{netuid}", ttl=900, mg.serialize())` |
| Historical blocks | Use `sub.block_at(height)` for point-in-time data |
| Data strategy | *Spike first:* evaluate SDK (S-3). Only integrate if Green/Yellow. Otherwise remain API-first. |

### 3.2 Enrichment pipeline
1. **Crawler** (GitHub README + website)  
2. **LLM classification** (already in place)  
3. **Store** in `subnet_meta` table (Postgres) with `context_hash`, `updated_at`.  
4. **Manual enrichment** for now, automated diff job later.

### 3.3 TVI (Validator Intelligence)
- **Purpose**: Show best validators to stake to
- **Data sources**: SDK metagraph + enriched subnet data
- **Scoring factors**: Stake, uptime, subnet performance, validator reputation
- **Page**: `/dash/tvi` - dedicated validator ranking page

### 3.4 Deployment
| Environment | Python | Notes |
|-------------|--------|-------|
| **Local / M1** | 3.11 + wheels | Using pre-built `grpcio` |
| **Heroku** | 3.10.14 | `apt-buildpack` not needed; pin wheels |
| **CI** | GitHub Actions | Run smoke + lint + dash screenshot |

---

## 4. Open questions / next decision gates
1. **Design system** – keep pure Dash Bootstrap styling (confirmed)  
2. **Auth & roles** – will analytics need login tiers? (future)  
3. **TVI formula** – final weightings & data freshness cadence.  
4. **API public?** – expose our enriched dataset as JSON for the community?  

---

## 5. Sprint 1 Completion Summary ✅

**Completed Tasks:**
- ✅ Added collapsible "Quick Start Guide" to `/dash/explorer` with onboarding help
- ✅ Added tooltips for market cap (TAO/USD), category, and confidence metrics
- ✅ Implemented confidence score as small badge next to subnet names
- ✅ Cleaned up category dropdown and improved UX
- ✅ Fixed About page navigation from landing page
- ✅ Updated README.md with accurate project structure
- ✅ All features tested and confirmed working

**Key Improvements:**
- Users now have clear onboarding guidance
- Tooltips provide context for complex metrics
- Visual confidence indicators improve scanability
- About page accessible from main navigation
- Documentation accurately reflects current codebase

---

## 6. Immediate tickets for cursor agent (Sprint 2)

| # | Title | Est | Notes |
|---|-------|-----|-------|
| 1 | Add privacy/security flags to subnet cards | 2h | Extend card component with flag indicators |
| 2 | Implement click-thru to subnet detail page stub | 3h | Create basic detail page with routing |
| 3 | Add confidence bar visualization | 1h | Replace badge with progress bar |
| 4 | Style guidelines for new card elements | 1h | Ensure consistency with existing design |

---

_This document is living – update after each sprint review._  
