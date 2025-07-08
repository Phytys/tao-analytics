"""
Correlation Analysis Page for TAO Analytics.
Dedicated page for clean statistical correlation analysis between metrics.
"""

import dash
from dash import html, dcc, Input, Output, callback, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.db import get_db, safe_query_execute
from models import MetricsSnap, SubnetMeta
from sqlalchemy import func, desc, and_, or_, text
import json
import os
from services.correlation_analysis import correlation_service
from services.cache_utils import cache_get, cache_set

def get_time_series_data(days_back=2, limit=5000):
    """Get time series data from metrics_snap table with highly optimized queries and caching."""
    cache_key = f'time_series_data_{days_back}_{limit}'
    
    # Try to get from cache first
    cached_result = cache_get(cache_key)
    if cached_result is not None:
        return cached_result
    
    session = get_db()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Use raw SQL for better performance with indexes
        from sqlalchemy import text
        
        # Optimized query for correlation analysis - reduced data load for Heroku
        sql = text("""
            SELECT 
                netuid, subnet_name, category, timestamp,
                -- Core performance metrics (most important for correlations)
                tao_score, stake_quality, buy_signal, emission_roi,
                -- Market dynamics (key metrics)
                market_cap_tao, fdv_tao, price_7d_change, flow_24h,
                -- Network health (essential metrics)
                active_validators, validator_util_pct, total_stake_tao,
                -- Stake distribution (important for analysis)
                stake_hhi, gini_coeff_top_100,
                -- Token flow (key indicators)
                reserve_momentum, tao_in, alpha_circ
            FROM metrics_snap 
            WHERE timestamp >= :cutoff_date
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        
        df = pd.read_sql(sql, session.bind, params={
            'cutoff_date': cutoff_date,
            'limit': limit
        })
        
        # Ensure timestamp is properly converted to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Cache the result for 5 minutes
        cache_set(cache_key, df, timeout=300)
        
        return df
    finally:
        session.close()

def get_subnet_list():
    """Get list of available subnets for dropdown with caching."""
    cache_key = 'subnet_list_correlation'
    
    # Try to get from cache first
    cached_result = cache_get(cache_key)
    if cached_result is not None:
        return cached_result
    
    session = get_db()
    try:
        # Get recent subnets with names
        from sqlalchemy import text
        
        # Use database-agnostic date arithmetic
        from config import ACTIVE_DATABASE_URL
        
        if 'postgresql' in ACTIVE_DATABASE_URL:
            # PostgreSQL syntax
            sql = text("""
                SELECT DISTINCT netuid, subnet_name, category
                FROM metrics_snap 
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                AND subnet_name IS NOT NULL
                ORDER BY netuid
            """)
        else:
            # SQLite syntax
            sql = text("""
                SELECT DISTINCT netuid, subnet_name, category
                FROM metrics_snap 
                WHERE timestamp >= datetime('now', '-7 days')
                AND subnet_name IS NOT NULL
                ORDER BY netuid
            """)
        
        result = session.execute(sql).fetchall()
        
        # Format for dropdown
        subnet_options = [
            {"label": "All Subnets (Network-wide)", "value": "all"}
        ]
        
        for row in result:
            label = f"Subnet {row.netuid}: {row.subnet_name}"
            if row.category:
                label += f" ({row.category})"
            subnet_options.append({
                "label": label,
                "value": str(row.netuid)
            })
        
        # Cache for 10 minutes
        cache_set(cache_key, subnet_options, timeout=600)
        
        return subnet_options
    finally:
        session.close()

def create_correlation_matrix(df, selected_subnet=None):
    """Create correlation matrix for comprehensive metrics analysis."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Determine analysis type and prepare data
    if selected_subnet and selected_subnet != "all":
        # Per-subnet analysis: use time-series data for one subnet
        subnet_data = df[df['netuid'] == int(selected_subnet)]
        if subnet_data.empty:
            return go.Figure().add_annotation(
                text=f"No data available for subnet {selected_subnet}", 
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )
        
        # Use all time-series data for the subnet
        analysis_data = subnet_data
        title = f"📊 Subnet {selected_subnet} Time-Series Correlation Matrix"
        subtitle = f"Showing how metrics correlate over time within this subnet"
    else:
        # Network-wide analysis: use latest data for each subnet
        latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
        analysis_data = latest
        title = "📊 Network-Wide Metric Correlation Matrix"
        subtitle = f"Showing how metrics correlate across {len(latest)} subnets"
    
    # Optimized metric selection for performance
    # Core performance metrics
    core_metrics = ['tao_score', 'stake_quality', 'buy_signal', 'emission_roi']
    
    # Market dynamics
    market_metrics = ['market_cap_tao', 'fdv_tao', 'price_7d_change', 'flow_24h']
    
    # Network health
    network_metrics = ['active_validators', 'validator_util_pct', 'total_stake_tao']
    
    # Stake distribution
    stake_metrics = ['stake_hhi', 'gini_coeff_top_100']
    
    # Token flow
    flow_metrics = ['reserve_momentum', 'tao_in', 'alpha_circ']
    
    # Combine all metric categories
    all_metrics = (core_metrics + market_metrics + network_metrics + 
                  stake_metrics + flow_metrics)
    
    # Filter to columns that exist in the data
    available_cols = [col for col in all_metrics if col in analysis_data.columns]
    
    if len(available_cols) < 2:
        return go.Figure().add_annotation(
            text="Insufficient data for correlation analysis", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Check if we have enough data points for meaningful correlations
    if len(analysis_data) < 5:
        return go.Figure().add_annotation(
            text=f"Insufficient data points ({len(analysis_data)}) for correlation analysis. Need at least 5 data points.", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate correlation matrix
    corr_matrix = analysis_data[available_cols].corr()
    
    # Create heatmap with enhanced styling
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu_r',
        zmid=0,
        text=np.round(corr_matrix.values, 3),
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
        hoverinfo='z+text'
    ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis_title="Metrics",
        yaxis_title="Metrics",
        annotations=[
            {
                'text': subtitle,
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.95,
                'showarrow': False,
                'font': {'size': 12, 'color': '#666666'}
            }
        ],
        width=None,
        height=600,
        margin=dict(l=50, r=50, t=100, b=50),
        font=dict(size=12),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig.update_xaxes(
        tickangle=45,
        tickfont=dict(size=10),
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray'
    )
    
    fig.update_yaxes(
        tickfont=dict(size=10),
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray'
    )
    
    return fig

def layout():
    """Layout for the correlation analysis page."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("📊 Correlation Analysis", className="text-center mb-4"),
                html.P(
                    "Analyze correlations between Bittensor subnet metrics to identify patterns and relationships.",
                    className="text-center text-muted mb-4"
                ),
                html.Div([
                    html.P([
                        html.Strong("💡 Tip: "),
                        "For individual subnet analysis, use longer time ranges (7+ days) to get meaningful time-series correlations."
                    ], className="text-center text-info small mb-0")
                ], id="analysis-tip")
            ])
        ]),
        
        # Controls Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Time Range:", className="form-label fw-bold"),
                                dcc.Dropdown(
                                    id="correlation-time-range",
                                    options=[
                                        {"label": "Last 1 Day", "value": 1},
                                        {"label": "Last 2 Days", "value": 2},
                                        {"label": "Last 7 Days", "value": 7},
                                        {"label": "Last 14 Days", "value": 14},
                                        {"label": "Last 30 Days", "value": 30},
                                        {"label": "Last 60 Days", "value": 60}
                                    ],
                                    value=2,
                                    clearable=False,
                                    className="mb-3"
                                )
                            ], width=6),
                            dbc.Col([
                                html.Label("Subnet Selection:", className="form-label fw-bold"),
                                dcc.Dropdown(
                                    id="subnet-selector",
                                    options=[{"label": "All Subnets (Network-wide)", "value": "all"}],
                                    value="all",
                                    clearable=False,
                                    placeholder="Loading subnets...",
                                    className="mb-3"
                                )
                            ], width=6)
                        ])
                    ])
                ], className="mb-4")
            ])
        ]),
        
        # Data Store for passing data between callbacks
        dcc.Store(id="correlation-data-store"),
        
        # Correlation Matrix
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("📈 Correlation Matrix", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            id="correlation-loading",
                            children=[
                                dcc.Graph(
                                    id="correlation-matrix",
                                    config={'displayModeBar': True, 'displaylogo': False}
                                )
                            ],
                            type="circle"
                        )
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Statistical Analysis Results
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("📊 Statistical Analysis", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="statistical-analysis-content")
                    ])
                ])
            ])
        ]),
        
        # Metrics Reference Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("📋 Metrics Reference", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="metrics-reference-table")
                    ])
                ])
            ])
        ])
        
    ], fluid=True, className="py-4")

# Callbacks for subnet list loading
@callback(
    Output("subnet-selector", "options"),
    Input("url", "pathname")
)
def load_subnet_options(pathname):
    """Load subnet options for dropdown."""
    if pathname != '/dash/correlation':
        raise PreventUpdate
    
    try:
        return get_subnet_list()
    except Exception as e:
        return [{"label": "All Subnets (Network-wide)", "value": "all"}]

# Callbacks for data loading
@callback(
    Output("correlation-data-store", "data"),
    Input("url", "pathname"),
    Input("correlation-time-range", "value"),
    Input("subnet-selector", "value")
)
def load_correlation_data(pathname, time_range, selected_subnet):
    """Load data for correlation analysis."""
    if pathname != '/dash/correlation':
        raise PreventUpdate
    
    if not time_range:
        time_range = 2
    
    try:
        df = get_time_series_data(time_range)
        return {
            'data': df.to_dict('records'),
            'time_range': time_range,
            'selected_subnet': selected_subnet,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'data': [],
            'error': str(e),
            'time_range': time_range,
            'selected_subnet': selected_subnet,
            'timestamp': datetime.now().isoformat()
        }

# Callbacks for correlation matrix
@callback(
    Output("correlation-matrix", "figure"),
    Input("correlation-data-store", "data")
)
def update_correlation_matrix(data):
    """Update correlation matrix using loaded data."""
    if not data or 'data' not in data or not data['data']:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    df = pd.DataFrame(data['data'])
    selected_subnet = data.get('selected_subnet', 'all')
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return create_correlation_matrix(df, selected_subnet)

# Callbacks for statistical analysis
@callback(
    Output("statistical-analysis-content", "children"),
    Input("correlation-data-store", "data"),
    Input("url", "pathname")
)
def update_statistical_analysis(data, pathname):
    """Update statistical analysis results."""
    if pathname != '/dash/correlation':
        return ""
    
    if not data or 'data' not in data or not data['data']:
        return html.P("No data available for analysis", className="text-muted")
    
    try:
        df = pd.DataFrame(data['data'])
        if df.empty:
            return html.P("No data available for analysis", className="text-muted")
        
        # Get analysis parameters
        time_range = data.get('time_range', 2)
        selected_subnet = data.get('selected_subnet', 'all')
        
        # Get correlation analysis
        analysis_result = correlation_service.get_correlation_analysis(time_range, selected_subnet)
        
        if not analysis_result['success']:
            return html.P(f"Analysis error: {analysis_result['error']}", className="text-danger")
        
        # Build analysis display
        analysis_content = []
        
        # Summary statistics
        summary = analysis_result['summary_stats']
        if summary:
            analysis_content.append(html.H5([
                "📈 Summary Statistics",
                html.I(
                    className="bi bi-info-circle ms-2",
                    id="summary-stats-tooltip",
                    style={"cursor": "pointer"}
                )
            ], className="mt-3 mb-2"))
            
            summary_items = []
            if 'total_subnets' in summary:
                summary_items.append(f"Total data points: {summary['total_subnets']}")
            if 'unique_subnets' in summary:
                summary_items.append(f"Unique subnets: {summary['unique_subnets']}")
            if 'metrics_analyzed' in analysis_result:
                summary_items.append(f"Metrics analyzed: {analysis_result['metrics_analyzed']}")
            
            if summary_items:
                analysis_content.append(html.Ul([
                    html.Li(item) for item in summary_items
                ], className="mb-3"))
        
        # Significant correlations
        significant_correlations = analysis_result['significant_correlations']
        if significant_correlations:
            analysis_content.append(html.H5([
                "🔗 Significant Correlations",
                html.I(
                    className="bi bi-info-circle ms-2",
                    id="significant-correlations-tooltip",
                    style={"cursor": "pointer"}
                )
            ], className="mt-3 mb-2"))
            
            corr_items = []
            for corr in significant_correlations[:10]:  # Show top 10
                strength_color = {
                    'Strong': 'text-success',
                    'Moderate': 'text-warning', 
                    'Weak': 'text-info'
                }.get(corr['strength'], 'text-muted')
                
                corr_items.append(html.Li([
                    html.Strong(f"{corr['metric1']} ↔ {corr['metric2']}"),
                    html.Br(),
                    html.Small([
                        f"r = {corr['correlation']}, ",
                        f"p = {corr['p_value']}, ",
                        f"n = {corr['sample_size']}, ",
                        html.Span(corr['strength'], className=strength_color)
                    ], className="text-muted")
                ], className="mb-2"))
            
            analysis_content.append(html.Ul(corr_items, className="mb-3"))
        
        # Outliers
        outliers = analysis_result['outliers']
        if outliers:
            analysis_content.append(html.H5([
                "⚠️ Statistical Outliers",
                html.I(
                    className="bi bi-info-circle ms-2",
                    id="statistical-outliers-tooltip",
                    style={"cursor": "pointer"}
                )
            ], className="mt-3 mb-2"))
            
            outlier_items = []
            for outlier in outliers[:8]:  # Show top 8
                outlier_items.append(html.Li([
                    html.Strong(f"{outlier['subnet_name']} (uid {outlier['netuid']})"),
                    html.Br(),
                    html.Small([
                        f"{outlier['metric']}: {outlier['value']} ",
                        f"(Z = {outlier['z_score']})"
                    ], className="text-muted")
                ], className="mb-2"))
            
            analysis_content.append(html.Ul(outlier_items, className="mb-3"))
        
        # Metric statistics
        key_metrics = ['tao_score', 'stake_quality', 'market_cap_tao']
        metric_stats = []
        
        for metric in key_metrics:
            if metric in summary:
                stats = summary[metric]
                metric_stats.append(html.Div([
                    html.H6(metric.replace('_', ' ').title(), className="mb-2"),
                    html.Small([
                        f"Mean: {stats['mean']}, ",
                        f"Std: {stats['std']}, ",
                        f"Range: {stats['min']} - {stats['max']}"
                    ], className="text-muted")
                ], className="mb-2"))
        
        if metric_stats:
            analysis_content.append(html.H5([
                "📊 Key Metric Statistics",
                html.I(
                    className="bi bi-info-circle ms-2",
                    id="key-metric-stats-tooltip",
                    style={"cursor": "pointer"}
                )
            ], className="mt-3 mb-2"))
            analysis_content.extend(metric_stats)
        
        # Add tooltips
        tooltips = [
            dbc.Tooltip(
                "Summary of the dataset including total data points, unique subnets analyzed, and date range of the data.",
                target="summary-stats-tooltip",
                placement="top",
                style={"fontSize": "14px", "maxWidth": "300px"}
            ),
            dbc.Tooltip(
                "Correlations with |r| ≥ 0.3 and p < 0.05. Shows relationships between metrics that are statistically significant. Strong: |r| ≥ 0.7, Moderate: |r| ≥ 0.5, Weak: |r| ≥ 0.3.",
                target="significant-correlations-tooltip",
                placement="top",
                style={"fontSize": "14px", "maxWidth": "350px"}
            ),
            dbc.Tooltip(
                "Subnets with metric values that are statistical outliers (|Z| > 2.0). These are extreme values that may indicate unusual performance, potential issues, or exceptional cases.",
                target="statistical-outliers-tooltip",
                placement="top",
                style={"fontSize": "14px", "maxWidth": "350px"}
            ),
            dbc.Tooltip(
                "Basic statistics (mean, standard deviation, range) for key metrics in the dataset. Shows the distribution and variability of important subnet metrics.",
                target="key-metric-stats-tooltip",
                placement="top",
                style={"fontSize": "14px", "maxWidth": "300px"}
            )
        ]
        
        return html.Div(analysis_content + tooltips)
        
    except Exception as e:
        return html.P(f"Error generating analysis: {str(e)}", className="text-danger")

def create_metrics_reference_table():
    """Create comprehensive metrics reference table."""
    
    # Define all metrics with their sources, descriptions, and analysis status
    metrics_data = [
        # Core Performance Metrics
        {
            'metric': 'tao_score',
            'description': 'Composite performance score (0-100) combining stake quality, consensus, and market factors',
            'source': 'Calculated',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'stake_quality',
            'description': 'Quality of stake distribution (0-100), lower HHI = better quality',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'buy_signal',
            'description': 'Investment signal (1-5) based on multiple factors',
            'source': 'Calculated',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'emission_roi',
            'description': 'Return on investment from daily emissions',
            'source': 'Calculated',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'trust_score',
            'description': 'Average trust score across validators',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Market & Price Metrics
        {
            'metric': 'market_cap_tao',
            'description': 'Market capitalization in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'fdv_tao',
            'description': 'Fully diluted valuation in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'price_tao',
            'description': 'Current price in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'price_1d_change',
            'description': '1-day price change percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'price_7d_change',
            'description': '7-day price change percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'price_30d_change',
            'description': '30-day price change percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'price_1h_change',
            'description': '1-hour price change percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'flow_24h',
            'description': '24-hour net volume flow in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'ath_60d',
            'description': '60-day all-time high price in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'atl_60d',
            'description': '60-day all-time low price in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Volume & Trading Metrics
        {
            'metric': 'buy_volume_tao_1d',
            'description': '24-hour buy volume in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'sell_volume_tao_1d',
            'description': '24-hour sell volume in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'total_volume_tao_1d',
            'description': '24-hour total volume in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'buy_vol_tao_1d',
            'description': '24-hour buy volume in TAO (alternative field)',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'sell_vol_tao_1d',
            'description': '24-hour sell volume in TAO (alternative field)',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'buy_sell_ratio',
            'description': 'Ratio of buy volume to sell volume',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'net_volume_tao_1h',
            'description': '1-hour net volume in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'net_volume_tao_7d',
            'description': '7-day net volume in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'total_volume_pct_change',
            'description': 'Percentage change in total volume',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Network & Validator Metrics
        {
            'metric': 'active_validators',
            'description': 'Number of active validators',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'validators_active',
            'description': 'Number of active validators (alternative field)',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'validator_util_pct',
            'description': 'Validator utilization percentage',
            'source': 'Calculated',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'total_stake_tao',
            'description': 'Total stake in TAO',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'max_validators',
            'description': 'Maximum number of validators allowed',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'uid_count',
            'description': 'Number of registered UIDs',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'active_stake_ratio',
            'description': 'Percentage of total stake on active validators',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Stake Distribution Metrics
        {
            'metric': 'stake_hhi',
            'description': 'Herfindahl-Hirschman Index for stake concentration (0-10,000)',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'gini_coeff_top_100',
            'description': 'Gini coefficient for top 100 stakeholders',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'hhi',
            'description': 'Herfindahl-Hirschman Index (alternative field)',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'stake_quality_rank_pct',
            'description': 'Stake quality ranking percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Token Flow & Emission Metrics
        {
            'metric': 'reserve_momentum',
            'description': 'Momentum of TAO reserves relative to market cap',
            'source': 'Calculated',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'tao_in',
            'description': 'TAO reserves in the subnet',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_circ',
            'description': 'Circulating Alpha tokens',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_prop',
            'description': 'Alpha proportion of total tokens',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'root_prop',
            'description': 'Root proportion of total tokens',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_in',
            'description': 'Alpha tokens flowing in',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_out',
            'description': 'Alpha tokens flowing out',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'emission_pct',
            'description': 'Emission percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_emitted_pct',
            'description': 'Percentage of Alpha tokens emitted',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Consensus & Incentive Metrics
        {
            'metric': 'consensus_alignment',
            'description': 'Percentage of validators within ±0.10 of mean consensus',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'mean_consensus',
            'description': 'Raw mean consensus value',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'pct_aligned',
            'description': 'Percentage of validators aligned with consensus',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'confidence',
            'description': 'Confidence level in consensus',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'mean_incentive',
            'description': 'Average incentive across UIDs',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'p95_incentive',
            'description': '95th percentile incentive',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Emission & PnL Metrics
        {
            'metric': 'emission_owner',
            'description': 'Owner share of emissions',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'emission_miners',
            'description': 'Miner share of emissions',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'emission_validators',
            'description': 'Validator share of emissions',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'total_emission_tao',
            'description': 'Total daily emission in TAO',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'tao_in_emission',
            'description': 'TAO portion of emissions',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'alpha_out_emission',
            'description': 'Alpha portion of emissions',
            'source': 'SDK',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'realized_pnl_tao',
            'description': 'Realized profit/loss in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'unrealized_pnl_tao',
            'description': 'Unrealized profit/loss in TAO',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Performance & Momentum Metrics
        {
            'metric': 'momentum_rank_pct',
            'description': 'Momentum ranking percentage',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        
        # Additional Volume Metrics
        {
            'metric': 'buy_volume_pct_change',
            'description': 'Percentage change in buy volume',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        },
        {
            'metric': 'sell_volume_pct_change',
            'description': 'Percentage change in sell volume',
            'source': 'TAO.app API',
            'analyzed': 'Yes',
            'in_correlation': 'Yes'
        }
    ]
    
    # Create table rows
    table_rows = []
    for metric in metrics_data:
        source_color = {
            'TAO.app API': 'text-primary',
            'SDK': 'text-success', 
            'Calculated': 'text-warning'
        }.get(metric['source'], 'text-muted')
        
        analyzed_badge = dbc.Badge(
            "✓" if metric['analyzed'] == 'Yes' else "✗",
            color="success" if metric['analyzed'] == 'Yes' else "secondary",
            className="me-2"
        )
        
        correlation_badge = dbc.Badge(
            "✓" if metric['in_correlation'] == 'Yes' else "✗",
            color="info" if metric['in_correlation'] == 'Yes' else "secondary",
            className="me-2"
        )
        
        table_rows.append(html.Tr([
            html.Td(html.Strong(metric['metric'])),
            html.Td(metric['description']),
            html.Td(html.Span(metric['source'], className=source_color)),
            html.Td([analyzed_badge, "Analyzed" if metric['analyzed'] == 'Yes' else "Not Analyzed"]),
            html.Td([correlation_badge, "Included" if metric['in_correlation'] == 'Yes' else "Excluded"])
        ]))
    
    # Create table
    table = dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("Metric"),
                html.Th("Description"),
                html.Th("Data Source"),
                html.Th("Analysis Status"),
                html.Th("Correlation Matrix")
            ])
        ]),
        html.Tbody(table_rows)
    ], striped=True, bordered=True, hover=True, responsive=True, className="small")
    
    return table

# Callback for metrics reference table
@callback(
    Output("metrics-reference-table", "children"),
    Input("url", "pathname")
)
def update_metrics_reference_table(pathname):
    """Update metrics reference table."""
    if pathname != '/dash/correlation':
        return ""
    
    try:
        table = create_metrics_reference_table()
        return table
    except Exception as e:
        return html.P(f"Error loading metrics table: {str(e)}", className="text-danger")

def register_callbacks(dash_app):
    """Register callbacks for the correlation page."""
    pass 