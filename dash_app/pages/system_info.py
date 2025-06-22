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
    "Dev-Tooling": "#98df8a"
}

CONFIDENCE_COLORS = {
    '0-20': '#dc3545',
    '20-40': '#fd7e14', 
    '40-60': '#ffc107',
    '60-80': '#20c997',
    '80-90': '#17a2b8',
    '90-100': '#28a745'
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
    
    # Charts Row 1
    dbc.Row([
        dbc.Col([
            html.Div(id="category-chart", className="chart-container")
        ], md=6),
        dbc.Col([
            html.Div(id="confidence-chart", className="chart-container")
        ], md=6),
    ], className="mb-4"),
    
    # Charts Row 2
    dbc.Row([
        dbc.Col([
            html.Div(id="provenance-chart", className="chart-container")
        ], md=6),
        dbc.Col([
            html.Div(id="cache-stats", className="chart-container")
        ], md=6),
    ], className="mb-4"),
    
    # Top Subnets Table
    html.Div(id="top-subnets", className="mb-4"),
    
    # Performance Metrics
    html.Div(id="performance-metrics", className="mb-4"),
    
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
        # Get all metrics
        landing_kpis = metrics_service.get_landing_kpis()
        category_stats = metrics_service.get_category_stats()
        confidence_dist = metrics_service.get_confidence_distribution()
        provenance_stats = metrics_service.get_provenance_stats()
        top_subnets = metrics_service.get_top_subnets(limit=10, sort_by='market_cap')
        cache_info = cache_stats()
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'confidence_dist': confidence_dist,
            'provenance_stats': provenance_stats,
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
                html.H4(f"{kpis['avg_confidence']}%", className="card-title text-warning"),
                html.P("Avg Confidence", className="card-text")
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
                html.H4(f"{kpis['total_market_cap']:.1f}M", className="card-title text-primary"),
                html.P("Total Market Cap (TAO)", className="card-text")
            ])
        ], className="text-center"),
    ]
    
    return dbc.Row([dbc.Col(card, md=4, lg=2) for card in cards], className="g-3")

@callback(
    Output("category-chart", "children"),
    Input("system-data", "data")
)
def render_category_chart(data):
    """Render category distribution chart."""
    if not data or 'category_stats' not in data:
        return html.Div("No data available")
    
    df = pd.DataFrame(data['category_stats'])
    
    fig = px.bar(
        df,
        x='category',
        y='count',
        color='category',
        title="Subnets by Category",
        color_discrete_map=CATEGORY_COLORS
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif")
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("confidence-chart", "children"),
    Input("system-data", "data")
)
def render_confidence_chart(data):
    """Render confidence distribution chart."""
    if not data or 'confidence_dist' not in data:
        return html.Div("No data available")
    
    df = pd.DataFrame(data['confidence_dist'])
    
    fig = px.bar(
        df,
        x='range',
        y='count',
        color='range',
        title="Confidence Score Distribution",
        color_discrete_map=CONFIDENCE_COLORS
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif")
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("provenance-chart", "children"),
    Input("system-data", "data")
)
def render_provenance_chart(data):
    """Render provenance distribution chart."""
    if not data or 'provenance_stats' not in data:
        return html.Div("No data available")
    
    provenance_data = data['provenance_stats']['provenance_counts']
    df = pd.DataFrame(provenance_data)
    
    fig = px.pie(
        df,
        names='provenance',
        values='count',
        title="Data Provenance Distribution"
    )
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif")
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("cache-stats", "children"),
    Input("system-data", "data")
)
def render_cache_stats(data):
    """Render cache statistics."""
    if not data or 'cache_info' not in data:
        return html.Div("No data available")
    
    cache_info = data['cache_info']
    
    # Create cache usage chart
    api_cache_usage = (cache_info['api_cache']['size'] / cache_info['api_cache']['max_size']) * 100
    db_cache_usage = (cache_info['db_cache']['size'] / cache_info['db_cache']['max_size']) * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=api_cache_usage,
        title={'text': "API Cache Usage"},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': "darkblue"},
               'steps': [
                   {'range': [0, 50], 'color': "lightgray"},
                   {'range': [50, 80], 'color': "yellow"},
                   {'range': [80, 100], 'color': "red"}
               ],
               'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 90}}
    ))
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif")
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

@callback(
    Output("top-subnets", "children"),
    Input("system-data", "data")
)
def render_top_subnets(data):
    """Render top subnets table."""
    if not data or 'top_subnets' not in data:
        return html.Div("No data available")
    
    subnets = data['top_subnets']
    
    table_header = [
        html.Thead(html.Tr([
            html.Th("NetUID"),
            html.Th("Name"),
            html.Th("Category"),
            html.Th("Market Cap (TAO)"),
            html.Th("Confidence"),
            html.Th("Context Tokens"),
            html.Th("Provenance")
        ]))
    ]
    
    table_body = [html.Tbody([
        html.Tr([
            html.Td(subnet['netuid']),
            html.Td(subnet['name']),
            html.Td(subnet['category']),
            html.Td(f"{subnet['market_cap']:.2f}"),
            html.Td(f"{subnet['confidence_score']:.0f}%"),
            html.Td(subnet['context_tokens']),
            html.Td(subnet['provenance'])
        ]) for subnet in subnets
    ])]
    
    return html.Div([
        html.H3("Top Subnets by Market Cap", className="mb-3"),
        dbc.Table(table_header + table_body, bordered=True, hover=True)
    ])

@callback(
    Output("performance-metrics", "children"),
    Input("system-data", "data")
)
def render_performance_metrics(data):
    """Render performance metrics."""
    if not data:
        return html.Div("No data available")
    
    cache_info = data.get('cache_info', {})
    provenance_stats = data.get('provenance_stats', {})
    
    metrics = [
        ("API Cache Size", f"{cache_info.get('api_cache', {}).get('size', 0)}/{cache_info.get('api_cache', {}).get('max_size', 0)}"),
        ("DB Cache Size", f"{cache_info.get('db_cache', {}).get('size', 0)}/{cache_info.get('db_cache', {}).get('max_size', 0)}"),
        ("API Cache TTL", f"{cache_info.get('api_cache', {}).get('ttl', 0)}s"),
        ("DB Cache TTL", f"{cache_info.get('db_cache', {}).get('ttl', 0)}s"),
        ("Avg Context Tokens", f"{provenance_stats.get('context_tokens', {}).get('avg', 0):.1f}"),
        ("Max Context Tokens", f"{provenance_stats.get('context_tokens', {}).get('max', 0)}"),
        ("Last Updated", data.get('timestamp', 'Unknown'))
    ]
    
    metric_cards = [
        dbc.Card([
            dbc.CardBody([
                html.H6(label, className="card-title"),
                html.P(value, className="card-text")
            ])
        ], className="text-center") for label, value in metrics
    ]
    
    return html.Div([
        html.H3("Performance Metrics", className="mb-3"),
        dbc.Row([dbc.Col(card, md=3) for card in metric_cards], className="g-3")
    ])

def register_callbacks(dash_app):
    """Register all callbacks with the dash app."""
    pass  # Callbacks are already registered via decorators 