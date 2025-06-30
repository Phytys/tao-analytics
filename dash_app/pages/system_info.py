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
from datetime import datetime, timedelta
from services.tao_metrics import tao_metrics_service

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

# Helper to check for stale data
STALE_THRESHOLD_HOURS = 2

def get_stale_warnings(landing_kpis):
    warnings = []
    now = datetime.utcnow()
    # TAO price
    price_ts = landing_kpis.get('tao_price_updated')
    if price_ts:
        try:
            price_dt = datetime.fromisoformat(price_ts.replace('Z', '+00:00'))
            if (now - price_dt) > timedelta(hours=STALE_THRESHOLD_HOURS):
                warnings.append(f"TAO price data is stale (last updated: {price_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        except Exception:
            warnings.append("TAO price data timestamp is invalid or unavailable.")
    else:
        warnings.append("TAO price data is unavailable.")
    # Screener
    screener_ts = landing_kpis.get('screener_updated')
    if screener_ts:
        try:
            screener_dt = datetime.fromisoformat(screener_ts.replace('Z', '+00:00'))
            if (now - screener_dt) > timedelta(hours=STALE_THRESHOLD_HOURS):
                warnings.append(f"Subnet screener data is stale (last updated: {screener_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        except Exception:
            warnings.append("Subnet screener data timestamp is invalid or unavailable.")
    else:
        warnings.append("Subnet screener data is unavailable.")
    return warnings

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
    
    # Warning Alert (at the top)
    html.Div(id="warning-alert", className="mb-4"),
    
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
        
        # Get network overview for timestamp data
        network_overview = tao_metrics_service.get_network_overview()
        
        # Add warnings for stale data using network overview timestamps
        warnings = get_stale_warnings(network_overview)
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'top_subnets': top_subnets,
            'cache_info': cache_info,
            'warnings': warnings,
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
    
    # Add enrichment stats cards
    enrichment_cards = [
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis.get('avg_context_tokens', 0)}", className="card-title text-info"),
                html.P("Avg Context Tokens", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis.get('rich_context_rate', 0)}%", className="card-title text-success"),
                html.P("Rich Context (>1K tokens)", className="card-text")
            ])
        ], className="text-center"),
        dbc.Card([
            dbc.CardBody([
                html.H4(f"{kpis.get('category_suggestions', 0)}", className="card-title text-warning"),
                html.P("Category Suggestions", className="card-text")
            ])
        ], className="text-center"),
    ]
    
    # Provenance breakdown card
    provenance_stats = kpis.get('provenance_stats', {})
    total_provenance = sum(provenance_stats.values())
    if total_provenance > 0:
        context_pct = round((provenance_stats.get('context', 0) / total_provenance) * 100, 1)
        model_pct = round((provenance_stats.get('model', 0) / total_provenance) * 100, 1)
        both_pct = round((provenance_stats.get('both', 0) / total_provenance) * 100, 1)
        
        provenance_card = dbc.Card([
            dbc.CardBody([
                html.H4(f"{context_pct}%", className="card-title text-success"),
                html.P("Context-Based", className="card-text"),
                html.Small(f"Model: {model_pct}% | Mixed: {both_pct}%", className="text-muted")
            ])
        ], className="text-center")
    else:
        provenance_card = dbc.Card([
            dbc.CardBody([
                html.H4("N/A", className="card-title text-muted"),
                html.P("Provenance", className="card-text")
            ])
        ], className="text-center")
    
    enrichment_cards.append(provenance_card)
    
    return [
        dbc.Row([dbc.Col(card, md=4, lg=2) for card in cards], className="g-3 mb-4"),
        dbc.Row([dbc.Col(card, md=3) for card in enrichment_cards], className="g-3")
    ]

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
    
    # Add context quality info
    if kpis.get('avg_context_tokens', 0) > 0:
        stats.append(
            html.Div([
                html.Br(),
                html.Strong(f"{kpis['avg_context_tokens']}"), " avg context tokens",
                html.Br(),
                html.Strong(f"{kpis.get('rich_context_rate', 0)}%"), " have rich context (>1K tokens)"
            ], className="text-info")
        )
    
    # Add last enrichment timestamp
    if kpis.get('last_enriched_at'):
        from datetime import datetime
        try:
            last_enriched = datetime.fromisoformat(kpis['last_enriched_at'].replace('Z', '+00:00'))
            stats.append(
                html.Div([
                    html.Br(),
                    html.Small(f"Last enriched: {last_enriched.strftime('%Y-%m-%d %H:%M:%S')}", className="text-muted")
                ])
            )
        except:
            pass
    
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

