"""
Dynamic Insights Dashboard - Time Series Analytics for Bittensor Network
Leverages rich metrics_snap data for comprehensive network analysis and trends.
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
from config import TAO_SCORE_COLUMN
import json
import os

from services.cache_utils import cache_get, cache_set

def get_time_series_data(days_back=30, limit=5000):
    """Get time series data using the same data source as other charts for consistency."""
    cache_key = f'time_series_data_{days_back}_{limit}'
    
    # Try to get from cache first
    cached_result = cache_get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Use the same data source as other charts for consistency
        from services.db import load_screener_frame
        
        # Get the same data that other charts use
        df = load_screener_frame()
        
        # Since load_screener_frame() returns current data (not time series),
        # we need to get historical data from metrics_snap for time series charts
        # But we'll use the same column structure and TAO score approach
        
        session = get_db()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Use raw SQL for better performance with indexes
            from sqlalchemy import text
            
            # Query using the configured TAO score column (exclude NULL values)
            sql = text(f"""
                SELECT 
                    netuid, subnet_name, category, timestamp,
                    -- Core performance metrics (use configured TAO score, exclude NULL)
                    {TAO_SCORE_COLUMN} as tao_score, 
                    stake_quality, buy_signal, emission_roi,
                    -- Market dynamics
                    market_cap_tao, fdv_tao, price_7d_change, price_1d_change, 
                    flow_24h, buy_sell_ratio, total_volume_tao_1d,
                    -- Network health & activity
                    active_validators, validator_util_pct, consensus_alignment,
                    active_stake_ratio, uid_count, max_validators,
                    -- Stake distribution & quality
                    total_stake_tao, stake_hhi, gini_coeff_top_100, hhi,
                    -- Token flow & momentum
                    reserve_momentum, tao_in, alpha_circ, alpha_prop, root_prop,
                    -- Performance & ranking
                    stake_quality_rank_pct, momentum_rank_pct,
                    realized_pnl_tao, unrealized_pnl_tao
                FROM metrics_snap 
                WHERE timestamp >= :cutoff_date
                AND {TAO_SCORE_COLUMN} IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            time_series_df = pd.read_sql(sql, session.bind, params={
                'cutoff_date': cutoff_date,
                'limit': limit
            })
            
            # Ensure timestamp is properly converted to datetime
            if 'timestamp' in time_series_df.columns:
                time_series_df['timestamp'] = pd.to_datetime(time_series_df['timestamp'])
            
            # Cache the result for 5 minutes
            cache_set(cache_key, time_series_df, timeout=300)
            
            return time_series_df
        finally:
            session.close()
    except Exception as e:
        print(f"Error in get_time_series_data: {e}")
        # Return empty DataFrame if there's an error
        return pd.DataFrame()

def get_network_summary_stats():
    """Get comprehensive network summary statistics using the same data source as other pages."""
    cache_key = 'network_summary_stats'
    
    # Try to get from cache first
    cached_result = cache_get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Use the same data source as the screener page for consistency
        from services.db import load_screener_frame
        
        # Get the same data that the screener page uses
        df = load_screener_frame()
        
        # Calculate summary stats from the complete dataset
        stats = {
            'total_subnets': len(df),
            'total_market_cap_tao': df['market_cap_tao'].sum() if 'market_cap_tao' in df.columns else 0,
            'total_stake_tao': df['total_stake_tao'].sum() if 'total_stake_tao' in df.columns else 0,
            'avg_tao_score': df['tao_score'].mean() if 'tao_score' in df.columns else 0,
            'avg_stake_quality': df['stake_quality'].mean() if 'stake_quality' in df.columns else 0,
            'high_performers': len(df[df['tao_score'] >= 70]) if 'tao_score' in df.columns else 0,
            'improving_subnets': len(df[df['flow_24h'] > 0]) if 'flow_24h' in df.columns else 0,
            'strong_buy_signals': len(df[df['buy_signal'] >= 4]) if 'buy_signal' in df.columns else 0,
            'total_validators': df['active_validators'].sum() if 'active_validators' in df.columns else 0,
            'avg_validator_util': df['validator_util_pct'].mean() if 'validator_util_pct' in df.columns else 0,
            'categories': df['primary_category'].nunique() if 'primary_category' in df.columns else 0,
            'data_points': 'All active subnets',
            'date_range': 'Current data'
        }
        
        result = (stats, df)
        
        # Cache the result for 5 minutes
        cache_set(cache_key, result, timeout=300)
        
        return result
    except Exception as e:
        print(f"Error in get_network_summary_stats: {e}")
        # Return empty stats if there's an error
        return ({'total_subnets': 0, 'total_market_cap_tao': 0, 'avg_tao_score': 0, 'high_performers': 0, 'strong_buy_signals': 0, 'categories': 0, 'data_points': 'Error loading data', 'date_range': 'N/A'}, pd.DataFrame())

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





