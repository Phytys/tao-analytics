"""
Dynamic Insights Dashboard - Time Series Analytics for Bittensor Network
Leverages rich metrics_snap data for comprehensive network analysis and trends.
"""

import dash
from dash import html, dcc, Input, Output, callback, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.db import get_db
from models import MetricsSnap, SubnetMeta
from sqlalchemy import func, desc, and_, or_, text
import json

def get_time_series_data(days_back=30):
    """Get time series data from metrics_snap table with flexible date range."""
    session = get_db()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        query = session.query(MetricsSnap).filter(
            MetricsSnap.timestamp >= cutoff_date
        ).order_by(MetricsSnap.timestamp.desc())
        
        df = pd.read_sql(query.statement, session.bind)
        
        # Ensure timestamp is properly converted to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    finally:
        session.close()

def get_network_summary_stats():
    """Get comprehensive network summary statistics."""
    session = get_db()
    try:
        # Get latest data for each subnet
        latest_query = session.query(
            MetricsSnap.netuid,
            MetricsSnap.subnet_name,
            MetricsSnap.category,
            MetricsSnap.tao_score,
            MetricsSnap.stake_quality,
            MetricsSnap.validator_util_pct,
            MetricsSnap.market_cap_tao,
            MetricsSnap.flow_24h,
            MetricsSnap.price_7d_change,
            MetricsSnap.active_validators,
            MetricsSnap.total_stake_tao,
            MetricsSnap.buy_signal,
            func.max(MetricsSnap.timestamp).label('latest_timestamp')
        ).group_by(
            MetricsSnap.netuid,
            MetricsSnap.subnet_name,
            MetricsSnap.category,
            MetricsSnap.tao_score,
            MetricsSnap.stake_quality,
            MetricsSnap.validator_util_pct,
            MetricsSnap.market_cap_tao,
            MetricsSnap.flow_24h,
            MetricsSnap.price_7d_change,
            MetricsSnap.active_validators,
            MetricsSnap.total_stake_tao,
            MetricsSnap.buy_signal
        ).subquery()
        
        latest_df = pd.read_sql(session.query(latest_query).statement, session.bind)
        
        # Calculate summary stats
        stats = {
            'total_subnets': len(latest_df),
            'total_market_cap_tao': latest_df['market_cap_tao'].sum(),
            'total_stake_tao': latest_df['total_stake_tao'].sum(),
            'avg_tao_score': latest_df['tao_score'].mean(),
            'avg_stake_quality': latest_df['stake_quality'].mean(),
            'high_performers': len(latest_df[latest_df['tao_score'] >= 70]),
            'improving_subnets': len(latest_df[latest_df['price_7d_change'] > 0]),
            'strong_buy_signals': len(latest_df[latest_df['buy_signal'] >= 4]),
            'total_validators': latest_df['active_validators'].sum(),
            'avg_validator_util': latest_df['validator_util_pct'].mean(),
            'categories': latest_df['category'].nunique(),
            'data_points': session.query(MetricsSnap).count(),
            'date_range': f"{session.query(func.min(MetricsSnap.timestamp)).scalar()} to {session.query(func.max(MetricsSnap.timestamp)).scalar()}"
        }
        
        return stats, latest_df
    finally:
        session.close()