@callback(
    Output("system-data", "data", allow_duplicate=True),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True
)
def refresh_data(n_clicks):
    """Refresh system data."""
    print(f"[DEBUG] Refresh button clicked: {n_clicks}")
    try:
        # Get essential metrics only
        landing_kpis = metrics_service.get_landing_kpis()
        category_stats = metrics_service.get_category_stats()
        top_subnets = metrics_service.get_top_subnets(limit=10, sort_by='market_cap')
        cache_info = cache_stats()
        
        # Get network overview for timestamp data
        network_overview = tao_metrics_service.get_network_overview()
        
        # Add warnings for stale data using network overview timestamps
        warnings = get_stale_warnings(network_overview)
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'top_subnets': top_subnets,
            'cache_info': cache_info,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error refreshing data: {e}")
        return {}

@callback(
    Output("system-data", "data", allow_duplicate=True),
    Input("clear-cache-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_cache(n_clicks):
    """Clear all caches."""
    print(f"[DEBUG] Clear cache button clicked: {n_clicks}")
    try:
        from services.cache import clear_all_caches
        clear_all_caches()
        print("All caches cleared successfully")
        
        # Reload data after clearing cache
        landing_kpis = metrics_service.get_landing_kpis()
        category_stats = metrics_service.get_category_stats()
        top_subnets = metrics_service.get_top_subnets(limit=10, sort_by='market_cap')
        cache_info = cache_stats()
        
        # Get network overview for timestamp data
        network_overview = tao_metrics_service.get_network_overview()
        
        # Add warnings for stale data using network overview timestamps
        warnings = get_stale_warnings(network_overview)
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'top_subnets': top_subnets,
            'cache_info': cache_info,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return {}

@callback(
    Output("system-data", "data", allow_duplicate=True),
    Input("cleanup-cache-btn", "n_clicks"),
    prevent_initial_call=True
)
def cleanup_cache(n_clicks):
    """Cleanup expired cache entries."""
    print(f"[DEBUG] Cleanup cache button clicked: {n_clicks}")
    try:
        from services.cache import cleanup_all_caches
        cleanup_all_caches()
        print("Cache cleanup completed")
        
        # Reload data after cleanup
        landing_kpis = metrics_service.get_landing_kpis()
        category_stats = metrics_service.get_category_stats()
        top_subnets = metrics_service.get_top_subnets(limit=10, sort_by='market_cap')
        cache_info = cache_stats()
        
        # Get network overview for timestamp data
        network_overview = tao_metrics_service.get_network_overview()
        
        # Add warnings for stale data using network overview timestamps
        warnings = get_stale_warnings(network_overview)
        
        return {
            'landing_kpis': landing_kpis,
            'category_stats': category_stats,
            'top_subnets': top_subnets,
            'cache_info': cache_info,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error cleaning up cache: {e}")
        return {}

@callback(
    Output("warning-alert", "children"),
    Input("system-data", "data")
)
def render_warnings(data):
    """Render warning alerts for stale data."""
    if not data:
        return html.Div()
    
    warnings = data.get('warnings', [])
    if not warnings:
        return html.Div()
    
    return dbc.Alert([
        html.H5("⚠️ Data Collection Warnings", className="alert-heading"),
        html.P("The following data sources may be stale or unavailable:"),
        html.Ul([html.Li(warning) for warning in warnings])
    ], color="warning", dismissable=True, className="mb-4")

def register_callbacks(dash_app):
    """Register all callbacks for the system info page."""
    pass 