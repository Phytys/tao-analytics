"""
Insights Dashboard - Time Series Analytics for Bittensor Network
Provides comprehensive insights from historical metrics data for investors and newcomers.
"""

import dash
from dash import html, dcc, Input, Output, callback
from dash.dependencies import State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from services.db import get_db
from models import MetricsSnap, SubnetMeta, CoinGeckoPrice
from sqlalchemy import func, desc, and_, or_, text
import numpy as np

def get_time_series_data():
    """Get time series data from metrics_snap table."""
    session = get_db()
    try:
        # Get all metrics with timestamps
        query = session.query(
            MetricsSnap.netuid,
            MetricsSnap.timestamp,
            MetricsSnap.tao_score,
            MetricsSnap.stake_quality,
            MetricsSnap.validator_util_pct,
            MetricsSnap.active_stake_ratio,
            MetricsSnap.consensus_alignment,
            MetricsSnap.emission_pct,
            MetricsSnap.alpha_emitted_pct,
            MetricsSnap.price_7d_change,
            MetricsSnap.price_30d_change,
            SubnetMeta.subnet_name,
            SubnetMeta.primary_category
        ).join(
            SubnetMeta, MetricsSnap.netuid == SubnetMeta.netuid
        ).order_by(
            MetricsSnap.timestamp.desc()
        )
        
        df = pd.read_sql(query.statement, session.bind)
        return df
    finally:
        session.close()

def get_network_trends(df):
    """Calculate network-wide trends and insights."""
    if df.empty:
        return {}
    
    # Get latest data
    latest_date = df['timestamp'].max()
    week_ago = latest_date - timedelta(days=7)
    month_ago = latest_date - timedelta(days=30)
    
    # Latest metrics
    latest = df[df['timestamp'] == latest_date]
    week_ago_data = df[df['timestamp'] >= week_ago]
    month_ago_data = df[df['timestamp'] >= month_ago]
    
    insights = {
        'total_subnets_tracked': len(latest['netuid'].unique()),
        'data_points_collected': len(df),
        'date_range': f"{df['timestamp'].min().strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}",
        'avg_tao_score': latest['tao_score'].mean(),
        'avg_stake_quality': latest['stake_quality'].mean(),
        'avg_validator_util': latest['validator_util_pct'].mean(),
        'high_performing_subnets': len(latest[latest['tao_score'] >= 70]),
        'improving_subnets': len(latest[latest['price_7d_change'] > 0]),
        'declining_subnets': len(latest[latest['price_7d_change'] < 0]),
        'most_active_category': latest['primary_category'].mode().iloc[0] if not latest['primary_category'].mode().empty else 'N/A',
        'avg_price_change_7d': latest['price_7d_change'].mean(),
        'avg_price_change_30d': latest['price_30d_change'].mean(),
    }
    
    return insights

