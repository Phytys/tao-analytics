import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback, callback_context, clientside_callback
import plotly.express as px
import plotly.graph_objects as go
from services.db import load_subnet_frame
from services.favicons import favicon_service
from services.cache import cache_stats
import pandas as pd, datetime as dt, json, os
from io import StringIO
from models import CoinGeckoPrice

CATS = ["All"] + sorted(
    load_subnet_frame()["primary_category"].dropna().unique().tolist()
)

# Category descriptions for tooltips
CATEGORY_DESCRIPTIONS = {
    "LLM-Inference": "AI text generation and language model services",
    "LLM-Training / Fine-tune": "Training and fine-tuning large language models",
    "Data-Feeds & Oracles": "Real-time data feeds and blockchain oracles",
    "Serverless-Compute": "GPU computing power and model deployment",
    "AI-Verification & Trust": "AI verification, zero-knowledge proofs, and trust systems",
    "Confidential-Compute": "Secure and private AI execution",
    "Hashrate-Mining (BTC / PoW)": "Bitcoin mining and proof-of-work services",
    "Finance-Trading & Forecasting": "Financial trading and prediction services",
    "Security & Auditing": "Security analysis and auditing services",
    "Privacy / Anonymity": "Privacy-focused AI and anonymity services",
    "Media-Vision / 3-D": "Computer vision, 3D modeling, and media AI",
    "Science-Research (Non-financial)": "Scientific research and non-financial AI",
    "Consumer-AI & Games": "Consumer AI applications and gaming",
    "Dev-Tooling": "Developer tools, SDKs, and validator utilities"
}

# Category color mapping for consistent colors
CATEGORY_COLORS = {
    "LLM-Inference": "#1f77b4",
    "LLM-Training / Fine-tune": "#ff7f0e", 
    "Data-Feeds & Oracles": "#2ca02c",
    "Serverless-Compute": "#d62728",
    "Hashrate-Mining (BTC / PoW)": "#9467bd",
    "Finance-Trading & Forecasting": "#8c564b",
    "Security & Auditing": "#e377c2",
    "Privacy / Anonymity": "#7f7f7f",
    "Media-Vision / 3-D": "#bcbd22",
    "Science-Research (Non-financial)": "#17becf",
    "Consumer-AI & Games": "#ff9896",
    "Dev-Tooling": "#98df8a"
}

# Confidence ribbon colors
CONFIDENCE_COLORS = {
    'high': '#28a745',      # Green for 90-100
    'medium': '#ffc107',    # Yellow for 70-89
    'low': '#dc3545'        # Red for 0-69
}

# Remove static TAO price cache - will be queried dynamically in callbacks

def get_confidence_color(score):
    """Get confidence ribbon color based on score."""
    if score >= 90:
        return CONFIDENCE_COLORS['high']
    elif score >= 70:
        return CONFIDENCE_COLORS['medium']
    else:
        return CONFIDENCE_COLORS['low']

