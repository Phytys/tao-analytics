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
| `/` **Landing** | Snapshot of network health + CTA to explorer | 🟢 existing, enhanced error handling | UX / cursor | Light hero, key stats, two CTAs ("Learn" & "Explore") |
| `/about` **What is Bittensor?** | 3-scroll explainer with diagrams | 🟡 placeholder exists | UX → cursor | Collapsible sections, SEO friendly |
| `/dash/explorer` **Subnet Explorer** | Browse + compare subnets | 🟢 ✅ Sprint 1 complete | cursor | Quick Start guide, tooltips, improved UX |
| `/dash/subnet/<netuid>` **Subnet Detail** | Deep dive (metrics, team, TVI) | 🟡 basic structure exists | cursor | Server-side pre-fetch via SDK |
| `/dash/sdk-poc` **SDK Proof of Concept** | Live on-chain data testing | 🟢 ✅ Sprint 3 in progress | cursor | Real-time metrics, emissions, stake analysis |
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
| **2 – Subnet cards v2 (DONE)** | • Add flags: `privacy_security_flag`, confidence bar <br>• Click-thru to detail page stub | ✅ Enhanced card styling with icons <br>✅ Improved "View Details" button <br>✅ Basic subnet detail page structure | ✅ **COMPLETE** |
| **3 – SDK Exploration Spike (IN PROGRESS)** | **Goal:** validate SDK viability in 3 days <br>• Stable RPC list <br>• p95 latency / error rate <br>• mini PoC chart in Dash <br>• Green/Yellow/Red write-up | ✅ Comprehensive SDK integration (`services/bittensor/`) <br>✅ Live metrics calculation (`metrics.py`) <br>✅ SDK PoC dashboard page (`sdk_poc.py`) <br>✅ Multiple RPC endpoints with fallbacks <br>✅ Real-time emission split analysis <br>🔄 Performance testing and validation | 🔄 **IN PROGRESS** |
| **4 – Subnet Detail page (API-only)** | Build on proven tao.app data | cursor | 🔄 **NEXT** |
| **5 – Conditional SDK integration** | Execute **only** if Spike = Green/Yellow | cursor | 🔄 **PLANNED** |
| **6 – TVI / Validator hub** | Data source flexible | cursor | 🔄 **PLANNED** |
| **7 – Analytics dashboard** | Power-user charts | cursor | 🔄 **PLANNED** |
| **8 – Polish & SEO** | Lighthouse, meta, OG | UX / cursor | 🔄 **PLANNED** |

*(Road-map will evolve; we lock only the next two sprints.)*

---

## 3. Data & Infrastructure

### 3.1 Data Pipeline Architecture

#### Primary Data Sources
1. **tao.app API** (`https://api.tao.app/api/beta/subnet_screener`)
   - **Purpose**: Raw subnet data (market cap, volume, URLs)
   - **Authentication**: API key required (`TAO_APP_API_KEY`)
   - **Frequency**: Manual/automated collection via `fetch_screener.py`
   - **Storage**: `screener_raw` table with JSON field

2. **CoinGecko API** (`https://api.coingecko.com/api/v3/`)
   - **Purpose**: TAO price and market cap data
   - **Authentication**: API key required (`COINGECKO_API_KEY`)
   - **Frequency**: Regular updates via `fetch_coingecko_data.py`
   - **Storage**: `coingecko` table

3. **Bittensor SDK** (Live on-chain data)
   - **Purpose**: Real-time subnet metrics and emissions
   - **Endpoints**: Multiple RPC endpoints with fallbacks
   - **Frequency**: Real-time (with 5-minute caching)
   - **Storage**: In-memory cache + real-time calculations

#### AI Enrichment Pipeline
4. **OpenAI GPT-4** (`https://api.openai.com/v1/chat/completions`)
   - **Purpose**: AI-powered subnet classification and description
   - **Model**: GPT-4o (optimal balance of quality and cost)
   - **Features**: 
     - Granular category classification (14 categories)
     - Confidence scoring with provenance tracking
     - Context-aware enrichment from websites/GitHub
     - Tag normalization and deduplication
   - **Storage**: `subnet_meta` table with enriched fields