def create_trend_chart(df, metric, title, color='#3e6ae1'):
    """Create a trend chart for a specific metric."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    # Aggregate by date
    daily_avg = df.groupby(df['timestamp'].dt.date)[metric].mean().reset_index()
    daily_avg['timestamp'] = pd.to_datetime(daily_avg['timestamp'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_avg['timestamp'],
        y=daily_avg[metric],
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

def create_category_performance(df):
    """Create category performance comparison."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    # Get latest data for each subnet
    latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
    
    # Calculate category averages
    category_metrics = latest.groupby('primary_category').agg({
        'tao_score': 'mean',
        'stake_quality': 'mean',
        'validator_util_pct': 'mean',
        'price_7d_change': 'mean'
    }).round(2)
    
    # Create subplot
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('TAO-Score by Category', 'Stake Quality by Category', 
                       'Validator Utilization by Category', '7-Day Price Change by Category'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
              '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#ff9896', '#98df8a']
    
    for i, metric in enumerate(['tao_score', 'stake_quality', 'validator_util_pct', 'price_7d_change']):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        fig.add_trace(
            go.Bar(
                x=category_metrics.index,
                y=category_metrics[metric],
                name=metric.replace('_', ' ').title(),
                marker_color=colors[:len(category_metrics)],
                hovertemplate='<b>%{x}</b><br>%{y:.2f}<extra></extra>'
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Category Performance Comparison",
        title_x=0.5
    )
    
    return fig

def create_top_performers(df):
    """Create top performing subnets chart."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    # Get latest data for each subnet
    latest = df.loc[df.groupby('netuid')['timestamp'].idxmax()]
    
    # Top 10 by TAO-Score
    top_tao = latest.nlargest(10, 'tao_score')[['subnet_name', 'netuid', 'tao_score', 'primary_category']]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_tao['tao_score'],
        y=[f"{row['subnet_name']} ({row['netuid']})" for _, row in top_tao.iterrows()],
        orientation='h',
        marker_color='#3e6ae1',
        hovertemplate='<b>%{y}</b><br>TAO-Score: %{x:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Top 10 Subnets by TAO-Score",
        xaxis_title="TAO-Score",
        yaxis_title="Subnet",
        height=400,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def create_improvement_tracker(df):
    """Create subnet improvement tracking."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    # Get data from last 30 days
    thirty_days_ago = df['timestamp'].max() - timedelta(days=30)
    recent_data = df[df['timestamp'] >= thirty_days_ago]
    
    # Calculate improvement for each subnet
    improvements = []
    for netuid in recent_data['netuid'].unique():
        subnet_data = recent_data[recent_data['netuid'] == netuid].sort_values('timestamp')
        if len(subnet_data) >= 2:
            first_score = subnet_data.iloc[0]['tao_score']
            last_score = subnet_data.iloc[-1]['tao_score']
            improvement = last_score - first_score
            
            subnet_name = subnet_data.iloc[0]['subnet_name']
            category = subnet_data.iloc[0]['primary_category']
            
            improvements.append({
                'netuid': netuid,
                'subnet_name': subnet_name,
                'category': category,
                'improvement': improvement,
                'start_score': first_score,
                'end_score': last_score
            })
    
    if not improvements:
        return go.Figure().add_annotation(text="No improvement data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    
    improvements_df = pd.DataFrame(improvements)
    top_improvers = improvements_df.nlargest(10, 'improvement')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_improvers['improvement'],
        y=[f"{row['subnet_name']} ({row['netuid']})" for _, row in top_improvers.iterrows()],
        orientation='h',
        marker_color=['#28a745' if x > 0 else '#dc3545' for x in top_improvers['improvement']],
        hovertemplate='<b>%{y}</b><br>Improvement: %{x:.1f} points<br>From: %{customdata[0]:.1f} → To: %{customdata[1]:.1f}<extra></extra>',
        customdata=list(zip(top_improvers['start_score'], top_improvers['end_score']))
    ))
    
    fig.update_layout(
        title="Top 10 Most Improved Subnets (Last 30 Days)",
        xaxis_title="TAO-Score Improvement",
        yaxis_title="Subnet",
        height=400,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

# Get data
df = get_time_series_data()
insights = get_network_trends(df)

# Create charts
tao_score_trend = create_trend_chart(df, 'tao_score', 'Average TAO-Score Over Time')
stake_quality_trend = create_trend_chart(df, 'stake_quality', 'Average Stake Quality Over Time', '#28a745')
validator_util_trend = create_trend_chart(df, 'validator_util_pct', 'Average Validator Utilization Over Time', '#ffc107')
category_performance = create_category_performance(df)
top_performers = create_top_performers(df)
improvement_tracker = create_improvement_tracker(df)

layout = html.Div([
    # Header with onboarding
    dbc.Card([
        dbc.CardBody([
            html.H1("📊 Bittensor Network Insights", className="dashboard-title mb-3"),
            html.Div([
                html.H5("🎯 Welcome to Time Series Analytics", className="text-primary mb-2"),
                html.P([
                    "This dashboard provides deep insights into the Bittensor network's performance over time. ",
                    "As our database grows with daily snapshots, these insights become increasingly valuable for ",
                    "understanding network trends, identifying opportunities, and tracking subnet performance."
                ], className="mb-3"),
                html.Div([
                    html.Strong("💡 For Newcomers: "),
                    "Learn how the network evolves and which subnets are performing best. ",
                    "Each metric tells a story about network health and growth."
                ], className="alert alert-info mb-2"),
                html.Div([
                    html.Strong("💰 For Investors: "),
                    "Track performance trends, identify improving subnets, and understand ",
                    "which categories are gaining momentum. Use this data to inform your investment decisions."
                ], className="alert alert-success mb-0")
            ])
        ])
    ], className="mb-4"),
    
    # Subnet Search Bar
    dbc.Card([
        dbc.CardBody([
            html.H5("🔍 Quick Subnet Search", className="mb-3"),
            html.P("Search for any subnet by name or number to view detailed analytics:", className="text-muted mb-3"),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id="subnet-search",
                        placeholder="Type subnet name or number (e.g., 'Apex' or '1')",
                        options=[],
                        value=None,
                        clearable=True,
                        searchable=True,
                        style={"width": "100%"}
                    )
                ], width=8),
                dbc.Col([
                    html.A(
                        dbc.Button(
                            "Go to Subnet",
                            id="go-to-subnet-btn",
                            color="primary",
                            className="w-100",
                            disabled=True
                        ),
                        id="subnet-link",
                        href="#",
                        className="text-decoration-none"
                    )
                ], width=4)
            ])
        ])
    ], className="mb-4"),
    
    # Network Overview Cards
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
                            html.H3(f"{insights.get('total_subnets_tracked', 0)}", className="text-primary"),
                            html.P("Subnets Tracked", className="text-muted mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H3(f"{insights.get('data_points_collected', 0):,}", className="text-success"),
                            html.P("Data Points", className="text-muted mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H3(f"{insights.get('high_performing_subnets', 0)}", className="text-warning"),
                            html.P("High Performers (≥70 TAO-Score)", className="text-muted mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H3(f"{insights.get('improving_subnets', 0)}", className="text-info"),
                            html.P("Improving Subnets", className="text-muted mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
            ], className="mb-3"),
            html.Small(f"Data range: {insights.get('date_range', 'N/A')}", className="text-muted")
        ])
    ], className="mb-4"),
    
    # Trend Analysis
    dbc.Card([
        dbc.CardHeader([
            html.H4("Network Trends", className="mb-0"),
            html.I(className="bi bi-info-circle ms-2", id="trends-tooltip")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=tao_score_trend, config={'displayModeBar': False})
                ], width=6),
                dbc.Col([
                    dcc.Graph(figure=stake_quality_trend, config={'displayModeBar': False})
                ], width=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=validator_util_trend, config={'displayModeBar': False})
                ], width=12),
            ])
        ])
    ], className="mb-4"),
    
    # Category Performance
    dbc.Card([
        dbc.CardHeader([
            html.H4("Category Performance Analysis", className="mb-0"),
            html.I(className="bi bi-info-circle ms-2", id="category-tooltip")
        ]),
        dbc.CardBody([
            dcc.Graph(figure=category_performance, config={'displayModeBar': False})
        ])
    ], className="mb-4"),
    
    # Top Performers and Improvement Tracking
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Top Performers", className="mb-0"),
                    html.I(className="bi bi-info-circle ms-2", id="performers-tooltip")
                ]),
                dbc.CardBody([
                    dcc.Graph(figure=top_performers, config={'displayModeBar': False})
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Improvement Tracking", className="mb-0"),
                    html.I(className="bi bi-info-circle ms-2", id="improvement-tooltip")
                ]),
                dbc.CardBody([
                    dcc.Graph(figure=improvement_tracker, config={'displayModeBar': False})
                ])
            ])
        ], width=6),
    ], className="mb-4"),
    
    # Tooltips
    dbc.Tooltip(
        "Overview of key network metrics including total subnets tracked, data points collected, "
        "high-performing subnets (TAO-Score ≥70), and subnets showing positive momentum.",
        target="overview-tooltip",
        placement="top"
    ),
    dbc.Tooltip(
        "Historical trends showing how network health metrics change over time. "
        "TAO-Score measures overall subnet health, Stake Quality shows decentralization, "
        "and Validator Utilization indicates network capacity usage.",
        target="trends-tooltip",
        placement="top"
    ),
    dbc.Tooltip(
        "Performance comparison across different subnet categories. This helps identify "
        "which types of AI services are performing best and which categories might be "
        "undervalued or overvalued.",
        target="category-tooltip",
        placement="top"
    ),
    dbc.Tooltip(
        "Current top-performing subnets by TAO-Score. These represent the healthiest "
        "and most well-run subnets in the network. Consider these for investment research.",
        target="performers-tooltip",
        placement="top"
    ),
    dbc.Tooltip(
        "Subnets showing the most improvement in TAO-Score over the last 30 days. "
        "These represent emerging opportunities and subnets that are actively improving "
        "their network health and performance.",
        target="improvement-tooltip",
        placement="top"
    ),
    
    # Refresh interval
    dcc.Interval(id="insights-interval", interval=300000, n_intervals=0),  # 5 minutes
])

