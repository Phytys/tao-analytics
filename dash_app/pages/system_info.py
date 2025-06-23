"""
System Information Dashboard for TAO Analytics.
Provides detailed system analytics and performance metrics for administrators.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from services.metrics import metrics_service
from services.cache import cache_stats
import pandas as pd
from datetime import datetime

# Color schemes
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
    "Dev-Tooling": "#98df8a",
    "AI-Verification & Trust": "#ff6b6b",
    "Confidential-Compute": "#4ecdc4"
}

layout = dbc.Container([
    # Header
    html.Div([
        html.H1("System Information Dashboard", className="dashboard-title"),
        html.P("Administrative overview of system performance and data quality", className="dashboard-subtitle"),
        html.Div([
            html.Span("🔐 Admin Access", className="badge bg-primary me-2"),
            html.A("Logout", href="/admin/logout", className="btn btn-outline-secondary btn-sm")
        ], className="mt-2")
    ], className="dashboard-header mb-4"),
    
    # Control buttons
    html.Div([
        dbc.Button("Refresh Data", id="refresh-btn", color="primary", className="me-2"),
        dbc.Button("Clear Cache", id="clear-cache-btn", color="warning", className="me-2"),
        dbc.Button("Cleanup Cache", id="cleanup-cache-btn", color="info"),
    ], className="mb-4"),
    
    # KPI Cards
    html.Div(id="kpi-cards", className="mb-4"),
    
    # Enrichment Progress Section
    html.Div([
        html.H3("Enrichment Progress", className="mb-3"),
        html.Div(id="enrichment-progress", className="mb-4"),
    ], className="mb-4"),
    
    # Charts Row - Only show useful charts
    dbc.Row([
        dbc.Col([
            html.Div(id="category-chart", className="chart-container")
        ], md=6),
        dbc.Col([
            html.Div(id="cache-stats", className="chart-container")
        ], md=6),
    ], className="mb-4"),
    
    # Top Subnets Table
    html.Div(id="top-subnets", className="mb-4"),
    
    # Store for data
    dcc.Store(id="system-data"),
    dcc.Interval(id="refresh-interval", interval=30000, n_intervals=0),  # 30 second refresh
], fluid=True, className="px-4")

@callback(
    Output("system-data", "data"),
    Input("refresh-interval", "n_intervals"),
    prevent_initial_call=False
)
def load_system_data(n_intervals):
    """Load all system data."""
    print(f"[DEBUG] Loading system data, interval: {n_intervals}")
    try:
        # Get essential metrics only
        landing_kpis = metrics_service.get_landing_kpis()
        category_stats = metrics_service.get_category_stats()
        top_subnets = metrics_service.get_top_subnets(limit=10, sort_by='market_cap')
        cache_info = cache_stats()
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'top_subnets': top_subnets,
            'cache_info': cache_info,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error loading system data: {e}")
        return {}

@callback(
    Output("kpi-cards", "children"),
    Input("system-data", "data")
)
def render_kpi_cards(data):
    """Render KPI cards."""
    if not data:
        return html.Div("No data available")
    
    kpis = data['landing_kpis']
    
    cards = [
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis['total_subnets']}", className="card-title text-primary"),
                html.P("Total Subnets", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis['enriched_subnets']}", className="card-title text-success"),
                html.P("Enriched Subnets", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis['enrichment_rate']}%", className="card-title text-info"),
                html.P("Enrichment Rate", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis['total_market_cap']}M", className="card-title text-warning"),
                html.P("Total Market Cap (TAO)", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis['high_confidence']}", className="card-title text-success"),
                html.P("High Confidence", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{len(kpis['category_distribution'])}", className="card-title text-primary"),
                html.P("Active Categories", className="card-text")
            ])
        ], className="text-center"),
    ]
    
    return dbc.Row([dbc.Col(card, md=4, lg=2) for card in cards], className="g-3")

@callback(
    Output("enrichment-progress", "children"),
    Input("system-data", "data")
)
def render_enrichment_progress(data):
    """Render enrichment progress section."""
    if not data:
        return html.Div("No data available")
    
    kpis = data['landing_kpis']
    total = kpis['total_subnets']
    enriched = kpis['enriched_subnets']
    remaining = total - enriched
    
    progress_bar = dbc.Progress(
        value=enriched,
        max=total,
        label=f"{enriched}/{total} ({kpis['enrichment_rate']}%)",
        color="success",
        className="mb-3"
    )
    
    stats = [
        html.Div([
            html.Strong(f"{enriched}"), " subnets enriched",
            html.Br(),
            html.Strong(f"{remaining}"), " subnets remaining"
        ], className="text-muted")
    ]
    
    if remaining > 0:
        stats.append(
            html.Div([
                html.Br(),
                html.Small("💡 Run enrichment script to improve coverage", className="text-info")
            ])
        )
    
    return html.Div([progress_bar] + stats)

@callback(
    Output("category-chart", "children"),
    Input("system-data", "data")
)
def render_category_chart(data):
    """Render category distribution chart."""
    if not data or 'category_stats' not in data:
        return html.Div("No data available")
    
    df = pd.DataFrame(data['category_stats'])
    
    # Check if dataframe is empty
    if df.empty:
        return html.Div("No category data available")
    
    fig = px.bar(
        df,
        x='category',
        y='count',
        title="Subnets per Category",
        color='category',
        color_discrete_map=CATEGORY_COLORS,
        text='count'
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
        xaxis_tickangle=-45
    )
    
    fig.update_traces(textposition='outside')
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("cache-stats", "children"),
    Input("system-data", "data")
)
def render_cache_stats(data):
    """Render cache statistics."""
    if not data or 'cache_info' not in data:
        return html.Div("No cache data available")
    
    cache_info = data['cache_info']
    
    # Create cache usage chart
    cache_sizes = {
        'API Cache': cache_info['api_cache']['size'],
        'DB Cache': cache_info['db_cache']['size']
    }
    
    fig = px.pie(
        values=list(cache_sizes.values()),
        names=list(cache_sizes.keys()),
        title="Cache Usage",
        color=list(cache_sizes.keys()),
        color_discrete_map={'API Cache': '#1f77b4', 'DB Cache': '#ff7f0e'}
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True
    )
    
    # Add cache details
    details = html.Div([
        html.Small([
            html.Strong("API Cache: "), f"{cache_info['api_cache']['size']}/{cache_info['api_cache']['max_size']}",
            html.Br(),
            html.Strong("DB Cache: "), f"{cache_info['db_cache']['size']}/{cache_info['db_cache']['max_size']}",
        ], className="text-muted mt-2")
    ])
    
    return html.Div([
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        details
    ])

@callback(
    Output("top-subnets", "children"),
    Input("system-data", "data")
)
def render_top_subnets(data):
    """Render top subnets table."""
    if not data or 'top_subnets' not in data:
        return html.Div("No subnet data available")
    
    subnets = data['top_subnets']
    
    if not subnets:
        return html.Div("No enriched subnets available")
    
    # Create table
    table_header = [
        html.Thead(html.Tr([
            html.Th("NetUID"),
            html.Th("Name"),
            html.Th("Category"),
            html.Th("Confidence"),
            html.Th("Market Cap (TAO)"),
            html.Th("Context Tokens")
        ]))
    ]
    
    table_body = [html.Tbody([
        html.Tr([
            html.Td(subnet['netuid']),
            html.Td(subnet['name']),
            html.Td(subnet['category']),
            html.Td(f"{subnet['confidence_score']}%"),
            html.Td(f"{subnet['market_cap']:,.0f}"),
            html.Td(subnet['context_tokens'])
        ]) for subnet in subnets
    ])]
    
    return html.Div([
        html.H3("Top Subnets by Market Cap", className="mb-3"),
        dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True)
    ])

def register_callbacks(dash_app):
    """Register all callbacks for the system info page."""
    pass 