layout = dbc.Container(
    [
        # --- Tesla-inspired header ---
        html.Div([
            html.H1("Bittensor Subnet Explorer", className="dashboard-title"),
            html.A(
                "Test Subnet Detail Page", 
                href="/dash/subnet-detail", 
                className="btn btn-outline-secondary btn-sm mt-2"
            )
        ], className="dashboard-header"),
        
        # --- Quick Start section (collapsible) ---
        html.Div([
            dbc.Button(
                [
                    html.I(className="bi bi-question-circle me-2"),
                    "Quick Start Guide",
                    html.I(className="bi bi-chevron-down ms-2", id="quick-start-icon")
                ],
                id="quick-start-toggle",
                color="outline-primary",
                className="mb-3",
                n_clicks=0
            ),
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("🎯 How to Use This Explorer", className="mb-3"),
                        html.Div([
                            html.Div([
                                html.H6("📊 Browse by Category", className="text-primary"),
                                html.P("Click categories to see similar AI services. Each category represents a different type of AI task or service.")
                            ], className="mb-3"),
                            html.Div([
                                html.H6("💰 Understanding Market Cap", className="text-primary"),
                                html.P("Market Capitalisation (MC) = token price × circulating supply. Shows what the network is worth right now, based on the number of tokens actually tradeable today. MC grows as new tokens are emitted, even if price is flat.")
                            ], className="mb-3"),
                            html.Div([
                                html.H6("🎯 Confidence Score (AI classification and description)", className="text-primary"),
                                html.P("Green = reliable data from website/GitHub, Yellow = mixed sources, Red = limited information available.")
                            ], className="mb-3"),
                            html.Div([
                                html.H6("🔍 Search & Filter", className="text-primary"),
                                html.P("Use the search box to find specific subnets by name, tags, or features. Filter by category to focus on specific AI services.")
                            ], className="mb-3"),
                            html.Hr(),
                            html.Div([
                                html.H6("🏷️ Category Guide", className="text-primary mb-2"),
                                html.Div([
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("LLM-Inference: ", className="fw-bold text-info"),
                                    html.Span("Text/chat model serving (e.g. Apex, Targon, Nineteen.ai)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("LLM-Training / Fine-tune: ", className="fw-bold text-info"),
                                    html.Span("Collaborative training or fine-tuning of models (e.g. Templar, OpenKaito, Gradients)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Data-Feeds & Oracles: ", className="fw-bold text-info"),
                                    html.Span("Real-time data acquisition or indexing (e.g. Data Universe, Desearch)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Serverless-Compute: ", className="fw-bold text-info"),
                                    html.Span("Raw GPU compute you can rent (e.g. SubVortex, Compute Horde, Storb)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("AI-Verification & Trust: ", className="fw-bold text-info"),
                                    html.Span("Model authenticity, ZK proofs, trust (e.g. Omron, ItsAI, FakeNews)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Confidential-Compute: ", className="fw-bold text-info"),
                                    html.Span("Secure/private AI execution (no current subnets listed)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Hashrate-Mining (BTC / PoW): ", className="fw-bold text-info"),
                                    html.Span("Pools redirecting external PoW hashrate (e.g. TAOHash, HashTensor)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Finance-Trading & Forecasting: ", className="fw-bold text-info"),
                                    html.Span("Quant, trading bots, on-chain signal (e.g. Infinite Games, Sturdy, CANDLES)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Security & Auditing: ", className="fw-bold text-info"),
                                    html.Span("Fake-news detection, code audit, threat intel (e.g. Yanez MIID, Bitsec.ai)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Privacy / Anonymity: ", className="fw-bold text-info"),
                                    html.Span("Privacy-focused AI, anonymity (e.g. TAO Private Network, taonado)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Media-Vision / 3-D: ", className="fw-bold text-info"),
                                    html.Span("Image, video, or 3-D generation/analysis (e.g. 404GEN, Nuance, Score)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Science-Research (Non-financial): ", className="fw-bold text-info"),
                                    html.Span("Protein folding, climate models, open science (e.g. Zeus, Mainframe, Gaia)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Consumer-AI & Games: ", className="fw-bold text-info"),
                                    html.Span("End-user apps, chat-RP, gaming, companions (e.g. Dippy, OMEGA Labs)"),
                                    html.Br(),
                                    html.Span("• ", className="fw-bold"),
                                    html.Span("Dev-Tooling: ", className="fw-bold text-info"),
                                    html.Span("SDKs, dashboards, validator tools (e.g. SWE - Rizzo, Ridges AI)")
                                ], className="small")
                            ])
                        ])
                    ]),
                    className="border-primary"
                ),
                id="quick-start-collapse",
                is_open=False
            )
        ], className="mb-4"),
        
        # --- filter controls ---
        html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id="cat-drop",
                        options=[{"label": "All categories", "value": "All"}] + [
                            {
                                "label": c, 
                                "value": c
                            } for c in CATS if c != "All"
                        ],
                        value="All",
                        clearable=False,
                        style={"width": "100%"}
                    ),
                ], xs=12, md=6, className="filter-col"),
                dbc.Col([
                    dcc.Input(
                        id="search-box",
                        type="text",
                        placeholder="Search subnets (name, tag, etc)",
                        debounce=True,
                        className="form-control"
                    ),
                    html.Div(id="refresh-stamp", className="text-muted minimal-last-updated"),
                ], xs=12, md=6, className="filter-col"),
            ], className="g-1 g-md-2"),
        ], className="filter-controls compact-filter-controls"),
        
        # --- KPI strip ---
        html.Div(id="kpi-strip", className="mb-4 compact-kpi-strip"),
        
        # --- minimalist chart toggle and chart ---
        html.Div([
            html.Div(
                dbc.ButtonGroup([
                    dbc.Button(
                        [
                            html.I(className="bi bi-pie-chart-fill me-1"),
                            "Subnets"
                        ],
                        id="btn-chart-count",
                        color="primary",
                        outline=False,  # Will be set dynamically
                        active=True,
                        n_clicks=0,
                        className="chart-toggle-btn"
                    ),
                    dbc.Button(
                        [
                            html.I(className="bi bi-bar-chart-fill me-1"),
                            "Market Cap"
                        ],
                        id="btn-chart-mcap",
                        color="primary",
                        outline=True,  # Will be set dynamically
                        active=False,
                        n_clicks=0,
                        className="chart-toggle-btn"
                    ),
                ], size="sm", className="chart-toggle-group justify-content-center mb-2", id="chart-toggle-group"),
                className="d-flex justify-content-center"
            ),
            html.Div(id="chart-fig", className="chart-container"),
        ], id="chart-section"),
        
        # --- card grid ---
        html.Div(id="card-grid", className="row g-4"),
        dcc.Store(id="cache-df"),
        dcc.Store(id="chart-mode-store", data="mcap"),
        dcc.Store(id="screen-size-store", data="large"),
    ],
    fluid=True,
    className="px-4"
)