@callback(
    Output("insights-interval", "disabled"),
    Input("insights-interval", "n_intervals")
)
def update_insights(n_intervals):
    """Update insights data periodically."""
    return False

@callback(
    Output("subnet-search", "options"),
    Input("subnet-search", "search_value")
)
def update_search_options(search_value):
    """Update search options based on user input."""
    session = get_db()
    try:
        # Get all subnets with names and netuids
        query = session.query(
            SubnetMeta.netuid,
            SubnetMeta.subnet_name,
            SubnetMeta.primary_category
        ).order_by(SubnetMeta.netuid)
        
        subnets = query.all()
        
        options = []
        for subnet in subnets:
            # Create option with both name and netuid
            label = f"{subnet.subnet_name} (Subnet {subnet.netuid})"
            value = str(subnet.netuid)
            
            # If there's a search value, filter options
            if search_value:
                search_lower = search_value.lower()
                if (search_lower in subnet.subnet_name.lower() or 
                    search_lower in str(subnet.netuid) or
                    search_lower in subnet.primary_category.lower()):
                    options.append({"label": label, "value": value})
            else:
                options.append({"label": label, "value": value})
        
        return options
    finally:
        session.close()

@callback(
    [Output("go-to-subnet-btn", "disabled"),
     Output("subnet-link", "href")],
    Input("subnet-search", "value")
)
def update_button_state_and_link(selected_value):
    """Enable/disable the Go button and update link href based on selection."""
    if selected_value:
        return False, f"/dash/subnet-detail?netuid={selected_value}"
    else:
        return True, "#"

def register_callbacks(dash_app):
    """Register callbacks for the insights page."""
    pass 