def create_metric_trend_chart(df, metric, title, color='#3e6ae1', aggregation='mean'):
    """Create a trend chart for any metric with flexible aggregation."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Aggregate by date
    if aggregation == 'mean':
        daily_data = df.groupby(df['timestamp'].dt.date)[metric].mean().reset_index()
    elif aggregation == 'sum':
        daily_data = df.groupby(df['timestamp'].dt.date)[metric].sum().reset_index()
    elif aggregation == 'median':
        daily_data = df.groupby(df['timestamp'].dt.date)[metric].median().reset_index()
    else:
        daily_data = df.groupby(df['timestamp'].dt.date)[metric].mean().reset_index()
    
    daily_data['timestamp'] = pd.to_datetime(daily_data['timestamp'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_data['timestamp'],
        y=daily_data[metric],
        mode='lines+markers',
        name=title,
        line=dict(color=color, width=3),
        marker=dict(size=6, color=color),
        hovertemplate='<b>%{x}</b><br>' + title + ': %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=title,
        hovermode='x unified',
        showlegend=False,
        height=300,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

def create_category_comparison(df, metric, title):
    """Create category comparison chart for any metric."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Get latest data for each subnet
    latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
    
    # Calculate category averages
    category_metrics = latest.groupby('category')[metric].mean().round(2).sort_values(ascending=False)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=category_metrics.values,
        y=category_metrics.index,
        orientation='h',
        marker_color='#3e6ae1',
        hovertemplate='<b>%{y}</b><br>' + title + ': %{x:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f"{title} by Category",
        xaxis_title=title,
        yaxis_title="Category",
        height=400,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def create_subnet_performance_chart(df, metric, title, top_n=10):
    """Create top/bottom subnet performance chart."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Get latest data for each subnet
    latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
    
    # Get top performers
    top_performers = latest.nlargest(top_n, metric)[['subnet_name', 'netuid', metric, 'category']]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_performers[metric],
        y=[f"{row['subnet_name']} ({row['netuid']})" for _, row in top_performers.iterrows()],
        orientation='h',
        marker_color='#28a745',
        hovertemplate='<b>%{y}</b><br>' + title + ': %{x:.2f}<br>Category: %{customdata}<extra></extra>',
        customdata=top_performers['category']
    ))
    
    fig.update_layout(
        title=f"Top {top_n} Subnets by {title}",
        xaxis_title=title,
        yaxis_title="Subnet",
        height=400,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def create_improvement_tracker(df, days_back=30):
    """Create subnet improvement tracking over specified period."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate improvement for each subnet
    improvements = []
    
    for netuid in df['netuid'].unique():
        subnet_data = df[df['netuid'] == netuid].sort_values('timestamp')
        if len(subnet_data) >= 2:
            first_score = subnet_data.iloc[0]['tao_score']
            last_score = subnet_data.iloc[-1]['tao_score']
            improvement = last_score - first_score
            
            if abs(improvement) >= 0.1:  # Minimum change threshold
                improvements.append({
                    'netuid': netuid,
                    'subnet_name': subnet_data.iloc[0]['subnet_name'],
                    'category': subnet_data.iloc[0]['category'],
                    'improvement': improvement,
                    'start_score': first_score,
                    'end_score': last_score,
                    'days_tracked': (subnet_data.iloc[-1]['timestamp'] - subnet_data.iloc[0]['timestamp']).days
                })
    
    if not improvements:
        return go.Figure().add_annotation(
            text=f"No improvement data available<br>Need at least 2 data points per subnet in last {days_back} days", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
    
    improvements_df = pd.DataFrame(improvements)
    top_improvers = improvements_df.nlargest(10, 'improvement')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_improvers['improvement'],
        y=[f"{row['subnet_name']} ({row['netuid']})" for _, row in top_improvers.iterrows()],
        orientation='h',
        marker_color=['#28a745' if x > 0 else '#dc3545' for x in top_improvers['improvement']],
        hovertemplate='<b>%{y}</b><br>Improvement: %{x:.1f} points<br>From: %{customdata[0]:.1f} → To: %{customdata[1]:.1f}<br>Days: %{customdata[2]}<extra></extra>',
        customdata=list(zip(top_improvers['start_score'], top_improvers['end_score'], top_improvers['days_tracked']))
    ))
    
    fig.update_layout(
        title=f"Top 10 Most Improved Subnets (Last {days_back} Days)",
        xaxis_title="TAO-Score Improvement",
        yaxis_title="Subnet",
        height=400,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def create_correlation_matrix(df):
    """Create correlation matrix for key metrics."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Get latest data for each subnet
    latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
    
    # Select numeric columns for correlation
    numeric_cols = ['tao_score', 'stake_quality', 'validator_util_pct', 'market_cap_tao', 
                   'flow_24h', 'price_7d_change', 'active_validators', 'total_stake_tao']
    
    # Filter to columns that exist in the data
    available_cols = [col for col in numeric_cols if col in latest.columns]
    
    if len(available_cols) < 2:
        return go.Figure().add_annotation(
            text="Insufficient data for correlation analysis", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    corr_matrix = latest[available_cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        hovertemplate='<b>%{y} vs %{x}</b><br>Correlation: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Metric Correlation Matrix",
        height=500,
        xaxis_title="Metrics",
        yaxis_title="Metrics"
    )
    
    return fig

# Available metrics for dynamic selection (static - no DB calls)
AVAILABLE_METRICS = {
    'tao_score': 'TAO-Score',
    'stake_quality': 'Stake Quality',
    'validator_util_pct': 'Validator Utilization (%)',
    'market_cap_tao': 'Market Cap (TAO)',
    'flow_24h': '24h Flow (TAO)',
    'price_7d_change': '7-Day Price Change (%)',
    'active_validators': 'Active Validators',
    'total_stake_tao': 'Total Stake (TAO)',
    'buy_signal': 'Buy Signal',
    'consensus_alignment': 'Consensus Alignment (%)',
    'emission_roi': 'Emission ROI',
    'stake_hhi': 'Stake HHI'
}

def layout():
    """Create the insights page layout with lazy data loading."""
    return html.Div([
        # Header
        dbc.Card([
            dbc.CardBody([
                html.H1("📊 Dynamic Network Insights", className="dashboard-title mb-3"),
                html.P([
                    "Comprehensive time series analytics leveraging our rich metrics database. ",
                    "Track network trends, subnet performance, and discover investment opportunities ",
                    "with interactive charts and dynamic filtering."
                ], className="text-muted mb-0")
            ])
        ], className="mb-4"),
        
        # Network Overview Cards (will be populated by callback)
        dbc.Card([
            dbc.CardHeader([
                html.H4("Network Overview", className="mb-0"),
                html.I(className="bi bi-info-circle ms-2", id="overview-tooltip")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="total-subnets", className="text-primary"),
                                html.P("Active Subnets", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="total-market-cap", className="text-success"),
                                html.P("Total Market Cap (TAO)", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="avg-tao-score", className="text-warning"),
                                html.P("Avg TAO-Score", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="high-performers", className="text-info"),
                                html.P("High Performers (≥70)", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="strong-buy-signals", className="text-danger"),
                                html.P("Strong Buy Signals (≥4)", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="categories", className="text-secondary"),
                                html.P("Categories", className="text-muted mb-0")
                            ])
                        ], className="text-center")
                    ], width=2),
                ], className="mb-3"),
                html.Small(id="data-info", className="text-muted")
            ])
        ], className="mb-4"),
        
        # SECTION 1: Custom Trend Analysis
        dbc.Card([
            dbc.CardHeader([
                html.H4("📈 Custom Trend Analysis", className="mb-0"),
                html.I(className="bi bi-graph-up ms-2", id="trend-tooltip")
            ]),
            dbc.CardBody([
                # Controls for this section
                dbc.Row([
                    dbc.Col([
                        html.Label("Time Range", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-time-range",
                            options=[
                                {"label": "Last 7 Days", "value": 7},
                                {"label": "Last 14 Days", "value": 14},
                                {"label": "Last 30 Days", "value": 30},
                                {"label": "Last 60 Days", "value": 60},
                                {"label": "All Available", "value": 365}
                            ],
                            value=30,
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Metric to Track", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Aggregation Method", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-aggregation",
                            options=[
                                {"label": "Average", "value": "mean"},
                                {"label": "Sum", "value": "sum"},
                                {"label": "Median", "value": "median"}
                            ],
                            value="mean",
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Filter by Category", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False
                        )
                    ], width=3),
                ], className="mb-4"),
                # Chart for this section
                dcc.Graph(id="custom-trend-chart", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # SECTION 2: Category Performance Analysis
        dbc.Card([
            dbc.CardHeader([
                html.H4("🏷️ Category Performance Analysis", className="mb-0"),
                html.I(className="bi bi-pie-chart ms-2", id="category-tooltip")
            ]),
            dbc.CardBody([
                # Controls for this section
                dbc.Row([
                    dbc.Col([
                        html.Label("Time Range", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="category-time-range",
                            options=[
                                {"label": "Last 7 Days", "value": 7},
                                {"label": "Last 14 Days", "value": 14},
                                {"label": "Last 30 Days", "value": 30},
                                {"label": "Last 60 Days", "value": 60},
                                {"label": "All Available", "value": 365}
                            ],
                            value=30,
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Metric to Compare", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="category-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Filter by Category", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False
                        )
                    ], width=4),
                ], className="mb-4"),
                # Chart for this section
                dcc.Graph(id="category-performance-chart", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # SECTION 3: Top Performers Analysis
        dbc.Card([
            dbc.CardHeader([
                html.H4("🏆 Top Performers Analysis", className="mb-0"),
                html.I(className="bi bi-trophy ms-2", id="performers-tooltip")
            ]),
            dbc.CardBody([
                # Controls for this section
                dbc.Row([
                    dbc.Col([
                        html.Label("Time Range", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="performers-time-range",
                            options=[
                                {"label": "Last 7 Days", "value": 7},
                                {"label": "Last 14 Days", "value": 14},
                                {"label": "Last 30 Days", "value": 30},
                                {"label": "Last 60 Days", "value": 60},
                                {"label": "All Available", "value": 365}
                            ],
                            value=30,
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Performance Metric", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="performers-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Filter by Category", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="performers-category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False
                        )
                    ], width=4),
                ], className="mb-4"),
                # Chart for this section
                dcc.Graph(id="top-performers-chart", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # SECTION 4: Improvement Tracking
        dbc.Card([
            dbc.CardHeader([
                html.H4("📈 Improvement Tracking", className="mb-0"),
                html.I(className="bi bi-arrow-up-circle ms-2", id="improvement-tooltip")
            ]),
            dbc.CardBody([
                # Controls for this section
                dbc.Row([
                    dbc.Col([
                        html.Label("Time Range for Improvement Analysis", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="improvement-time-range",
                            options=[
                                {"label": "Last 7 Days", "value": 7},
                                {"label": "Last 14 Days", "value": 14},
                                {"label": "Last 30 Days", "value": 30},
                                {"label": "Last 60 Days", "value": 60},
                                {"label": "All Available", "value": 365}
                            ],
                            value=30,
                            clearable=False
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Minimum Improvement Threshold", className="form-label fw-bold"),
                        dcc.Slider(
                            id="improvement-threshold",
                            min=0.1,
                            max=5.0,
                            step=0.1,
                            value=0.1,
                            marks={0.1: '0.1', 1.0: '1.0', 2.0: '2.0', 3.0: '3.0', 4.0: '4.0', 5.0: '5.0'},
                            tooltip={"placement": "bottom", "always_visible": False}
                        )
                    ], width=6),
                ], className="mb-4"),
                # Chart for this section
                dcc.Graph(id="improvement-tracking-chart", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # SECTION 5: Fixed Network Trends (Static)
        dbc.Card([
            dbc.CardHeader([
                html.H4("📊 Fixed Network Trends", className="mb-0"),
                html.I(className="bi bi-graph-up ms-2", id="fixed-trends-tooltip")
            ]),
            dbc.CardBody([
                html.P("These charts show key network metrics over time (last 30 days):", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id="stake-quality-trend", config={'displayModeBar': False})
                    ], width=6),
                    dbc.Col([
                        dcc.Graph(id="market-cap-trend", config={'displayModeBar': False})
                    ], width=6),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id="flow-trend", config={'displayModeBar': False})
                    ], width=12),
                ])
            ])
        ], className="mb-4"),
        
        # SECTION 6: Correlation Analysis (Static)
        dbc.Card([
            dbc.CardHeader([
                html.H4("🔗 Metric Correlations", className="mb-0"),
                html.I(className="bi bi-diagram-3 ms-2", id="correlation-tooltip")
            ]),
            dbc.CardBody([
                html.P("Correlation matrix showing relationships between different metrics:", className="text-muted mb-3"),
                dcc.Graph(id="correlation-matrix", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # Tooltips
        dbc.Tooltip(
            "Overview of key network metrics including total subnets, market cap, average TAO-Score, "
            "high performers, strong buy signals, and category diversity.",
            target="overview-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "Create custom trend charts by selecting any metric, time range, aggregation method, and category filter. "
            "Perfect for tracking specific metrics over time.",
            target="trend-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "Compare subnet categories by any metric. Helps identify which types of AI services are performing best "
            "and which categories might be undervalued.",
            target="category-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "View top-performing subnets by any selected metric. These represent the best-performing subnets "
            "in the network for your chosen criteria.",
            target="performers-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "Track subnets showing the most improvement in TAO-Score over the selected time period. "
            "These represent emerging opportunities and subnets that are actively improving.",
            target="improvement-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "Fixed network trends showing key metrics over time. These provide a consistent baseline "
            "for understanding network health and growth.",
            target="fixed-trends-tooltip",
            placement="top"
        ),
        dbc.Tooltip(
            "Correlation matrix showing relationships between different metrics. "
            "Helps understand which factors influence each other.",
            target="correlation-tooltip",
            placement="top"
        ),
        
        # Store for dynamic data
        dcc.Store(id="trend-data-store"),
        dcc.Store(id="category-data-store"),
        dcc.Store(id="performers-data-store"),
        dcc.Store(id="improvement-data-store"),
        dcc.Store(id="overview-data-store"),
        dcc.Store(id="fixed-trends-data-store"),
        dcc.Store(id="correlation-data-store"),
    ])

# Callbacks for network overview
@callback(
    Output("overview-data-store", "data"),
    Input("url", "pathname")
)
def load_overview_data(pathname):
    """Load network overview data when page loads."""
    if pathname == "/dash/insights":
        try:
            stats, latest_df = get_network_summary_stats()
            return {
                'stats': stats,
                'categories': sorted(latest_df['category'].unique().tolist()) if not latest_df.empty else []
            }
        except Exception as e:
            return {'stats': {}, 'categories': []}
    return {'stats': {}, 'categories': []}

@callback(
    Output("total-subnets", "children"),
    Output("total-market-cap", "children"),
    Output("avg-tao-score", "children"),
    Output("high-performers", "children"),
    Output("strong-buy-signals", "children"),
    Output("categories", "children"),
    Output("data-info", "children"),
    Input("overview-data-store", "data")
)
def update_overview_cards(data):
    """Update overview cards with loaded data."""
    if not data or 'stats' not in data:
        return "0", "0", "0.0", "0", "0", "0", "No data available"
    
    stats = data['stats']
    return (
        f"{stats.get('total_subnets', 0)}",
        f"{stats.get('total_market_cap_tao', 0):,.0f}",
        f"{stats.get('avg_tao_score', 0):.1f}",
        f"{stats.get('high_performers', 0)}",
        f"{stats.get('strong_buy_signals', 0)}",
        f"{stats.get('categories', 0)}",
        f"Data: {stats.get('data_points', 0):,} points | Range: {stats.get('date_range', 'N/A')}"
    )

@callback(
    Output("trend-category-filter", "options"),
    Output("category-filter", "options"),
    Output("performers-category-filter", "options"),
    Input("overview-data-store", "data")
)
def update_category_filters(data):
    """Update category filter options."""
    if not data or 'categories' not in data:
        return [{"label": "All Categories", "value": "All"}], [{"label": "All Categories", "value": "All"}], [{"label": "All Categories", "value": "All"}]
    
    categories = data['categories']
    category_options = [{"label": "All Categories", "value": "All"}] + [{"label": cat, "value": cat} for cat in categories if cat]
    return category_options, category_options, category_options

# Callbacks for SECTION 1: Custom Trend Analysis
@callback(
    Output("trend-data-store", "data"),
    Input("trend-time-range", "value")
)
def update_trend_data(time_range):
    """Update data for trend analysis."""
    df = get_time_series_data(time_range)
    return df.to_dict('records')

@callback(
    Output("custom-trend-chart", "figure"),
    Input("trend-data-store", "data"),
    Input("trend-metric", "value"),
    Input("trend-aggregation", "value"),
    Input("trend-category-filter", "value")
)
def update_custom_trend_chart(data, metric, aggregation, category):
    """Update custom trend chart."""
    if not data:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Apply category filter
    if category != "All":
        df = df[df['category'] == category]
    
    if df.empty:
        return go.Figure().add_annotation(text="No data available for selected filters", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    return create_metric_trend_chart(df, metric, f"{AVAILABLE_METRICS[metric]} Over Time", aggregation=aggregation)

# Callbacks for SECTION 2: Category Performance Analysis
@callback(
    Output("category-data-store", "data"),
    Input("category-time-range", "value")
)
def update_category_data(time_range):
    """Update data for category analysis."""
    df = get_time_series_data(time_range)
    return df.to_dict('records')

@callback(
    Output("category-performance-chart", "figure"),
    Input("category-data-store", "data"),
    Input("category-metric", "value"),
    Input("category-filter", "value")
)
def update_category_performance_chart(data, metric, category):
    """Update category performance chart."""
    if not data:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Apply category filter
    if category != "All":
        df = df[df['category'] == category]
    
    if df.empty:
        return go.Figure().add_annotation(text="No data available for selected category", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    return create_category_comparison(df, metric, AVAILABLE_METRICS[metric])

# Callbacks for SECTION 3: Top Performers Analysis
@callback(
    Output("performers-data-store", "data"),
    Input("performers-time-range", "value")
)
def update_performers_data(time_range):
    """Update data for performers analysis."""
    df = get_time_series_data(time_range)
    return df.to_dict('records')

@callback(
    Output("top-performers-chart", "figure"),
    Input("performers-data-store", "data"),
    Input("performers-metric", "value"),
    Input("performers-category-filter", "value")
)
def update_top_performers_chart(data, metric, category):
    """Update top performers chart."""
    if not data:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Apply category filter
    if category != "All":
        df = df[df['category'] == category]
    
    if df.empty:
        return go.Figure().add_annotation(text="No data available for selected category", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    return create_subnet_performance_chart(df, metric, AVAILABLE_METRICS[metric])

# Callbacks for SECTION 4: Improvement Tracking
@callback(
    Output("improvement-data-store", "data"),
    Input("improvement-time-range", "value")
)
def update_improvement_data(time_range):
    """Update data for improvement analysis."""
    df = get_time_series_data(time_range)
    return df.to_dict('records')

@callback(
    Output("improvement-tracking-chart", "figure"),
    Input("improvement-data-store", "data"),
    Input("improvement-time-range", "value"),
    Input("improvement-threshold", "value")
)
def update_improvement_tracking_chart(data, time_range, threshold):
    """Update improvement tracking chart."""
    if not data:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return create_improvement_tracker(df, time_range)

# Callbacks for SECTION 5: Fixed Network Trends
@callback(
    Output("fixed-trends-data-store", "data"),
    Input("url", "pathname")
)
def load_fixed_trends_data(pathname):
    """Load fixed trends data when page loads."""
    if pathname == "/dash/insights":
        try:
            df_30d = get_time_series_data(30)
            return df_30d.to_dict('records')
        except Exception as e:
            return []
    return []

@callback(
    Output("stake-quality-trend", "figure"),
    Output("market-cap-trend", "figure"),
    Output("flow-trend", "figure"),
    Input("fixed-trends-data-store", "data")
)
def update_fixed_trends(data):
    """Update fixed trend charts."""
    if not data:
        empty_fig = go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return empty_fig, empty_fig, empty_fig
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    stake_quality_trend = create_metric_trend_chart(df, 'stake_quality', 'Average Stake Quality Over Time', '#28a745')
    market_cap_trend = create_metric_trend_chart(df, 'market_cap_tao', 'Total Market Cap (TAO) Over Time', '#ffc107', 'sum')
    flow_trend = create_metric_trend_chart(df, 'flow_24h', 'Total 24h Flow (TAO) Over Time', '#dc3545', 'sum')
    
    return stake_quality_trend, market_cap_trend, flow_trend

# Callbacks for SECTION 6: Correlation Analysis
@callback(
    Output("correlation-data-store", "data"),
    Input("url", "pathname")
)
def load_correlation_data(pathname):
    """Load correlation data when page loads."""
    if pathname == "/dash/insights":
        try:
            df_30d = get_time_series_data(30)
            return df_30d.to_dict('records')
        except Exception as e:
            return []
    return []

@callback(
    Output("correlation-matrix", "figure"),
    Input("correlation-data-store", "data")
)
def update_correlation_matrix(data):
    """Update correlation matrix."""
    if not data:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(data)
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return create_correlation_matrix(df)

def register_callbacks(dash_app):
    """Register callbacks for the insights page."""
    pass 