@callback(
    Output("cache-df", "data"),
    Output("refresh-stamp", "children"),
    Input("cat-drop", "value"),
    Input("search-box", "value"),
)
def refresh_df(cat, search):
    df = load_subnet_frame(cat, search or "")
    stamp = f"Last updated: {dt.datetime.utcnow().strftime('%H:%M:%S')} UTC"
    return df.to_json(date_unit="s", orient="split"), stamp

@callback(
    Output("quick-start-collapse", "is_open"),
    Output("quick-start-icon", "className"),
    Input("quick-start-toggle", "n_clicks"),
    State("quick-start-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_quick_start(n_clicks, is_open):
    if n_clicks:
        if is_open:
            return False, "bi bi-chevron-down ms-2"
        else:
            return True, "bi bi-chevron-up ms-2"
    return is_open, "bi bi-chevron-down ms-2"

@callback(
    Output("kpi-strip", "children"),
    Input("cache-df", "data"),
)
def render_kpis(json_df):
    if not json_df:
        return html.Div("No data available")
    
    df = pd.read_json(StringIO(json_df), orient="split")
    total = len(df)
    cats = df["primary_category"].nunique()
    
    # Only show essential badges that respond to filters/search
    badges = [
        html.Span(f"📊 {total} Subnets", className="kpi-badge"),
        html.Span(f"🏷️ {cats} Categories", className="kpi-badge"),
    ]
    
    # Add a helpful message if filters are applied
    if total < 125:  # Assuming 125 is the total number of subnets
        badges.append(
            html.Span(f"🔍 Filtered results", className="kpi-badge kpi-filtered")
        )
    
    return html.Div(badges)

@callback(
    Output("chart-mode-store", "data"),
    Output("btn-chart-count", "active"),
    Output("btn-chart-mcap", "active"),
    Output("btn-chart-count", "outline"),
    Output("btn-chart-mcap", "outline"),
    Input("btn-chart-count", "n_clicks"),
    Input("btn-chart-mcap", "n_clicks"),
)
def toggle_chart_mode(n_count, n_mcap):
    ctx = callback_context
    if not ctx.triggered:
        # Default: Market Cap is active
        return "mcap", False, True, True, False
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn_id == "btn-chart-mcap":
        return "mcap", False, True, True, False
    return "count", True, False, False, True

@callback(
    Output("chart-fig", "children"),
    Input("cache-df", "data"),
    Input("chart-mode-store", "data"),
    Input("screen-size-store", "data"),
)
def render_chart(json_df, mode, screen_size):
    if not json_df:
        print("DEBUG: No JSON data available for charts")
        return html.Div("No data available", style={"textAlign": "center", "padding": "2rem"})
    
    try:
        df = pd.read_json(StringIO(json_df), orient="split")
        print(f"DEBUG: Loaded {len(df)} rows for chart, mode: {mode}, screen: {screen_size}")
        showlegend = screen_size == "large"
        
        if mode == "count":
            count_data = df.groupby("primary_category").size().reset_index()
            count_data.columns = ["primary_category", "count"]
            print(f"DEBUG: Pie chart data - {len(count_data)} categories")
            fig = px.pie(
                count_data,
                names="primary_category",
                values="count",
                title="Subnets per Category",
                color_discrete_map=CATEGORY_COLORS
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=50, b=20),
                height=350,
                showlegend=showlegend,
                autosize=True,
                font=dict(size=12),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Inter"
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>Subnets: %{value}<br>Percentage: %{percent}<extra></extra>"
            )
            
        elif mode == "mcap":
            mcap_data = df.groupby("primary_category")["mcap_tao"].sum().reset_index()
            print(f"DEBUG: Bar chart data - {len(mcap_data)} categories")
            fig = px.bar(
                mcap_data,
                x="primary_category",
                y="mcap_tao",
                title="Total Market-cap (TAO) by Category",
                color="primary_category",
                color_discrete_map=CATEGORY_COLORS
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=50, b=20),
                height=350,
                showlegend=False,
                autosize=True,
                font=dict(size=12),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Inter"
                )
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Market Cap: %{y:,.0f} TAO<extra></extra>"
            )
            
        else:
            # Fallback to pie chart
            count_data = df.groupby("primary_category").size().reset_index()
            count_data.columns = ["primary_category", "count"]
            fig = px.pie(
                count_data,
                names="primary_category",
                values="count",
                title="Subnets per Category",
                color_discrete_map=CATEGORY_COLORS
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=50, b=20),
                height=350,
                showlegend=showlegend,
                autosize=True,
                font=dict(size=12),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Inter"
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>Subnets: %{value}<br>Percentage: %{percent}<extra></extra>"
            )
        
        print("DEBUG: Chart created successfully")
        return dcc.Graph(
            figure=fig, 
            config={
                'displayModeBar': False,
                'responsive': True,
                'displaylogo': False
            }
        )
        
    except Exception as e:
        print(f"DEBUG: Error creating chart: {e}")
        return html.Div(f"Error loading chart: {str(e)}", style={"textAlign": "center", "padding": "2rem", "color": "red"})