### 3.2 Database Schema

#### Core Tables
- **`screener_raw`**: Raw API data with JSON field for flexibility
- **`subnet_meta`**: Enriched data with AI-generated classifications
- **`coingecko`**: TAO price and market cap history

#### Key Fields in `subnet_meta`
- `primary_category`: 14 granular categories (LLM-Inference, Serverless-Compute, etc.)
- `confidence`: AI confidence score (0-100) with provenance tracking
- `privacy_security_flag`: Boolean for privacy/security focus
- `context_hash`: MD5 hash for change detection
- `provenance`: JSON tracking of data sources (context vs model knowledge)

### 3.3 SDK usage
| Task | Detail |
|------|--------|
| Connection helper | `SubtensorClient(endpoint=BT.MAIN_RPC, netuid=0)` |
| Cached metagraph | `redis.setex(f"mg:{netuid}", ttl=900, mg.serialize())` |
| Historical blocks | Use `sub.block_at(height)` for point-in-time data |
| Data strategy | *Spike first:* evaluate SDK (S-3). Only integrate if Green/Yellow. Otherwise remain API-first. |

### 3.4 Enrichment pipeline
1. **Crawler** (GitHub README + website)  
2. **LLM classification** (already in place)  
3. **Store** in `subnet_meta` table (Postgres) with `context_hash`, `updated_at`.  
4. **Manual enrichment** for now, automated diff job later.

### 3.5 TVI (Validator Intelligence)
- **Purpose**: Show best validators to stake to
- **Data sources**: SDK metagraph + enriched subnet data
- **Scoring factors**: Stake, uptime, subnet performance, validator reputation
- **Page**: `/dash/tvi` - dedicated validator ranking page

### 3.6 Deployment
| Environment | Python | Notes |
|-------------|--------|-------|
| **Local / M1** | 3.11 + wheels | Using pre-built `grpcio` |
| **Heroku** | 3.10.14 | `apt-buildpack` not needed; pin wheels |
| **CI** | GitHub Actions | Run smoke + lint + dash screenshot |

---

## 4. Current Development Status (Sprint 3)

### ✅ Completed in Sprint 3

#### SDK Integration Infrastructure
- **`services/bittensor/`** - Complete SDK integration module
  - `metrics.py` - Comprehensive subnet metrics calculation (328 lines)
  - `endpoints.py` - Network endpoint constants and RPC pool
  - `cache.py` - SDK data caching with 5-minute TTL
  - `probe.py` - Network connectivity testing
  - `debug_*.py` - Various debugging utilities
  - `test_spike.py` - SDK testing and validation

#### Live Metrics Calculation
- **Total Stake Analysis**: Real-time TAO staked per subnet
- **Stake HHI**: Herfindahl-Hirschman Index for concentration (0-10,000)
- **Emission Split Analysis**: Owner/miners/validators distribution
- **Rolling Window Calculations**: 3-block averages for stability
- **Consensus & Trust Scores**: Network health indicators

#### SDK PoC Dashboard
- **`dash_app/pages/sdk_poc.py`** - Live dashboard for subnet 64
- **Interactive Charts**: Gauge charts, pie charts, real-time updates
- **Performance Optimization**: 5-minute caching, ultra-fast PoC mode
- **Error Handling**: Graceful fallbacks and user feedback

#### Error Handling Enhancements
- **Graceful Data Failures**: `data_available` flag in landing page
- **User-Friendly Errors**: Retry buttons and clear messaging
- **Conditional Rendering**: Hide sections when data unavailable
- **Enhanced UI**: Better error states and responsive design

### 🔄 In Progress

#### Performance Testing
- **Latency Analysis**: p95 response times for SDK calls
- **Error Rate Monitoring**: Connection failure tracking
- **Cache Effectiveness**: Hit rates and performance impact
- **Resource Usage**: Memory and CPU consumption

