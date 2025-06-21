import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback, callback_context
import plotly.express as px
import plotly.graph_objects as go
from services.db import load_subnet_frame
import pandas as pd, datetime as dt, json, os
from io import StringIO

CATS = ["All"] + sorted(
    load_subnet_frame()["primary_category"].dropna().unique().tolist()
)

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

layout = dbc.Container(
    [
        # --- Tesla-inspired header ---
        html.Div([
            html.H1("Bittensor Subnet Explorer", className="dashboard-title"),
            html.P("Comprehensive analytics and insights for the decentralized AI network", className="dashboard-subtitle"),
        ], className="dashboard-header"),
        
        # --- filter controls ---
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Category Filter", className="form-label"),
                    dcc.Dropdown(
                        id="cat-drop",
                        options=[{"label": c, "value": c} for c in CATS],
                        value="All",
                        clearable=False,
                        className="form-select"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Search Subnets", className="form-label"),
                    dcc.Input(
                        id="search-box",
                        type="text",
                        placeholder="Search by name or tags...",
                        debounce=True,
                        className="form-control"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Last Updated", className="form-label"),
                    html.Div(id="refresh-stamp", className="text-muted"),
                ], md=4),
            ]),
        ], className="filter-controls"),
        
        # --- KPI strip ---
        html.Div(id="kpi-strip", className="mb-4"),
        
        # --- charts ---
        html.Div([
            dcc.Tabs(
                id="charts-tab",
                value="count",
                children=[
                    dcc.Tab(label="Subnets per Category", value="count"),
                    dcc.Tab(label="Market-cap by Category", value="mcap"),
                ],
                className="nav-tabs"
            ),
            html.Div(id="chart-fig", className="chart-container"),
        ]),
        
        # --- card grid ---
        html.Div(id="card-grid", className="row g-4"),
        dcc.Store(id="cache-df"),
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
    Output("kpi-strip", "children"),
    Input("cache-df", "data"),
)
def render_kpis(json_df):
    if not json_df:
        return html.Div("No data available")
    
    df = pd.read_json(StringIO(json_df), orient="split")
    total = len(df)
    cats = df["primary_category"].nunique()
    privacy = (df["privacy_security_flag"] == True).mean() * 100
    avg_confidence = df["confidence"].mean()
    
    badges = [
        html.Span(f"{total} Subnets", className="kpi-badge"),
        html.Span(f"{cats} Categories", className="kpi-badge"),
        html.Span(f"{privacy:.0f}% Privacy-Focused", className="kpi-badge"),
        html.Span(f"{avg_confidence:.0f}% Avg Confidence", className="kpi-badge"),
    ]
    return html.Div(badges)

@callback(
    Output("chart-fig", "children"),
    Input("cache-df", "data"),
    Input("charts-tab", "value"),
)
def render_chart(json_df, mode):
    if not json_df:
        return html.Div("No data available")
    
    df = pd.read_json(StringIO(json_df), orient="split")
    
    if mode == "count":
        fig = px.pie(
            df.groupby("primary_category").size().reset_index(name="count"),
            names="primary_category",
            values="count",
            title="Subnets per Category",
            color_discrete_map=CATEGORY_COLORS
        )
    else:
        fig = px.bar(
            df.groupby("primary_category")["mcap_tao"].sum().reset_index(),
            x="primary_category",
            y="mcap_tao",
            title="Total Market-cap (TAO) by Category",
            color="primary_category",
            color_discrete_map=CATEGORY_COLORS
        )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
        showlegend=True,
        font=dict(family="Inter, sans-serif")
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("card-grid", "children"),
    Input("cache-df", "data"),
)
def render_cards(json_df):
    if not json_df:
        return html.Div("No data available")
    
    df = pd.read_json(StringIO(json_df), orient="split").sort_values("mcap_tao", ascending=False)
    
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
        category_class = f"category-{row.primary_category.replace(' ', '-').replace('/', '-')}" if pd.notna(row.primary_category) else ""
        
        # Subnet name with number
        subnet_display_name = f"{row.netuid} {row.subnet_name}" if pd.notna(row.subnet_name) else f"Subnet {row.netuid}"
        
        # Category badge
        category_badge = (
            dbc.Badge(row.primary_category, color="info", className="mb-2")
            if pd.notna(row.primary_category)
            else dbc.Badge("Uncategorized", color="secondary", className="mb-2")
        )
        
        chips = [
            dbc.Badge(tag, color="primary", className="me-1 mb-1")
            for tag in tags[:6]  # Limit to 6 tags
        ]
        
        privacy_badge = (
            dbc.Badge("Privacy", color="danger", className="ms-1")
            if row.privacy_security_flag
            else ""
        )
        
        # Detailed description
        description = row.what_it_does if pd.notna(row.what_it_does) else "No detailed description available."
        
        # Links section with proper URL formatting
        links = []
        website_url = format_url(row.website_url)
        github_url = format_url(row.github_url)
        
        if website_url:
            links.append(
                html.A(
                    "🌐 Website", 
                    href=website_url, 
                    target="_blank", 
                    className="btn btn-sm btn-outline-primary me-2"
                )
            )
        if github_url:
            links.append(
                html.A(
                    "📁 GitHub", 
                    href=github_url, 
                    target="_blank", 
                    className="btn btn-sm btn-outline-secondary"
                )
            )
        
        # Card structure with expandable description
        card_body = [
            # Header with market cap
            html.Div([
                html.H6(mcap_str, className="text-primary mb-0"),
            ], className="text-end mb-2"),
            
            # Title with subnet number
            html.H5(subnet_display_name, className="card-title mb-2"),
            
            # Category
            category_badge,
            
            # Tagline
            html.P(row.tagline or "No description available", className="card-text mb-2"),
            
            # Tags
            html.Div(chips + [privacy_badge], className="mb-3"),
            
            # Expandable description with links
            html.Details([
                html.Summary("What it does", className="text-primary fw-bold mb-2"),
                html.P(description, className="card-text small mb-2"),
                html.Div(links, className="mt-2") if links else html.Div()
            ], className="mb-2"),
            
            # Confidence score
            html.Small(f"Confidence: {row.confidence:.0f}%", className="text-muted"),
        ]
        
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(card_body),
                className=f"h-100 {category_class}",
                style={"border-left": "4px solid #3e6ae1"}
            ),
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

def register_callbacks(dash_app):
    """Register all callbacks with the dash app."""
    pass  # Callbacks are already registered via decorators 