@callback(
    Output("card-grid", "children"),
    Input("cache-df", "data"),
)
def render_cards(json_df):
    if not json_df:
        return html.Div("No data available")
    
    df = pd.read_json(StringIO(json_df), orient="split").sort_values("mcap_tao", ascending=False)
    
    # Get latest TAO price from database for USD conversions
    from services.db import get_db
    from models import CoinGeckoPrice
    with get_db() as session:
        tao_price_row = session.query(CoinGeckoPrice).order_by(CoinGeckoPrice.fetched_at.desc()).first()
        tao_price_usd = tao_price_row.price_usd if tao_price_row else 0
    
    def format_url(url):
        """Format URL to ensure it has proper protocol and is valid."""
        if pd.isna(url) or not url or url.strip() == "":
            return None
        
        url = url.strip()
        
        # If it already has a protocol, return as is
        if url.startswith(('http://', 'https://')):
            return url
        
        # If it's just a domain, add https://
        if '.' in url and not url.startswith('/'):
            return f"https://{url}"
        
        # If it's a relative path, skip it
        return None
    
    def format_provenance(provenance_str):
        """Format provenance data for display."""
        if pd.isna(provenance_str) or not provenance_str:
            return None
        
        try:
            import json
            provenance_data = json.loads(provenance_str)
            context_fields = sum(1 for v in provenance_data.values() if v == 'context')
            model_fields = sum(1 for v in provenance_data.values() if v == 'model')
            total_fields = len(provenance_data)
            
            if context_fields == total_fields:
                return "📄 AI analyzed website/GitHub data"
            elif model_fields == total_fields:
                return "🤖 AI used prior knowledge"
            elif context_fields > model_fields:
                return f"📄 AI mostly used website/GitHub data"
            else:
                return f"🤖 AI mostly used prior knowledge"
        except:
            return "📊 Data source available"
    
    def make_card(row):
        # Handle secondary_tags as comma-separated string
        if pd.isna(row.secondary_tags) or not row.secondary_tags:
            tags = []
        else:
            tags = [tag.strip() for tag in str(row.secondary_tags).split(',') if tag.strip()]
        
        # Format market cap
        mcap = row.mcap_tao
        if mcap >= 1000000:
            mcap_str = f"{mcap/1000000:.1f}M TAO"
        elif mcap >= 1000:
            mcap_str = f"{mcap/1000:.1f}K TAO"
        else:
            mcap_str = f"{mcap:.0f} TAO"
        
        # Category class for border color
        category_class = f"category-{row.primary_category.replace(' ', '-').replace('/', '-')}" if bool(pd.notna(row.primary_category)) else ""
        
        # Subnet name with number
        subnet_display_name = f"{row.netuid} {row.subnet_name}" if bool(pd.notna(row.subnet_name)) else f"Subnet {row.netuid}"
        
        # Get favicon for website
        favicon_element = html.Div()
        try:
            if bool(pd.notna(row.favicon_url)) and bool(row.favicon_url):
                # Use cached favicon from database
                favicon_element = html.Img(
                    src=row.favicon_url,
                    alt="Favicon",
                    style={
                        'width': '20px',
                        'height': '20px',
                        'margin-right': '8px',
                        'border-radius': '2px'
                    }
                )
        except Exception as e:
            # If favicon logic fails, just continue without favicon
            print(f"Favicon error for subnet {row.netuid}: {e}")
            favicon_element = html.Div()
        
        # Confidence badge (simple, inline)
        confidence_score = row.confidence if bool(pd.notna(row.confidence)) else 0
        confidence_color = (
            "success" if confidence_score >= 90 else
            "warning" if confidence_score >= 70 else
            "danger"
        )
        confidence_badge = dbc.Badge(
            f"{confidence_score:.0f}% AI confidence",
            color=confidence_color,
            className="ms-2 small fw-normal opacity-75",
            style={"font-size": "0.75em", "font-weight": 400},
            id=f"confidence-badge-{row.netuid}"
        )
        confidence_tooltip = dbc.Tooltip(
            "Data confidence: Green = reliable data from website/GitHub, Yellow = mixed sources, Red = limited information.",
            target=f"confidence-badge-{row.netuid}",
            placement="top"
        )
        
        # Market cap with badge and tooltip (show USD) - safely calculate USD
        mcap_id = f"market-cap-{row.netuid}"
        mcap_usd = mcap * tao_price_usd if tao_price_usd > 0 else 0
        if mcap_usd >= 1_000_000:
            mcap_usd_str = f"${mcap_usd/1_000_000:.1f}M"
        elif mcap_usd >= 1_000:
            mcap_usd_str = f"${mcap_usd/1_000:.1f}K"
        else:
            mcap_usd_str = f"${mcap_usd:,.0f}"
        mcap_badge = dbc.Badge(
            f"{mcap_str} ({mcap_usd_str})",
            color="light",
            className="text-primary mb-0 px-2 py-1 fw-semibold",
            style={"font-size": "1em"},
            id=mcap_id
        )
        mcap_tooltip = dbc.Tooltip(
            "Market Capitalisation (MC) = token price × circulating supply. Shows what the network is worth right now, based on the number of tokens actually tradeable today. MC grows as new tokens are emitted, even if price is flat.",
            target=mcap_id,
            placement="auto"
        )
        # Category badge with tooltip directly on the badge
        cat_id = f"category-badge-{row.netuid}"
        val = row.primary_category
        if isinstance(val, (str, int, float)):
            show_badge = val is not None and bool(pd.notna(val))
        else:
            show_badge = False
        category_badge = (
            dbc.Badge(val, color="info", className="mb-2", id=cat_id)
            if show_badge
            else dbc.Badge("Uncategorized", color="secondary", className="mb-2", id=cat_id)
        )
        cat_tooltip = dbc.Tooltip(
            f"Category: {row.primary_category}. Click category filter to see similar AI services.",
            target=cat_id,
            placement="top"
        )
        # Card structure with tooltips directly on text
        website_val = row.website_url
        github_val = row.github_url
        website_ok = isinstance(website_val, (str, int, float)) and website_val is not None and bool(pd.notna(website_val))
        github_ok = isinstance(github_val, (str, int, float)) and github_val is not None and bool(pd.notna(github_val))
        card_body = [
            # Header with market cap
            html.Div([
                mcap_badge,
                mcap_tooltip
            ], className="text-end mb-2"),
            # Title with subnet number and confidence badge
            html.H5([
                favicon_element,
                subnet_display_name,
                confidence_badge,
                confidence_tooltip
            ], className="card-title mb-2 d-flex align-items-center"),
            # Category badge with tooltip
            category_badge,
            cat_tooltip,
            
            # Tagline
            html.P(row.tagline or "No description available", className="card-text mb-2"),
            
            # Tags
            html.Div([
                dbc.Badge(tag, color="primary", className="me-1 mb-1")
                for tag in tags[:6]  # Limit to 6 tags
            ], className="mb-3"),
            
            # Expandable description with links
            html.Details([
                html.Summary("What it does", className="text-primary fw-bold mb-2"),
                html.P(row.what_it_does if bool(pd.notna(row.what_it_does)) else "No detailed description available.", className="card-text small mb-2"),
                html.Div([
                    html.A(
                        "🌐 Website", 
                        href=format_url(row.website_url), 
                        target="_blank", 
                        className="btn btn-sm btn-outline-primary me-2"
                    ),
                    html.A(
                        "📁 GitHub", 
                        href=format_url(row.github_url), 
                        target="_blank", 
                        className="btn btn-sm btn-outline-secondary"
                    )
                ], className="mt-2") if (website_ok or github_ok) else html.Div(),
            ], className="mb-2"),
            
            # New expandable section for use case and technical features
            html.Details([
                html.Summary("Use Case & Technical Features", className="text-primary fw-bold mb-2"),
                html.Div([
                    # Primary use case
                    html.Div([
                        html.Strong("Primary Use Case: ", className="text-info"),
                        html.Span(row.primary_use_case or "Not specified", className="small")
                    ], className="mb-2") if bool(pd.notna(row.primary_use_case)) else html.Div(),
                    
                    # Key technical features
                    html.Div([
                        html.Strong("Key Technical Features: ", className="text-info"),
                        html.Span(row.key_technical_features or "Not specified", className="small")
                    ], className="mb-2") if bool(pd.notna(row.key_technical_features)) else html.Div(),
                ])
            ], className="mb-2") if (bool(pd.notna(row.primary_use_case)) or bool(pd.notna(row.key_technical_features))) else html.Div(),
            
            # Provenance info
            html.Small(
                format_provenance(row.provenance) if bool(pd.notna(row.provenance)) else "",
                className="text-muted d-block"
            ) if bool(pd.notna(row.provenance)) else html.Div(),
            
            # View Details button - prominent and clear
            html.Div([
                html.A(
                    dbc.Button(
                        [
                            html.I(className="bi bi-arrow-right me-2"),
                            "View Details"
                        ],
                        color="primary",
                        size="md",
                        className="w-100 fw-bold"
                    ),
                    href=f"/dash/subnet-detail?netuid={row.netuid}",
                    className="text-decoration-none"
                )
            ], className="mt-3")
        ]
        
        # Debug print for link generation
        print(f"Generated link for subnet {row.netuid}: /dash/subnet-detail?netuid={row.netuid}")
        
        return dbc.Col(
            html.Div([
                dbc.Card(
                    dbc.CardBody(card_body),
                    className=f"h-100 {category_class}",
                    style={
                        "border-left": "4px solid #3e6ae1",
                        "position": "relative",
                        "padding-top": "32px",  # More space for ribbon
                        "background": "#f8f9fa",  # Debug background
                    }
                )
            ], style={
                'position': 'relative',
                'min-height': '240px',
                'overflow': 'visible'
            }),
            lg=4, md=6, className="mb-4"
        )
    
    cards = [make_card(r) for _, r in df.iterrows()]
    print(f"Generated {len(cards)} cards")  # Debug print
    return cards