#### SDK Validation
- **Connectivity Testing**: Multiple RPC endpoint reliability
- **Data Accuracy**: Cross-validation with API data
- **Stability Assessment**: Long-running connection tests
- **Fallback Strategy**: API-first with SDK enhancement

### 📊 Data Pipeline Status

#### Current Data Flow
1. **Raw Data**: tao.app API → `screener_raw` table ✅
2. **Price Data**: CoinGecko API → `coingecko` table ✅
3. **AI Enrichment**: Websites/GitHub → GPT-4 → `subnet_meta` table ✅
4. **Live Metrics**: Bittensor SDK → Real-time calculations ✅
5. **Caching**: LRU cache for performance optimization ✅

#### Caching Strategy
- **API Cache**: 1-hour TTL for external API responses
- **Database Cache**: 30-minute TTL for database queries
- **SDK Cache**: 5-minute TTL for Bittensor SDK data
- **Favicon Cache**: Persistent storage with URL mapping

---

## 5. Open questions / next decision gates
1. **Design system** – keep pure Dash Bootstrap styling (confirmed)  
2. **Auth & roles** – will analytics need login tiers? (future)  
3. **TVI formula** – final weightings & data freshness cadence.  
4. **API public?** – expose our enriched dataset as JSON for the community?  
5. **SDK Integration Decision** – Green/Yellow/Red assessment based on Sprint 3 results
6. **Database Migration** – SQLite to PostgreSQL for production scaling

---

## 6. Sprint 3 Completion Summary (In Progress)

**Completed Tasks:**
- ✅ Comprehensive Bittensor SDK integration with live metrics
- ✅ Real-time subnet metrics calculation (stake, emissions, consensus)
- ✅ SDK PoC dashboard with interactive charts
- ✅ Multiple RPC endpoint support with fallbacks
- ✅ Enhanced error handling and user experience
- ✅ Performance optimization with caching strategies
- ✅ Code organization improvements (scripts → services)

**Key Technical Achievements:**
- Live on-chain data collection and analysis
- Rolling window calculations for emission stability
- Database-agnostic JSON field extraction
- Comprehensive caching strategy for performance
- Graceful error handling and user feedback
- Modular architecture for easy extension

**Next Steps for Sprint 3 Completion:**
- Complete performance testing and validation
- Assess SDK reliability and error rates
- Determine Green/Yellow/Red status for full integration
- Document findings and recommendations

---

## 7. Immediate tickets for cursor agent (Sprint 4)

| # | Title | Est | Notes |
|---|-------|-----|-------|
| 1 | Complete SDK performance testing | 4h | Latency analysis, error rate monitoring |
| 2 | Integrate live SDK data into subnet detail page | 6h | Add real-time metrics to existing detail page |
| 3 | Implement SDK fallback strategy | 3h | API-first with SDK enhancement |
| 4 | Add historical metrics and charts | 4h | Time-series data visualization |
| 5 | Optimize caching for production use | 2h | Fine-tune TTL and cache sizes |

---

## 8. Data Pipeline Deep Dive

### Enrichment Quality Metrics
- **Context Token Correlation**: Higher context = higher confidence
- **Provenance Tracking**: Context vs model knowledge ratio
- **Category Accuracy**: Manual validation of AI classifications
- **Tag Quality**: Normalization and deduplication effectiveness

### Performance Benchmarks
- **API Response Times**: tao.app, CoinGecko, OpenAI
- **Database Query Performance**: JSON extraction and joins
- **SDK Latency**: RPC endpoint response times
- **Cache Hit Rates**: LRU cache effectiveness

### Scalability Considerations
- **Database Growth**: SQLite to PostgreSQL migration path
- **API Rate Limits**: Respecting external service limits
- **SDK Connection Pooling**: Managing multiple RPC connections
- **Cache Memory Usage**: Balancing performance vs memory

---

_This document is living – update after each sprint review._  