# Available metrics for dynamic selection (static - no DB calls)
AVAILABLE_METRICS = {
    # Core performance metrics
    'tao_score': 'TAO-Score',
    'stake_quality': 'Stake Quality',
    'buy_signal': 'Buy Signal',
    'emission_roi': 'Emission ROI',
    
    # Market dynamics
    'market_cap_tao': 'Market Cap (TAO)',
    'fdv_tao': 'Fully Diluted Valuation (TAO)',
    'price_7d_change': '7-Day Price Change (%)',
    'price_1d_change': '1-Day Price Change (%)',
    'flow_24h': '24h Flow (TAO)',
    'buy_sell_ratio': 'Buy/Sell Ratio',
    'total_volume_tao_1d': '24h Total Volume (TAO)',
    
    # Network health & activity
    'active_validators': 'Active Validators',
    'validator_util_pct': 'Validator Utilization (%)',
    'consensus_alignment': 'Consensus Alignment (%)',
    'active_stake_ratio': 'Active Stake Ratio (%)',
    'uid_count': 'Registered UIDs',
    'max_validators': 'Max Validators',
    
    # Stake distribution & quality
    'total_stake_tao': 'Total Stake (TAO)',
    'stake_hhi': 'Stake HHI',
    'gini_coeff_top_100': 'Gini Coefficient (Top 100)',
    'hhi': 'HHI',
    
    # Token flow & momentum
    'reserve_momentum': 'Reserve Momentum',
    'tao_in': 'TAO Reserves',
    'alpha_circ': 'Circulating Alpha',
    'alpha_prop': 'Alpha Proportion',
    'root_prop': 'Root Proportion',
    
    # Performance & ranking
    'stake_quality_rank_pct': 'Stake Quality Rank (%)',
    'momentum_rank_pct': 'Momentum Rank (%)',
    'realized_pnl_tao': 'Realized PnL (TAO)',
    'unrealized_pnl_tao': 'Unrealized PnL (TAO)'
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
                    "with interactive charts and dynamic filtering. ",
                    html.A("Correlation analysis and GPT insights", href="/dash/correlation", className="text-primary"),
                    " are now available on a dedicated page."
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
                                html.P("Active Subnets", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="subnets-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="total-market-cap", className="text-success"),
                                html.P("Total Market Cap (TAO)", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="market-cap-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="avg-tao-score", className="text-warning"),
                                html.P("Avg TAO-Score", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="tao-score-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="high-performers", className="text-info"),
                                html.P("High Performers (≥70)", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="performers-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="strong-buy-signals", className="text-danger"),
                                html.P("Strong Buy Signals (≥4)", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="buy-signals-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(id="categories", className="text-secondary"),
                                html.P("Categories", className="text-muted mb-0"),
                                html.I(className="bi bi-info-circle ms-1", id="categories-tooltip", style={"cursor": "pointer"})
                            ])
                        ], className="text-center")
                    ], width=2),
                ], className="mb-3"),
                html.Small(id="data-info", className="text-muted")
            ])
        ], className="mb-4"),
        
        # Global Time Range Control
        dbc.Card([
            dbc.CardHeader([
                html.H4("⏰ Global Time Range Control", className="mb-0"),
                html.I(className="bi bi-clock ms-2", id="time-range-tooltip")
            ]),
            dbc.CardBody([
                html.P("Set the time range for all charts below. Changing this will update all sections simultaneously:", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            id="shared-time-range",
                            options=[
                                {"label": "Last 3 Days", "value": 3},
                                {"label": "Last 7 Days", "value": 7},
                                {"label": "Last 14 Days", "value": 14},
                                {"label": "Last 30 Days", "value": 30},
                                {"label": "Last 60 Days", "value": 60},
                                {"label": "All Available", "value": 365}
                            ],
                            value=3,
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=4),
                ])
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
                        html.Label([
                            "Metric to Track",
                            html.I(className="bi bi-info-circle ms-1", id="trend-metric-tooltip", style={"cursor": "pointer"})
                        ], className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label([
                            "Aggregation Method",
                            html.I(className="bi bi-info-circle ms-1", id="trend-aggregation-tooltip", style={"cursor": "pointer"})
                        ], className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-aggregation",
                            options=[
                                {"label": "Average", "value": "mean"},
                                {"label": "Sum", "value": "sum"},
                                {"label": "Median", "value": "median"}
                            ],
                            value="mean",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label([
                            "Filter by Category",
                            html.I(className="bi bi-info-circle ms-1", id="trend-category-tooltip", style={"cursor": "pointer"})
                        ], className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="trend-category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=4),
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
                        html.Label("Metric to Compare", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="category-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Filter by Category", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=6),
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
                        html.Label("Performance Metric", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="performers-metric",
                            options=[{"label": v, "value": k} for k, v in AVAILABLE_METRICS.items()],
                            value="tao_score",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Filter by Category", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="performers-category-filter",
                            options=[{"label": "All Categories", "value": "All"}],
                            value="All",
                            clearable=False,
                            className="dd-compact",
                            style={"width": "100%"},
                        )
                    ], width=6),
                ], className="mb-4"),
                # Chart for this section
                dcc.Graph(id="top-performers-chart", config={'displayModeBar': False})
            ])
        ], className="mb-4"),
        
        # SECTION 4: Improvement Tracking
        dbc.Card([
            dbc.CardHeader([
                html.H4("📈 Improvement Tracking (7-Day)", className="mb-0"),
                html.I(className="bi bi-arrow-up-circle ms-2", id="improvement-tooltip")
            ]),
            dbc.CardBody([
                html.P("Track subnets showing the most improvement in TAO-Score over the last 7 days:", className="text-muted mb-3"),
                # Controls for this section
                dbc.Row([
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
                    ], width=12),
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
        

        
        # Enhanced Tooltips with Detailed Information
        dbc.Tooltip(
            "📊 Network Overview: Key metrics snapshot including total active subnets, combined market cap in TAO, "
            "average TAO-Score across all subnets, count of high performers (≥70 score), strong buy signals (≥4/5), "
            "and total category diversity. Data points and date range show the scope of analysis.",
            target="overview-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "⏰ Global Time Range: Control the time period for all charts simultaneously. Options range from 7 days "
            "to all available data. This ensures consistent analysis across all sections and prevents data mismatches. "
            "Performance optimized with smart data limits.",
            target="time-range-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "📈 Custom Trend Analysis: Create personalized trend charts by selecting any metric, aggregation method "
            "(average, sum, median), and category filter. Perfect for tracking specific metrics over time and "
            "identifying patterns in subnet performance. Supports all 20+ available metrics.",
            target="trend-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "🏷️ Category Performance: Compare subnet categories by any metric to identify which AI service types "
            "are performing best. Helps discover undervalued categories and understand market trends. "
            "Categories include LLM-Inference, Data-Feeds, Serverless-Compute, and more.",
            target="category-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "🏆 Top Performers: View the best-performing subnets by any selected metric. These represent "
            "the highest-quality subnets in the network for your chosen criteria. Useful for identifying "
            "investment opportunities and understanding what drives success in different categories.",
            target="performers-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "📈 Improvement Tracking: Monitor subnets showing the most TAO-Score improvement over the last 7 days. "
            "These represent emerging opportunities and subnets that are actively improving. "
            "Adjust the threshold to focus on significant improvements only.",
            target="improvement-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),
        dbc.Tooltip(
            "📊 Fixed Network Trends: Consistent baseline charts showing stake quality, market cap, and flow trends "
            "over time. These provide essential context for understanding network health, growth patterns, "
            "and overall market dynamics in the Bittensor ecosystem.",
            target="fixed-trends-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "400px"}
        ),

        
        # Individual metric card tooltips
        dbc.Tooltip(
            "🌐 Active Subnets: Total number of subnets currently active in the Bittensor network. "
            "This represents the diversity and scale of AI services available on the network.",
            target="subnets-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        dbc.Tooltip(
            "💰 Total Market Cap: Combined market capitalization of all subnets in TAO tokens. "
            "This represents the total value of all subnet tokens in the network.",
            target="market-cap-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        dbc.Tooltip(
            "📊 Average TAO-Score: Mean TAO-Score across all subnets (0-100 scale). "
            "Proprietary algorithm for evaluating subnet performance and potential.",
            target="tao-score-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        dbc.Tooltip(
            "⭐ High Performers: Number of subnets with TAO-Score ≥ 70. "
            "These represent the highest-quality subnets in the network.",
            target="performers-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        dbc.Tooltip(
            "🚀 Strong Buy Signals: Number of subnets with buy signal ≥ 4/5. "
            "These represent subnets with strong positive momentum and investment potential.",
            target="buy-signals-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        dbc.Tooltip(
            "🏷️ Categories: Total number of unique subnet categories. "
            "Higher diversity indicates a more robust and varied AI service ecosystem.",
            target="categories-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        ),
        
        # Control element tooltips
        dbc.Tooltip(
            "📊 Metric to Track: Select from 20+ available metrics including TAO-Score, stake quality, "
            "market cap, flow, validator utilization, and more. Each metric provides different insights "
            "into subnet performance and network health.",
            target="trend-metric-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "350px"}
        ),
        dbc.Tooltip(
            "📈 Aggregation Method: Choose how to combine data points over time. Average shows typical performance, "
            "Sum shows total impact, Median shows middle performance (less affected by outliers).",
            target="trend-aggregation-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "350px"}
        ),
        dbc.Tooltip(
            "🏷️ Filter by Category: Focus analysis on specific AI service types. Categories include LLM-Inference, "
            "Data-Feeds, Serverless-Compute, and more. 'All Categories' shows network-wide trends.",
            target="trend-category-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "350px"}
        ),
        
        # Store for dynamic data
        dcc.Store(id="overview-data-store"),
        dcc.Store(id="shared-data-store"),
    ])

# Callbacks for network overview
@callback(
    Output("overview-data-store", "data"),
    Input("url", "pathname")
)
def load_overview_data(pathname):
    """Load network overview data when page loads."""
    if pathname != "/dash/insights":
        raise PreventUpdate
    
    try:
        stats, latest_df = get_network_summary_stats()
        
        result = {
            'stats': stats,
            'categories': sorted(latest_df['primary_category'].unique().tolist()) if latest_df is not None and not latest_df.empty and 'primary_category' in latest_df.columns else []
        }
        return result
    except Exception as e:
        print(f"Error in load_overview_data: {e}")
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
        f"Data: {stats.get('data_points', 'Recent data only')} | Range: {stats.get('date_range', 'N/A')}"
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

# SHARED DATA STORE - Single source of truth for all sections
@callback(
    Output("shared-data-store", "data"),
    Input("url", "pathname"),
    Input("shared-time-range", "value")
)
def load_shared_data(pathname, time_range):
    """Load shared time series data for all sections with performance limits."""
    if pathname != "/dash/insights":
        raise PreventUpdate
    
    try:
        # Map time range to days with reasonable limits
        days_map = {
            "7d": 7,
            "14d": 14,
            "30d": 30,
            "60d": 60,
            "90d": 90
        }
        days_back = days_map.get(time_range, 30)
        
        # Limit data points based on time range to prevent memory issues
        limit_map = {
            "7d": 1000,
            "14d": 2000,
            "30d": 5000,
            "60d": 8000,
            "90d": 10000
        }
        limit = limit_map.get(time_range, 5000)
        
        # Load time series data with limits
        df = get_time_series_data(days_back=days_back, limit=limit)
        
        # Keep all columns for comprehensive analysis (correlation matrix needs all metrics)
        # Only filter out non-numeric columns that aren't useful for analysis
        exclude_columns = ['id', 'confidence', 'data_quality_flag', 
                          'last_screener_update', 'created_at', 'updated_at', 'additional', 
                          'discord', 'github_repo', 'owner_coldkey', 'owner_hotkey', 
                          'subnet_contact', 'subnet_url', 'subnet_website', 'symbol']
        
        # Keep all columns except the excluded ones
        available_columns = [col for col in df.columns if col not in exclude_columns]
        df_trimmed = df[available_columns]
        
        # Convert DataFrame to list of dictionaries for JSON serialization
        data_records = []
        for _, row in df_trimmed.iterrows():
            data_records.append(row.to_dict())
        
        return {
            'data': data_records,
            'time_range': days_back,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error loading shared data: {e}")
        return {'data': [], 'time_range': 30, 'timestamp': datetime.now().isoformat()}

# Callbacks for SECTION 1: Custom Trend Analysis
@callback(
    Output("custom-trend-chart", "figure"),
    Input("shared-data-store", "data"),
    Input("trend-metric", "value"),
    Input("trend-aggregation", "value"),
    Input("trend-category-filter", "value")
)
def update_custom_trend_chart(shared_data, metric, aggregation, category):
    """Update custom trend chart using shared data."""
    if not shared_data or 'data' not in shared_data or not shared_data['data']:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(shared_data['data'])
    
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
    Output("category-performance-chart", "figure"),
    Input("shared-data-store", "data"),
    Input("category-metric", "value"),
    Input("category-filter", "value")
)
def update_category_performance_chart(shared_data, metric, category):
    """Update category performance chart using shared data."""
    if not shared_data or 'data' not in shared_data or not shared_data['data']:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(shared_data['data'])
    
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
    Output("top-performers-chart", "figure"),
    Input("shared-data-store", "data"),
    Input("performers-metric", "value"),
    Input("performers-category-filter", "value")
)
def update_top_performers_chart(shared_data, metric, category):
    """Update top performers chart using shared data."""
    if not shared_data or 'data' not in shared_data or not shared_data['data']:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    df = pd.DataFrame(shared_data['data'])
    
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
    Output("improvement-tracking-chart", "figure"),
    Input("url", "pathname"),
    Input("improvement-threshold", "value")
)
def update_improvement_tracking_chart(pathname, threshold):
    """Update improvement tracking chart using fixed 7-day data."""
    if pathname != "/dash/insights":
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    try:
        # Always use 7 days for improvement tracking
        df = get_time_series_data(7)
        
        # Ensure timestamp is properly converted to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return create_improvement_tracker(df, 7)
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading improvement data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callbacks for SECTION 5: Fixed Network Trends
@callback(
    Output("stake-quality-trend", "figure"),
    Output("market-cap-trend", "figure"),
    Output("flow-trend", "figure"),
    Input("shared-data-store", "data")
)
def update_fixed_trends(shared_data):
    """Update fixed trend charts using shared data."""
    if not shared_data or 'data' not in shared_data or not shared_data['data']:
        empty_fig = go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return empty_fig, empty_fig, empty_fig
    
    df = pd.DataFrame(shared_data['data'])
    
    # Ensure timestamp is properly converted to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    stake_quality_trend = create_metric_trend_chart(df, 'stake_quality', 'Average Stake Quality Over Time', '#28a745')
    market_cap_trend = create_metric_trend_chart(df, 'market_cap_tao', 'Total Market Cap (TAO) Over Time', '#ffc107', 'sum')
    flow_trend = create_metric_trend_chart(df, 'flow_24h', 'Total 24h Flow (TAO) Over Time', '#dc3545', 'sum')
    
    return stake_quality_trend, market_cap_trend, flow_trend







def register_callbacks(dash_app):
    """Register callbacks for the insights page."""
    pass 