# Callback for expandable cards
@callback(
    Output({"type": "subnet-card", "index": "ALL"}, "className"),
    Output({"type": "expand-btn", "index": "ALL"}, "className"),
    Input({"type": "expand-btn", "index": "ALL"}, "n_clicks"),
    State({"type": "expand-btn", "index": "ALL"}, "id"),
    prevent_initial_call=True
)
def toggle_card_expansion(n_clicks, btn_ids):
    if not n_clicks or not btn_ids:
        return ["subnet-card"] * len(btn_ids), ["expand-btn"] * len(btn_ids)
    
    # Find which button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return ["subnet-card"] * len(btn_ids), ["expand-btn"] * len(btn_ids)
    
    clicked_id = ctx.triggered[0]["prop_id"].split(".")[0]
    clicked_id = json.loads(clicked_id)
    clicked_index = clicked_id["index"]
    
    # Update classes
    card_classes = []
    btn_classes = []
    
    for btn_id in btn_ids:
        if btn_id["index"] == clicked_index:
            # Toggle this card
            is_expanded = "expanded" in (btn_classes[-1] if btn_classes else "")
            card_classes.append("subnet-card expanded" if not is_expanded else "subnet-card")
            btn_classes.append("expand-btn expanded" if not is_expanded else "expand-btn")
        else:
            card_classes.append("subnet-card")
            btn_classes.append("expand-btn")
    
    return card_classes, btn_classes

@callback(
    Output("chart-section", "style"),
    Input("cat-drop", "value"),
)
def toggle_chart_section(selected_category):
    """Show/hide entire chart section based on category selection."""
    if selected_category == "All":
        return {"display": "block"}  # Show section
    else:
        return {"display": "none"}   # Hide section completely

# Clientside callback to update screen size only on resize
# TODO: Re-implement screen size detection in a compatible way if mobile-specific tweaks are needed.
# (Old code removed here)

def register_callbacks(dash_app):
    """Register all callbacks with the dash app."""
    pass  # Callbacks are already registered via decorators 