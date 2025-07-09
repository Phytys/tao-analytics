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
from services.db import get_db
from models import MetricsSnap
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
        dbc.Button("Cleanup Cache", id="cleanup-cache-btn", color="info", className="me-2"),
        dbc.Button("Clear GPT Insights", id="clear-gpt-insights-btn", color="danger", className="me-2"),
        dbc.Button("Clear GPT Correlation", id="clear-gpt-correlation-btn", color="danger"),
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
    
    # Memory & Cache Monitoring Section
    html.Div([
        html.H3("Memory & Cache Monitoring", className="mb-3"),
        html.Div(id="memory-cache-status", className="mb-4"),
    ], className="mb-4"),
    
    # TAO Score Monitoring Section
    html.Div([
        html.H3("TAO Score Monitoring", className="mb-3"),
        html.Div(id="tao-score-status", className="mb-4"),
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
    Output("memory-cache-status", "children"),
    Input("system-data", "data")
)
def render_memory_cache_status(data):
    """Render memory and cache monitoring status."""
    try:
        from services.cache_utils import _get_memory_usage, _memory_cache, _cache_sizes
        
        # Get memory usage
        memory_mb = _get_memory_usage()
        
        # Get cache statistics
        cache_entries = len(_memory_cache)
        cache_size_mb = sum(_cache_sizes.values()) / (1024 * 1024) if _cache_sizes else 0
        
        # Determine memory status
        if memory_mb > 400:  # 80% of 512MB dyno
            memory_status = "danger"
            memory_icon = "🔴"
        elif memory_mb > 300:  # 60% of 512MB dyno
            memory_status = "warning"
            memory_icon = "🟡"
        else:
            memory_status = "success"
            memory_icon = "🟢"
        
        # Get Redis status from cache info
        redis_status = "Unknown"
        if data and 'cache_info' in data:
            cache_info = data['cache_info']
            if 'redis_available' in cache_info:
                redis_status = "🟢 Available" if cache_info['redis_available'] else "🔴 SSL Error"
            else:
                redis_status = "⚪ Unknown"
        
        return dbc.Card([
            dbc.CardBody([
                html.H5("Memory & Cache Status", className="card-title"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(f"{memory_icon} {memory_mb:.1f}MB", 
                                       className=f"text-{memory_status}"),
                                html.P("Memory Usage", className="card-text")
                            ])
                        ], className="text-center")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(f"{cache_entries}", className="text-info"),
                                html.P("Cache Entries", className="card-text")
                            ])
                        ], className="text-center")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(f"{cache_size_mb:.2f}MB", className="text-warning"),
                                html.P("Cache Size", className="card-text")
                            ])
                        ], className="text-center")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(redis_status, className="text-secondary"),
                                html.P("Redis Status", className="card-text")
                            ])
                        ], className="text-center")
                    ], width=3),
                ]),
                html.Hr(),
                html.H6("Cache Details", className="mt-3"),
                html.Div([
                    html.P(f"• Memory Usage: {memory_mb:.1f}MB"),
                    html.P(f"• In-Memory Cache Entries: {cache_entries}"),
                    html.P(f"• Cache Size: {cache_size_mb:.2f}MB"),
                    html.P(f"• Redis Status: {redis_status}"),
                    html.P(f"• Auto-cleanup threshold: 100MB"),
                ], className="text-muted small")
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading memory status: {e}", color="danger")

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
    Output("tao-score-status", "children"),
    Input("system-data", "data")
)
def render_tao_score_status(data):
    """Render TAO Score monitoring status."""
    try:
        session = get_db()
        
        # Get current TAO score statistics
        latest_metrics = session.query(MetricsSnap).filter(
            MetricsSnap.tao_score.isnot(None)
        ).order_by(MetricsSnap.timestamp.desc()).limit(1).first()
        
        if not latest_metrics:
            return html.Div("No TAO score data available", className="alert alert-warning")
        
        # Get TAO score distribution
        all_scores = session.query(MetricsSnap.tao_score).filter(
            MetricsSnap.tao_score.isnot(None),
            MetricsSnap.timestamp >= latest_metrics.timestamp - timedelta(hours=1)
        ).all()
        
        scores = [score[0] for score in all_scores if score[0] is not None]
        
        if not scores:
            return html.Div("No recent TAO score data", className="alert alert-warning")
        
        # Calculate statistics for v1.1
        score_stats = {
            'count': len(scores),
            'mean': sum(scores) / len(scores),
            'min': min(scores),
            'max': max(scores),
            'last_updated': latest_metrics.timestamp,
            'formula_version': 'v1.1 (Legacy)'
        }
        
        # Get v2.1 scores if available
        v21_scores = session.query(MetricsSnap.tao_score_v21).filter(
            MetricsSnap.tao_score_v21.isnot(None),
            MetricsSnap.timestamp >= latest_metrics.timestamp - timedelta(hours=1)
        ).all()
        
        v21_score_list = [score[0] for score in v21_scores if score[0] is not None]
        
        if v21_score_list:
            v21_stats = {
                'count': len(v21_score_list),
                'mean': sum(v21_score_list) / len(v21_score_list),
                'min': min(v21_score_list),
                'max': max(v21_score_list),
                'formula_version': 'v2.1 (Production)'
            }
        else:
            v21_stats = None
        
        # Check for recent score changes (last 24 hours)
        yesterday = latest_metrics.timestamp - timedelta(days=1)
        recent_changes = session.query(MetricsSnap).filter(
            MetricsSnap.timestamp >= yesterday,
            MetricsSnap.tao_score.isnot(None)
        ).order_by(MetricsSnap.netuid, MetricsSnap.timestamp.desc()).all()
        
        # Group by netuid and check for significant changes
        significant_changes = []
        seen_netuids = set()
        
        for metric in recent_changes:
            if metric.netuid in seen_netuids:
                continue
            seen_netuids.add(metric.netuid)
            
            # Get previous score (24h ago)
            prev_metric = session.query(MetricsSnap).filter(
                MetricsSnap.netuid == metric.netuid,
                MetricsSnap.timestamp < yesterday,
                MetricsSnap.tao_score.isnot(None)
            ).order_by(MetricsSnap.timestamp.desc()).first()
            
            if prev_metric and abs(metric.tao_score - prev_metric.tao_score) > 15:
                significant_changes.append({
                    'netuid': metric.netuid,
                    'subnet_name': metric.subnet_name,
                    'old_score': prev_metric.tao_score,
                    'new_score': metric.tao_score,
                    'change': metric.tao_score - prev_metric.tao_score,
                    'price_7d': metric.price_7d_change
                })
        
        session.close()
        
        # Create status cards for v1.1
        v11_cards = [
            dbc.Card([
                dbc.CardBody([
                    html.H4(score_stats['formula_version'], className="card-title text-primary"),
                    html.P("v1.1 Formula", className="card-text")
                ])
            ], className="text-center"),
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{score_stats['count']}", className="card-title text-success"),
                    html.P("v1.1 Subnets", className="card-text")
                ])
            ], className="text-center"),
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{score_stats['mean']:.1f}", className="card-title text-info"),
                    html.P("v1.1 Average", className="card-text")
                ])
            ], className="text-center"),
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{score_stats['min']:.1f} - {score_stats['max']:.1f}", className="card-title text-warning"),
                    html.P("v1.1 Range", className="card-text")
                ])
            ], className="text-center"),
        ]
        
        # Create status cards for v2.1 if available
        if v21_stats:
            v21_cards = [
                dbc.Card([
                    dbc.CardBody([
                        html.H4(v21_stats['formula_version'], className="card-title text-primary"),
                        html.P("v2.1 Formula", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{v21_stats['count']}", className="card-title text-success"),
                        html.P("v2.1 Subnets", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{v21_stats['mean']:.1f}", className="card-title text-info"),
                        html.P("v2.1 Average", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{v21_stats['min']:.1f} - {v21_stats['max']:.1f}", className="card-title text-warning"),
                        html.P("v2.1 Range", className="card-text")
                    ])
                ], className="text-center"),
            ]
        else:
            v21_cards = [
                dbc.Card([
                    dbc.CardBody([
                        html.H4("v2.1 Not Available", className="card-title text-muted"),
                        html.P("Not calculated yet", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4("0", className="card-title text-muted"),
                        html.P("v2.1 Subnets", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4("N/A", className="card-title text-muted"),
                        html.P("v2.1 Average", className="card-text")
                    ])
                ], className="text-center"),
                dbc.Card([
                    dbc.CardBody([
                        html.H4("N/A", className="card-title text-muted"),
                        html.P("v2.1 Range", className="card-text")
                    ])
                ], className="text-center"),
            ]
        
        # Create alerts for significant changes
        alerts = []
        if significant_changes:
            alert_content = []
            for change in significant_changes[:5]:  # Show top 5
                alert_content.append(html.Div([
                    html.Strong(f"Subnet {change['netuid']} ({change['subnet_name']}): "),
                    f"{change['old_score']:.1f} → {change['new_score']:.1f} ",
                    html.Span(f"({change['change']:+.1f})", 
                             className="text-danger" if change['change'] < 0 else "text-success"),
                    f" | 7d: {change['price_7d']:+.1f}%" if change['price_7d'] else ""
                ]))
            
            alerts.append(dbc.Alert([
                html.H5("🚨 Significant Score Changes (24h)", className="alert-heading"),
                html.Div(alert_content)
            ], color="warning", className="mb-3"))
        
        # Create score distribution chart
        score_df = pd.DataFrame({'score': scores})
        fig = px.histogram(score_df, x='score', nbins=20, 
                          title=f"TAO Score Distribution (Last Hour, {len(scores)} subnets)")
        fig.update_layout(height=300)
        
        return html.Div([
            # Production version indicator
            dbc.Alert([
                html.H5("🎯 Production Status", className="alert-heading"),
                html.P("TAO Score v2.1 is currently used in production across all user-facing pages.", className="mb-0")
            ], color="success", className="mb-3"),
            
            # v1.1 Status cards
            html.H5("TAO Score v1.1 (Legacy - For Comparison)", className="mb-2"),
            dbc.Row([dbc.Col(card, md=3) for card in v11_cards], className="mb-3"),
            
            # v2.1 Status cards
            html.H5("TAO Score v2.1 (Production - Currently Used)", className="mb-2"),
            dbc.Row([dbc.Col(card, md=3) for card in v21_cards], className="mb-3"),
            
            # Alerts
            html.Div(alerts),
            
            # Distribution chart
            dcc.Graph(figure=fig, className="mb-3"),
            
            # Correlation Analysis
            html.Div([
                html.H5("📊 Correlation Analysis", className="mb-3"),
                html.Div(id="tao-score-correlation", children=[
                    dbc.Spinner(html.Div("Loading correlation analysis..."), size="sm")
                ])
            ], className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(f"Last updated: {score_stats['last_updated'].strftime('%Y-%m-%d %H:%M:%S')} UTC", 
                          className="text-muted")
            ])
        ])
        
    except Exception as e:
        return html.Div(f"Error loading TAO score data: {str(e)}", className="alert alert-danger")

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
    Output("system-data", "data", allow_duplicate=True),
    Input("clear-gpt-insights-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_gpt_insights(n_clicks):
    """Clear GPT insights cache."""
    print(f"[DEBUG] Clear GPT insights button clicked: {n_clicks}")
    try:
        from services.gpt_insight import clear_gpt_insights_cache
        success = clear_gpt_insights_cache()
        if success:
            print("GPT insights cache cleared successfully")
        else:
            print("Failed to clear GPT insights cache")
        
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
        print(f"Error clearing GPT insights cache: {e}")
        return {}

@callback(
    Output("system-data", "data", allow_duplicate=True),
    Input("clear-gpt-correlation-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_gpt_correlation(n_clicks):
    """Clear GPT correlation analysis cache."""
    print(f"[DEBUG] Clear GPT correlation analysis button clicked: {n_clicks}")
    try:
        from services.correlation_analysis import correlation_service
        success = correlation_service.clear_cache()
        if success:
            print("GPT correlation analysis cache cleared successfully")
        else:
            print("Failed to clear GPT correlation analysis cache")
        
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
        print(f"Error clearing GPT correlation analysis cache: {e}")
        return {}

@callback(
    Output("tao-score-correlation", "children"),
    Input("system-data", "data")
)
def render_tao_score_correlation(data):
    """Render TAO score correlation analysis."""
    try:
        from services.calc_metrics import calculate_tao_scores_comparison
        import pandas as pd
        
        # Get historical data for predictive correlation analysis
        with get_db() as session:
            # Get data from yesterday and 7 days ago for predictive analysis
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            seven_days_ago = today - timedelta(days=7)
            
                    # Get all records with both TAO scores and price changes
        query = session.query(MetricsSnap).filter(
            MetricsSnap.tao_score.isnot(None),
            MetricsSnap.tao_score_v21.isnot(None),
            MetricsSnap.price_1d_change.isnot(None),
            MetricsSnap.price_7d_change.isnot(None)
        ).order_by(MetricsSnap.timestamp.desc())
        df = pd.read_sql(query.statement, session.bind)
        
        # Check if we have enough data and provide debugging info
        data_info = f"Records with both TAO scores and price data: {len(df)}"
        
        if df.empty or len(df) < 10:
            return html.Div([
                html.Div("Insufficient data for correlation analysis", className="alert alert-warning"),
                html.Small(data_info, className="text-muted d-block mt-2")
            ])
        
        # Calculate correlations between TAO scores and price changes
        correlations = {}
        
        # 1. TAO score vs 1-day price change
        if 'price_1d_change' in df.columns:
            try:
                v11_corr_1d = float(df['tao_score'].corr(df['price_1d_change']))
                v21_corr_1d = float(df['tao_score_v21'].corr(df['price_1d_change']))
                if not pd.isna(v11_corr_1d) and not pd.isna(v21_corr_1d):
                    correlations['1d'] = {
                        'v11': v11_corr_1d,
                        'v21': v21_corr_1d,
                        'improvement': v21_corr_1d - v11_corr_1d
                    }
            except:
                pass
        
        # 2. TAO score vs 7-day price change
        if 'price_7d_change' in df.columns:
            try:
                v11_corr_7d = float(df['tao_score'].corr(df['price_7d_change']))
                v21_corr_7d = float(df['tao_score_v21'].corr(df['price_7d_change']))
                if not pd.isna(v11_corr_7d) and not pd.isna(v21_corr_7d):
                    correlations['7d'] = {
                        'v11': v11_corr_7d,
                        'v21': v21_corr_7d,
                        'improvement': v21_corr_7d - v11_corr_7d
                    }
            except:
                pass
        
        # Create correlation cards
        correlation_cards = []
        for period, corr_data in correlations.items():
            if corr_data['v11'] is not None and corr_data['v21'] is not None:
                v11_color = "success" if corr_data['v11'] > 0.3 else "warning" if corr_data['v11'] > 0.1 else "danger"
                v21_color = "success" if corr_data['v21'] > 0.3 else "warning" if corr_data['v21'] > 0.1 else "danger"
                improvement_color = "success" if corr_data['improvement'] > 0 else "danger"
                improvement_icon = "↗️" if corr_data['improvement'] > 0 else "↘️"
                
                correlation_cards.append(
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(f"{period.upper()} Predictive Correlation", className="card-title"),
                                html.Div([
                                    html.Small("v1.1: ", className="text-muted"),
                                    html.Span(f"{corr_data['v11']:.3f}", className=f"text-{v11_color} fw-bold")
                                ], className="mb-1"),
                                html.Div([
                                    html.Small("v2.1: ", className="text-muted"),
                                    html.Span(f"{corr_data['v21']:.3f}", className=f"text-{v21_color} fw-bold")
                                ], className="mb-1"),
                                html.Div([
                                    html.Small("Improvement: ", className="text-muted"),
                                    html.Span(f"{improvement_icon} {corr_data['improvement']:+.3f}", 
                                             className=f"text-{improvement_color} fw-bold")
                                ])
                            ])
                        ])
                    ], md=6)
                )
        
        if not correlation_cards:
            return html.Div("Insufficient data for correlation analysis", className="alert alert-warning")
        
        return html.Div([
            html.P("Correlation: TAO scores vs price changes", className="text-muted mb-3"),
            dbc.Row(correlation_cards, className="mb-3"),
            html.Small(f"Data: {data_info}", className="text-muted d-block"),
            html.Small("1D: TAO score vs 1-day price change | 7D: TAO score vs 7-day price change", className="text-muted")
        ])
        
    except Exception as e:
        return html.Div(f"Error calculating correlations: {str(e)}", className="alert alert-danger")

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