import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from services.db import load_screener_frame, get_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import CoinGeckoPrice, MetricsSnap
from services.gpt_insight import get_buy_signal_for_subnet, get_insight, extract_buy_signal_from_insight
import time

# Fetch latest TAO/USD price from CoinGeckoPrice
try:
    from services.db import get_db
    session = get_db()
    price_row = session.query(CoinGeckoPrice).order_by(CoinGeckoPrice.fetched_at.desc()).first()
    tao_price_usd = float(price_row.price_usd) if price_row and price_row.price_usd else 0.0
    session.close()
except Exception:
    tao_price_usd = 0.0

# Load data once for initial test (will be replaced with callback/caching)
df = load_screener_frame()
# Get fresh timestamp for display
latest_ts = df['metrics_timestamp'].max() if 'metrics_timestamp' in df.columns else None

# Add buy signal scores from GPT insights
from services.gpt_insight import get_buy_signal_for_subnet
df['buy_signal'] = df['netuid'].apply(get_buy_signal_for_subnet)

# Function to reload data with latest buy signals
def reload_data_with_buy_signals():
    """Reload screener data with latest buy signals from database."""
    fresh_df = load_screener_frame()
    fresh_df['buy_signal'] = fresh_df['netuid'].apply(get_buy_signal_for_subnet)
    
    # Calculate market_cap_musd if market_cap_tao exists
    if 'market_cap_tao' in fresh_df.columns:
        fresh_df['market_cap_usd'] = fresh_df['market_cap_tao'] * tao_price_usd
        fresh_df['market_cap_usd'] = fresh_df['market_cap_usd'].fillna(0)
        fresh_df.loc[fresh_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        # Convert to millions USD for display
        fresh_df['market_cap_musd'] = fresh_df['market_cap_usd'] / 1_000_000
    
    return fresh_df

# Add market_cap_usd column (in millions)
if 'market_cap_tao' in df.columns:
    df['market_cap_usd'] = df['market_cap_tao'] * tao_price_usd
    df['market_cap_usd'] = df['market_cap_usd'].fillna(0)
    df.loc[df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
    # Convert to millions USD for display
    df['market_cap_musd'] = df['market_cap_usd'] / 1_000_000

# Define available metrics for dynamic axes (only those that exist in the dataframe)
AXIS_METRICS = {
    # Price & Momentum
    'price_1h_change': {'label': '1-Hour Price Change (%)', 'type': 'percentage'},
    'price_1d_change': {'label': '1-Day Price Change (%)', 'type': 'percentage'},
    'price_7d_change': {'label': '7-Day Price Change (%)', 'type': 'percentage'},
    'price_30d_change': {'label': '30-Day Price Change (%)', 'type': 'percentage'},
    'price_tao': {'label': 'Price (TAO)', 'type': 'price'},
    'ath_60d': {'label': '60-Day ATH (TAO)', 'type': 'price'},
    'atl_60d': {'label': '60-Day ATL (TAO)', 'type': 'price'},
    
    # Volume & Flow Analysis
    'buy_volume_tao_1d': {'label': '24h Buy Volume (TAO)', 'type': 'volume'},
    'sell_volume_tao_1d': {'label': '24h Sell Volume (TAO)', 'type': 'volume'},
    'total_volume_tao_1d': {'label': '24h Total Volume (TAO)', 'type': 'volume'},
    'buy_sell_ratio': {'label': 'Buy/Sell Ratio', 'type': 'ratio'},
    'net_volume_tao_1h': {'label': '1h Net Volume (TAO)', 'type': 'volume'},
    'net_volume_tao_7d': {'label': '7d Net Volume (TAO)', 'type': 'volume'},
    'flow_24h': {'label': '24h Net Flow (TAO)', 'type': 'volume'},
    'buy_volume_pct_change': {'label': 'Buy Volume % Change', 'type': 'percentage'},
    'sell_volume_pct_change': {'label': 'Sell Volume % Change', 'type': 'percentage'},
    'total_volume_pct_change': {'label': 'Total Volume % Change', 'type': 'percentage'},
    
    # Network Health & Participation
    'uid_count': {'label': 'Total UIDs', 'type': 'count'},
    'active_validators': {'label': 'Active Validators', 'type': 'count'},
    'validators_active': {'label': 'Validators Active', 'type': 'count'},
    'max_validators': {'label': 'Max Validators', 'type': 'count'},
    'validator_util_pct': {'label': 'Validator Utilization (%)', 'type': 'percentage'},
    
    # Stake Quality & Distribution
    'tao_score': {'label': 'TAO-Score', 'type': 'score'},
    'stake_quality': {'label': 'Stake Quality', 'type': 'score'},
    'stake_quality_rank_pct': {'label': 'Stake Quality Rank (%)', 'type': 'percentage'},
    'active_stake_ratio': {'label': 'Active Stake Ratio (%)', 'type': 'percentage'},
    'stake_hhi': {'label': 'Stake HHI', 'type': 'concentration'},
    'hhi': {'label': 'HHI Index', 'type': 'concentration'},
    'gini_coeff_top_100': {'label': 'Gini Coefficient (Top 100)', 'type': 'concentration'},
    
    # Momentum & Performance
    'reserve_momentum': {'label': 'Reserve Momentum', 'type': 'momentum'},
    'momentum_rank_pct': {'label': 'Momentum Rank (%)', 'type': 'percentage'},
    'consensus_alignment': {'label': 'Consensus Alignment (%)', 'type': 'percentage'},
    'realized_pnl_tao': {'label': 'Realized PnL (TAO)', 'type': 'pnl'},
    'unrealized_pnl_tao': {'label': 'Unrealized PnL (TAO)', 'type': 'pnl'},
    
    # Market & Valuation
    'market_cap_tao': {'label': 'Market Cap (TAO)', 'type': 'market_cap'},
    'fdv_tao': {'label': 'Fully Diluted Valuation (TAO)', 'type': 'market_cap'},
    'total_stake_tao': {'label': 'Total Stake (TAO)', 'type': 'stake'},
    
    # Emission & Token Economics
    'tao_in': {'label': 'TAO Reserves', 'type': 'reserves'},
    'emission_pct': {'label': 'Emission Percentage', 'type': 'percentage'},
    'alpha_emitted_pct': {'label': 'Alpha Emitted (%)', 'type': 'percentage'},
    'emission_roi': {'label': 'Emission ROI', 'type': 'roi'},
    
    # Token Flow & Distribution
    'alpha_in': {'label': 'Alpha In (TAO)', 'type': 'flow'},
    'alpha_out': {'label': 'Alpha Out (TAO)', 'type': 'flow'},
    'alpha_circ': {'label': 'Alpha Circulation', 'type': 'flow'},
    'alpha_prop': {'label': 'Alpha Proportion', 'type': 'proportion'},
    'root_prop': {'label': 'Root Proportion', 'type': 'proportion'},
}

# Create axis options for dropdowns
axis_options = [{"label": f"{v['label']}", "value": k} for k, v in AXIS_METRICS.items()]

# Get available categories for dropdown
categories = sorted(df['primary_category'].dropna().unique().tolist())
category_options = [{"label": "All Categories", "value": "All"}] + [
    {"label": cat, "value": cat} for cat in categories
]

# Compute max market cap for slider (set to 1000 MUSD)
mcap_max = 1000

# Create initial figures
def create_initial_momentum_fig():
    """Create initial momentum figure."""
    fig = px.scatter(
        df,
        x='price_7d_change',
        y='price_30d_change',
        size='market_cap_musd',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'tao_score', 'metrics_timestamp', 'primary_category', 'market_cap_musd'],
        title="Price Momentum Analysis",
        labels={
            'price_7d_change': '7-Day Price Change (%)',
            'price_30d_change': '30-Day Price Change (%)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'primary_category': 'Category'
        },
        size_max=40
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=8),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Category: %{customdata[4]}<br>" +
                     "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                     "X: %{x:.1f}%<br>" +
                     "Y: %{y:.1f}%<br>" +
                     "TAO-Score: %{customdata[2]:.1f}<br>" +
                     "Data: %{customdata[3]}<br>" +
                     "<extra></extra>"
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    return fig

def create_initial_buy_signal_fig():
    """Create initial buy signal figure."""
    fig = px.scatter(
        df,
        x='tao_score',
        y='flow_24h',
        size='market_cap_musd',
        color='buy_signal',
        color_continuous_scale=['grey', 'red', 'orange', 'yellow', 'lightgreen', 'darkgreen'],
        hover_data=['subnet_name', 'netuid', 'tao_score', 'flow_24h', 'buy_signal'],
        title="Buy Signal Analysis",
        labels={
            'tao_score': 'TAO-Score',
            'flow_24h': '24h Net Flow (TAO)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'buy_signal': 'Buy Signal'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "TAO-Score: %{customdata[2]:.1f}<br>" +
                     "24h Flow: %{customdata[3]:.0f} TAO<br>" +
                     "Buy Signal: %{customdata[4]}<br>" +
                     "<extra></extra>"
    )
    return fig

# Create initial figures
momentum_fig = create_initial_momentum_fig()
buy_signal_fig = create_initial_buy_signal_fig()

# Create additional charts for the third section
def create_tao_score_distribution():
    """Create TAO-Score distribution histogram."""
    fig = px.histogram(
        df,
        x='tao_score',
        nbins=20,
        title="TAO-Score Distribution",
        labels={'tao_score': 'TAO-Score', 'count': 'Number of Subnets'},
        color_discrete_sequence=['#3e6ae1']
    )
    fig.update_layout(
        xaxis_title="TAO-Score",
        yaxis_title="Number of Subnets",
        showlegend=False
    )
    return fig

def create_validator_utilization():
    """Create validator utilization scatter plot."""
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    fig = px.scatter(
        viz_df,
        x='validator_util_pct',
        y='tao_score',
        size='market_cap_musd',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'validator_util_pct', 'tao_score'],
        title="Validator Utilization vs TAO-Score",
        labels={
            'validator_util_pct': 'Validator Utilization (%)',
            'tao_score': 'TAO-Score',
            'market_cap_musd': 'Market Cap (MUSD)',
            'primary_category': 'Category'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Validator Util: %{customdata[2]:.1f}%<br>" +
                     "TAO-Score: %{customdata[3]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig

def create_volume_analysis():
    """Create volume analysis scatter plot."""
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    fig = px.scatter(
        viz_df,
        x='buy_volume_tao_1d',
        y='sell_volume_tao_1d',
        size='market_cap_musd',
        color='buy_sell_ratio',
        color_continuous_scale='RdYlGn',
        hover_data=['subnet_name', 'netuid', 'buy_volume_tao_1d', 'sell_volume_tao_1d', 'buy_sell_ratio', 'market_cap_musd'],
        title="Buy vs Sell Volume Analysis",
        labels={
            'buy_volume_tao_1d': '24h Buy Volume (TAO)',
            'sell_volume_tao_1d': '24h Sell Volume (TAO)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'buy_sell_ratio': 'Buy/Sell Ratio'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Buy Volume: %{customdata[2]:.0f} TAO<br>" +
                     "Sell Volume: %{customdata[3]:.0f} TAO<br>" +
                     "Buy/Sell Ratio: %{customdata[4]:.2f}<br>" +
                     "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                     "<extra></extra>"
    )
    # Add diagonal line for equal buy/sell
    max_val = max(viz_df['buy_volume_tao_1d'].max(), viz_df['sell_volume_tao_1d'].max())
    fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode='lines', 
                            line=dict(dash='dash', color='gray'), 
                            name='Equal Buy/Sell', showlegend=False))
    return fig

def create_stake_distribution():
    """Create stake distribution analysis."""
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    fig = px.scatter(
        viz_df,
        x='stake_hhi',
        y='gini_coeff_top_100',
        size='market_cap_musd',
        color='active_stake_ratio',
        color_continuous_scale='Viridis',
        hover_data=['subnet_name', 'netuid', 'stake_hhi', 'gini_coeff_top_100', 'active_stake_ratio', 'market_cap_musd'],
        title="Stake Distribution Analysis",
        labels={
            'stake_hhi': 'Stake HHI (Concentration)',
            'gini_coeff_top_100': 'Gini Coefficient (Top 100)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'active_stake_ratio': 'Active Stake Ratio (%)'
        },
        size_max=25
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Stake HHI: %{customdata[2]:.2f}<br>" +
                     "Gini Coefficient: %{customdata[3]:.2f}<br>" +
                     "Active Stake Ratio: %{customdata[4]:.1f}%<br>" +
                     "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                     "<extra></extra>"
    )
    return fig

def create_network_health():
    """Create network health analysis."""
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    fig = px.scatter(
        viz_df,
        x='active_validators',
        y='validator_util_pct',
        size='market_cap_musd',
        color='uid_count',
        color_continuous_scale='Plasma',
        hover_data=['subnet_name', 'netuid', 'active_validators', 'validator_util_pct', 'uid_count', 'market_cap_musd'],
        title="Network Health & Participation",
        labels={
            'active_validators': 'Active Validators',
            'validator_util_pct': 'Validator Utilization (%)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'uid_count': 'Total UIDs'
        },
        size_max=25
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Active Validators: %{customdata[2]}<br>" +
                     "Validator Utilization: %{customdata[3]:.1f}%<br>" +
                     "Total UIDs: %{customdata[4]}<br>" +
                     "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                     "<extra></extra>"
    )
    return fig

# Create initial figures for additional analysis
tao_score_fig = create_tao_score_distribution()
validator_fig = create_validator_utilization()
volume_fig = create_volume_analysis()
stake_dist_fig = create_stake_distribution()
network_health_fig = create_network_health()

# Layout with dynamic control panels
layout = html.Div([
    # --- Tesla-inspired header ---
    html.Div([
        html.H1("Subnet Screener", className="dashboard-title"),
        html.P("Discover and analyze Bittensor subnets with AI-powered insights, dynamic charts, and comprehensive metrics for investment decision making.", className="text-muted mb-4"),
    ], className="dashboard-header"),
    
    # --- Quick Start section (collapsible) ---
    html.Div([
        dbc.Button(
            [
                html.I(className="bi bi-question-circle me-2"),
                "Quick Start Guide",
                html.I(className="bi bi-chevron-down ms-2", id="screener-quick-start-icon")
            ],
            id="screener-quick-start-toggle",
            color="outline-primary",
            className="mb-3",
            n_clicks=0
        ),
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody([
                    html.H5("🎯 How to Use This Screener", className="mb-3"),
                    html.P("Welcome to the Subnet Explorer! This tool helps you discover investment opportunities across Bittensor subnets using AI-powered analytics and comprehensive metrics.", className="mb-3"),
                    html.Div([
                        html.Div([
                            html.H6("✅ AI-Generated Buy Signal", className="text-primary"),
                            html.P("Each subnet is scored 1-5 by an AI model based on fundamentals, market data, and network health. Look for green 'BUY' indicators in the Buy Signal chart.")
                        ], className="mb-3"),
                        html.Div([
                            html.H6("📈 TAO Score", className="text-primary"),
                            html.P("Higher TAO scores indicate better investment potential. Proprietary algorithm for evaluating subnet performance and potential.")
                        ], className="mb-3"),
                        html.Div([
                            html.H6("🧠 Dynamic Chart Axes", className="text-primary"),
                            html.P("Choose any two metrics for X and Y axes in the Price Momentum and Buy Signal charts. Over 30 metrics available including price changes, volume analysis, and network health indicators.")
                        ], className="mb-3"),
                        html.Div([
                            html.H6("🔍 Filter & Sort", className="text-primary"),
                            html.P("Use category and market cap filters to focus your analysis on specific types of subnets or investment ranges.")
                        ], className="mb-3"),
                        html.Div([
                            html.H6("📊 Additional Analysis", className="text-primary"),
                            html.P("Explore volume analysis, stake distribution, network health, TAO-score distribution, and validator utilization in the bottom section.")
                        ], className="mb-3"),
                        html.Div([
                            html.H6("💡 Interactive Insights", className="text-primary"),
                            html.P("Click on any dot in the Buy Signal chart to generate AI insights and detailed analysis. Wait a few seconds for the AI analysis to complete.")
                        ], className="mb-3")
                    ])
                ]),
                className="border-primary"
            ),
            id="screener-quick-start-collapse",
            is_open=False
        )
    ], className="mb-4"),
    # Section 1: Price Momentum Analysis with Dynamic Axes
    dbc.Card([
        dbc.CardHeader([
            html.H4("Price Momentum Analysis", className="mb-0", id="price-momentum-header"),
            html.Small("Dynamic Axis Selection for Price & Momentum Metrics", className="text-muted")
        ]),
        dbc.CardBody([
            # Control Panel
            dbc.Row([
                dbc.Col([
                    html.Small("X-Axis Metric", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="momentum-x-axis",
                        options=axis_options,
                        value="price_7d_change",
                        clearable=False,
                        placeholder="Select X-axis metric",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    html.Small("Y-Axis Metric", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="momentum-y-axis",
                        options=axis_options,
                        value="price_30d_change",
                        clearable=False,
                        placeholder="Select Y-axis metric",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    html.Small("Category Filter", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="momentum-category-filter",
                        options=category_options,
                        value="All",
                        clearable=False,
                        placeholder="Category",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    html.Small("Market Cap Range (MUSD)", className="text-muted mb-1 d-block"),
                    dcc.RangeSlider(
                        id="momentum-mcap-slider",
                        min=0,
                        max=mcap_max,
                        step=10,
                        value=[0, mcap_max],
                        marks={0: '0', int(mcap_max): f"${int(mcap_max)}M"},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], width=3),
            ], className="mb-2"),
            
            # Chart
            dcc.Graph(id="momentum-chart", figure=momentum_fig, style={"height": "600px"}),
            
            # Data timestamp
            html.Div([
                html.Small(id="momentum-data-timestamp", className="text-muted")
            ], className="mt-2"),
        ])
    ], className="mb-4"),
    
    # Section 2: Buy Signal Analysis with Dynamic Axes
    dbc.Card([
        dbc.CardHeader([
            html.H4("Buy Signal Analysis", className="mb-0", id="buy-signal-header"),
            html.Small("Dynamic Axis Selection for Buy Signal Analysis", className="text-muted"),
            html.Div([
                html.P("💡 Click on any grey dot to generate AI insights. Insights will appear below the graph.", 
                       className="text-danger mb-1", style={"fontSize": "14px"}),
                html.P("⏱️ Please wait a few seconds for the AI analysis to complete.", 
                       className="text-danger mb-0", style={"fontSize": "14px"})
            ], className="mt-2")
        ]),
        dbc.CardBody([
            # Control Panel
            dbc.Row([
                dbc.Col([
                    html.Small("X-Axis Metric", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="buy-signal-x-axis",
                        options=axis_options,
                        value="tao_score",
                        clearable=False,
                        placeholder="Select X-axis metric",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    html.Small("Y-Axis Metric", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="buy-signal-y-axis",
                        options=axis_options,
                        value="flow_24h",
                        clearable=False,
                        placeholder="Select Y-axis metric",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    html.Small("Category Filter", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="buy-signal-category-filter",
                        options=category_options,
                        value="All",
                        clearable=False,
                        placeholder="Category",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=3),
                dbc.Col([
                    dbc.Switch(
                        id="show-netuid-labels",
                        label="Show NetUID Labels",
                        value=False,
                        className="mt-4"
                    )
                ], width=3),
            ], className="mb-2"),
            
            # Buy Signal Chart
            dcc.Graph(
                id="buy-signal-chart",
                figure=buy_signal_fig,
                style={"height": "500px"}
            ),
            
            # Data timestamp
            html.Div([
                html.Small(id="buy-signal-data-timestamp", className="text-muted")
            ], className="mt-2"),
            # Insight display area
            html.Div(id="insight-display", className="mt-3")
        ])
    ], className="mb-4"),
    
    # Section 3: Additional Analysis - Fixed Charts
    dbc.Card([
        dbc.CardHeader([
            html.H4("Additional Analysis", className="mb-0", id="additional-analysis-header"),
            html.Small("Network Health, Volume Analysis & Stake Distribution", className="text-muted")
        ]),
        dbc.CardBody([
            # Control Panel (simplified - only category and market cap filters)
            dbc.Row([
                dbc.Col([
                    html.Small("Category Filter", className="text-muted mb-1 d-block"),
                    dcc.Dropdown(
                        id="additional-category-filter",
                        options=category_options,
                        value="All",
                        clearable=False,
                        placeholder="Category",
                        className="dd-compact",
                        style={"width": "100%"},
                    )
                ], width=6),
                dbc.Col([
                    html.Small("Market Cap Range (MUSD)", className="text-muted mb-1 d-block"),
                    dcc.RangeSlider(
                        id="additional-mcap-slider",
                        min=0,
                        max=mcap_max,
                        step=10,
                        value=[0, mcap_max],
                        marks={0: '0', int(mcap_max): f"${int(mcap_max)}M"},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], width=6),
            ], className="mb-2"),
            
            # First row: TAO-Score Distribution and Volume Analysis
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="tao-score-distribution",
                        figure=tao_score_fig,
                        style={"height": "400px"}
                    )
                ], width=6),
                dbc.Col([
                    dcc.Graph(
                        id="volume-analysis",
                        figure=volume_fig,
                        style={"height": "400px"}
                    )
                ], width=6),
            ], className="mb-4"),
            
            # Second row: Stake Distribution and Network Health
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="stake-distribution",
                        figure=stake_dist_fig,
                        style={"height": "400px"}
                    )
                ], width=6),
                dbc.Col([
                    dcc.Graph(
                        id="network-health",
                        figure=network_health_fig,
                        style={"height": "400px"}
                    )
                ], width=6),
            ], className="mb-4"),
            
            # Third row: Validator Utilization
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="validator-utilization",
                        figure=validator_fig,
                        style={"height": "400px"}
                    )
                ], width=12),
            ], className="mb-4"),
            
            # Data timestamp
            html.Div([
                html.Small(id="additional-data-timestamp", className="text-muted")
            ], className="mt-2"),
        ])
    ], className="mb-4"),
    
    # Store for buy signal refresh
    dcc.Store(id="buy-signal-refresh"),
])

@callback(
    Output("insight-display", "children"),
    Output("buy-signal-refresh", "data"),
    Input("buy-signal-chart", "clickData")
)
def handle_buy_signal_click(click_data):
    """Handle click on buy signal chart to generate insights."""
    if not click_data or not click_data.get('points'):
        return "Click on any subnet dot to generate AI insights.", None
    
    point = click_data['points'][0]
    netuid = point['customdata'][1]  # NetUID is in customdata[1]
    
    try:
        # Generate insight for the clicked subnet
        insight = get_insight(netuid)
        
        # Extract buy signal from insight
        buy_signal = extract_buy_signal_from_insight(insight)
        
        # Update buy signal in database
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            if latest_metrics:
                latest_metrics.buy_signal = buy_signal
                session.commit()
        
        # Format the insight display
        insight_display = dbc.Card([
            dbc.CardHeader([
                html.H5(f"AI Insight for Subnet {netuid}", className="mb-0"),
                dbc.Badge(f"Buy Signal: {buy_signal}/5", color="success" if buy_signal >= 4 else "warning" if buy_signal >= 3 else "danger")
            ]),
            dbc.CardBody([
                html.P(insight, className="mb-0")
            ])
        ])
        
        return insight_display, time.time()
        
    except Exception as e:
        error_display = dbc.Alert([
            html.H5("Error generating insight", className="alert-heading"),
            html.P(f"Could not generate AI insight for subnet {netuid}: {str(e)}")
        ], color="danger")
        return error_display, None

@callback(
    Output("momentum-chart", "figure"),
    Input("momentum-x-axis", "value"),
    Input("momentum-y-axis", "value"),
    Input("momentum-category-filter", "value"),
    Input("momentum-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_momentum_chart(x_axis, y_axis, category, mcap_range, _):
    """Update momentum chart with dynamic axes."""
    try:
        # Always reload fresh data from database
        fresh_df = reload_data_with_buy_signals()
        
        # Validate that selected axes exist in dataframe
        if x_axis not in fresh_df.columns or y_axis not in fresh_df.columns:
            # Create error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"❌ Invalid axis selection<br>'{x_axis}' or '{y_axis}' not available in data<br><br>Please select different metrics",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red"),
                align="center"
            )
            fig.update_layout(
                title="Price Momentum Analysis - Error",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                plot_bgcolor='white'
            )
            return fig
        
        # Apply category filter
        if category == "All" or category is None:
            filtered_df = fresh_df
        else:
            filtered_df = fresh_df[fresh_df['primary_category'] == category]
        
        # Apply market cap filter (in MUSD)
        if mcap_range and len(mcap_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
                (filtered_df['market_cap_musd'] <= mcap_range[1])
            ]
        
        # Ensure market_cap_musd is at least 0.1 for sizing
        if 'market_cap_musd' in filtered_df.columns:
            filtered_df['market_cap_musd'] = filtered_df['market_cap_musd'].fillna(0.1)
            filtered_df.loc[filtered_df['market_cap_musd'] < 0.1, 'market_cap_musd'] = 0.1
        
        # Get axis labels
        x_label = AXIS_METRICS.get(x_axis, {}).get('label', x_axis)
        y_label = AXIS_METRICS.get(y_axis, {}).get('label', y_axis)
        
        # Create updated figure
        fig = px.scatter(
            filtered_df,
            x=x_axis,
            y=y_axis,
            size='market_cap_musd',
            color='primary_category',
            hover_data=['subnet_name', 'netuid', 'tao_score', 'metrics_timestamp', 'primary_category', 'market_cap_musd'],
            title="Price Momentum Analysis",
            labels={
                x_axis: x_label,
                y_axis: y_label,
                'market_cap_musd': 'Market Cap (MUSD)',
                'primary_category': 'Category'
            },
            size_max=40
        )
        
        fig.update_traces(
            marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=8),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "NetUID: %{customdata[1]}<br>" +
                         "Category: %{customdata[4]}<br>" +
                         "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                         f"{x_label}: %{{x:.1f}}<br>" +
                         f"{y_label}: %{{y:.1f}}<br>" +
                         "TAO-Score: %{customdata[2]:.1f}<br>" +
                         "Data: %{customdata[3]}<br>" +
                         "<extra></extra>"
        )
        
        # Add quadrant lines for percentage metrics
        if AXIS_METRICS.get(x_axis, {}).get('type') == 'percentage':
            fig.add_vline(x=0, line_dash="dash", line_color="gray")
        if AXIS_METRICS.get(y_axis, {}).get('type') == 'percentage':
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        return fig
        
    except Exception as e:
        # Create error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"❌ Error creating chart<br>{str(e)}<br><br>Please try different axis selections",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Price Momentum Analysis - Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='white'
        )
        return fig

@callback(
    Output("buy-signal-chart", "figure"),
    Input("buy-signal-x-axis", "value"),
    Input("buy-signal-y-axis", "value"),
    Input("buy-signal-category-filter", "value"),
    Input("show-netuid-labels", "value"),
    Input("buy-signal-refresh", "data")
)
def update_buy_signal_chart(x_axis, y_axis, category, show_labels, _):
    """Update buy signal chart with dynamic axes."""
    try:
        # Always reload fresh data from database to get latest buy signals
        fresh_df = reload_data_with_buy_signals()
        
        # Validate that selected axes exist in dataframe
        if x_axis not in fresh_df.columns or y_axis not in fresh_df.columns:
            # Create error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"❌ Invalid axis selection<br>'{x_axis}' or '{y_axis}' not available in data<br><br>Please select different metrics",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red"),
                align="center"
            )
            fig.update_layout(
                title="Buy Signal Analysis - Error",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                plot_bgcolor='white'
            )
            return fig
        
        # Apply category filter
        if category == "All" or category is None:
            filtered_df = fresh_df
        else:
            filtered_df = fresh_df[fresh_df['primary_category'] == category]
        
        # Reload buy signals from database to get latest values
        filtered_df['buy_signal'] = filtered_df['netuid'].apply(get_buy_signal_for_subnet)
        
        # Ensure market_cap_musd is calculated
        if 'market_cap_musd' not in filtered_df.columns and 'market_cap_tao' in filtered_df.columns:
            filtered_df['market_cap_usd'] = filtered_df['market_cap_tao'] * tao_price_usd
            filtered_df['market_cap_usd'] = filtered_df['market_cap_usd'].fillna(0)
            filtered_df.loc[filtered_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
            filtered_df['market_cap_musd'] = filtered_df['market_cap_usd'] / 1_000_000
        
        # Create color mapping: buy signal if available, grey if not
        filtered_df['color_value'] = filtered_df['buy_signal'].fillna(0)  # 0 for grey (no signal)
        
        # Create custom color scale: grey for 0, then heatmap colors for 1-5
        colorscale = [
            [0, 'lightgrey'],      # 0 = no signal (grey)
            [0.2, '#ff7f7f'],      # 1 = red (avoid)
            [0.4, '#ffbf7f'],      # 2 = orange (weak)
            [0.6, '#ffff7f'],      # 3 = yellow (neutral)
            [0.8, '#7fff7f'],      # 4 = light green (good)
            [1.0, '#007f00']       # 5 = dark green (strong buy)
        ]
        
        # Get axis labels
        x_label = AXIS_METRICS.get(x_axis, {}).get('label', x_axis)
        y_label = AXIS_METRICS.get(y_axis, {}).get('label', y_axis)
        
        # Ensure market_cap_musd is at least 0.1 for sizing
        if 'market_cap_musd' in filtered_df.columns:
            filtered_df['market_cap_musd'] = filtered_df['market_cap_musd'].fillna(0.1)
            filtered_df.loc[filtered_df['market_cap_musd'] < 0.1, 'market_cap_musd'] = 0.1
        
        fig = px.scatter(
            filtered_df,
            x=x_axis,
            y=y_axis,
            size='market_cap_musd',
            color='color_value',
            hover_data=[
                'subnet_name',    # 0
                'netuid',         # 1
                'buy_signal',     # 2
                x_axis,           # 3
                y_axis,           # 4
                'market_cap_musd' # 5
            ],
            title="Buy Signal Analysis",
            labels={
                x_axis: x_label,
                y_axis: y_label,
                'market_cap_musd': 'Market Cap (MUSD)',
                'color_value': 'Buy Signal'
            },
            size_max=30,
            color_continuous_scale=colorscale,
            range_color=[0, 5]
        )
        
        fig.update_traces(
            marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "NetUID: %{customdata[1]}<br>" +
                         "Buy Signal: %{customdata[2]}/5 (Click to generate)<br>" +
                         f"{x_label}: %{{customdata[3]:.1f}}<br>" +
                         f"{y_label}: %{{customdata[4]:.1f}}<br>" +
                         "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                         "<extra></extra>"
        )
        
        # Add quadrant lines for percentage metrics
        if AXIS_METRICS.get(x_axis, {}).get('type') == 'percentage':
            fig.add_vline(x=0, line_dash="dash", line_color="gray")
        if AXIS_METRICS.get(y_axis, {}).get('type') == 'percentage':
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        # Update colorbar title and ticks
        fig.update_layout(
            coloraxis_colorbar=dict(
                title="Buy Signal",
                tickmode='array',
                tickvals=[0, 1, 2, 3, 4, 5],
                ticktext=['No Signal', '1 (Avoid)', '2 (Weak)', '3 (Neutral)', '4 (Good)', '5 (Strong)']
            )
        )
        
        # Add netuid labels if toggle is enabled
        if show_labels:
            annotations = []
            for idx, row in filtered_df.iterrows():
                annotations.append(
                    dict(
                        x=row[x_axis],
                        y=row[y_axis],
                        text=str(row['netuid']),
                        showarrow=False,
                        font=dict(size=10, color='black')
                    )
                )
            fig.update_layout(annotations=annotations)
        
        return fig
        
    except Exception as e:
        # Create error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"❌ Error creating chart<br>{str(e)}<br><br>Please try different axis selections",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Buy Signal Analysis - Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='white'
        )
        return fig

@callback(
    Output("volume-analysis", "figure"),
    Input("additional-category-filter", "value"),
    Input("additional-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_volume_analysis(category, mcap_range, _):
    """Update volume analysis chart based on filters."""
    try:
        # Always reload fresh data from database
        fresh_df = reload_data_with_buy_signals()
        
        # Apply category filter
        if category == "All" or category is None:
            filtered_df = fresh_df
        else:
            filtered_df = fresh_df[fresh_df['primary_category'] == category]
        
        # Apply market cap filter (in MUSD)
        if mcap_range and len(mcap_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
                (filtered_df['market_cap_musd'] <= mcap_range[1])
            ]
        
        fig = px.scatter(
            filtered_df,
            x='buy_volume_tao_1d',
            y='sell_volume_tao_1d',
            size='market_cap_musd',
            color='buy_sell_ratio',
            color_continuous_scale='RdYlGn',
            hover_data=['subnet_name', 'netuid', 'buy_volume_tao_1d', 'sell_volume_tao_1d', 'buy_sell_ratio', 'market_cap_musd'],
            title="Buy vs Sell Volume Analysis",
            labels={
                'buy_volume_tao_1d': '24h Buy Volume (TAO)',
                'sell_volume_tao_1d': '24h Sell Volume (TAO)',
                'market_cap_musd': 'Market Cap (MUSD)',
                'buy_sell_ratio': 'Buy/Sell Ratio'
            },
            size_max=30
        )
        
        fig.update_traces(
            marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "NetUID: %{customdata[1]}<br>" +
                         "Buy Volume: %{customdata[2]:.0f} TAO<br>" +
                         "Sell Volume: %{customdata[3]:.0f} TAO<br>" +
                         "Buy/Sell Ratio: %{customdata[4]:.2f}<br>" +
                         "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                         "<extra></extra>"
        )
        
        # Add diagonal line for equal buy/sell
        max_val = max(filtered_df['buy_volume_tao_1d'].max(), filtered_df['sell_volume_tao_1d'].max())
        fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode='lines', 
                                line=dict(dash='dash', color='gray'), 
                                name='Equal Buy/Sell', showlegend=False))
        
        return fig
        
    except Exception as e:
        # Create error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"❌ Error creating volume analysis<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Volume Analysis - Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='white'
        )
        return fig

@callback(
    Output("stake-distribution", "figure"),
    Input("additional-category-filter", "value"),
    Input("additional-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_stake_distribution(category, mcap_range, _):
    """Update stake distribution chart based on filters."""
    try:
        # Always reload fresh data from database
        fresh_df = reload_data_with_buy_signals()
        
        # Apply category filter
        if category == "All" or category is None:
            filtered_df = fresh_df
        else:
            filtered_df = fresh_df[fresh_df['primary_category'] == category]
        
        # Apply market cap filter (in MUSD)
        if mcap_range and len(mcap_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
                (filtered_df['market_cap_musd'] <= mcap_range[1])
            ]
        
        fig = px.scatter(
            filtered_df,
            x='stake_hhi',
            y='gini_coeff_top_100',
            size='market_cap_musd',
            color='active_stake_ratio',
            color_continuous_scale='Viridis',
            hover_data=['subnet_name', 'netuid', 'stake_hhi', 'gini_coeff_top_100', 'active_stake_ratio', 'market_cap_musd'],
            title="Stake Distribution Analysis",
            labels={
                'stake_hhi': 'Stake HHI (Concentration)',
                'gini_coeff_top_100': 'Gini Coefficient (Top 100)',
                'market_cap_musd': 'Market Cap (MUSD)',
                'active_stake_ratio': 'Active Stake Ratio (%)'
            },
            size_max=25
        )
        
        fig.update_traces(
            marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "NetUID: %{customdata[1]}<br>" +
                         "Stake HHI: %{customdata[2]:.2f}<br>" +
                         "Gini Coefficient: %{customdata[3]:.2f}<br>" +
                         "Active Stake Ratio: %{customdata[4]:.1f}%<br>" +
                         "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                         "<extra></extra>"
        )
        
        return fig
        
    except Exception as e:
        # Create error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"❌ Error creating stake distribution<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Stake Distribution - Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='white'
        )
        return fig

@callback(
    Output("network-health", "figure"),
    Input("additional-category-filter", "value"),
    Input("additional-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_network_health(category, mcap_range, _):
    """Update network health chart based on filters."""
    try:
        # Always reload fresh data from database
        fresh_df = reload_data_with_buy_signals()
        
        # Apply category filter
        if category == "All" or category is None:
            filtered_df = fresh_df
        else:
            filtered_df = fresh_df[fresh_df['primary_category'] == category]
        
        # Apply market cap filter (in MUSD)
        if mcap_range and len(mcap_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
                (filtered_df['market_cap_musd'] <= mcap_range[1])
            ]
        
        fig = px.scatter(
            filtered_df,
            x='active_validators',
            y='validator_util_pct',
            size='market_cap_musd',
            color='uid_count',
            color_continuous_scale='Plasma',
            hover_data=['subnet_name', 'netuid', 'active_validators', 'validator_util_pct', 'uid_count', 'market_cap_musd'],
            title="Network Health & Participation",
            labels={
                'active_validators': 'Active Validators',
                'validator_util_pct': 'Validator Utilization (%)',
                'market_cap_musd': 'Market Cap (MUSD)',
                'uid_count': 'Total UIDs'
            },
            size_max=25
        )
        
        fig.update_traces(
            marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "NetUID: %{customdata[1]}<br>" +
                         "Active Validators: %{customdata[2]}<br>" +
                         "Validator Utilization: %{customdata[3]:.1f}%<br>" +
                         "Total UIDs: %{customdata[4]}<br>" +
                         "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                         "<extra></extra>"
        )
        
        return fig
        
    except Exception as e:
        # Create error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"❌ Error creating network health<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Network Health - Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='white'
        )
        return fig

@callback(
    Output("tao-score-distribution", "figure"),
    Input("additional-category-filter", "value"),
    Input("additional-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_tao_score_distribution(category, mcap_range, _):
    """Update TAO-Score distribution based on momentum filters."""
    # Always reload fresh data from database
    fresh_df = reload_data_with_buy_signals()
    
    # Apply category filter
    if category == "All" or category is None:
        filtered_df = fresh_df
    else:
        filtered_df = fresh_df[fresh_df['primary_category'] == category]
    
    # Apply market cap filter (in MUSD)
    if mcap_range and len(mcap_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
            (filtered_df['market_cap_musd'] <= mcap_range[1])
        ]
    
    fig = px.histogram(
        filtered_df,
        x='tao_score',
        nbins=20,
        title="TAO-Score Distribution",
        labels={'tao_score': 'TAO-Score', 'count': 'Number of Subnets'},
        color_discrete_sequence=['#3e6ae1']
    )
    fig.update_layout(
        xaxis_title="TAO-Score",
        yaxis_title="Number of Subnets",
        showlegend=False
    )
    return fig

@callback(
    Output("validator-utilization", "figure"),
    Input("additional-category-filter", "value"),
    Input("additional-mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_validator_utilization(category, mcap_range, _):
    """Update validator utilization chart based on additional analysis filters."""
    # Always reload fresh data from database
    fresh_df = reload_data_with_buy_signals()
    
    # Apply category filter
    if category == "All" or category is None:
        filtered_df = fresh_df
    else:
        filtered_df = fresh_df[fresh_df['primary_category'] == category]
    
    # Apply market cap filter (in MUSD)
    if mcap_range and len(mcap_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
            (filtered_df['market_cap_musd'] <= mcap_range[1])
        ]
    
    # Ensure market_cap_musd is at least 0.1 for sizing
    if 'market_cap_musd' in filtered_df.columns:
        filtered_df['market_cap_musd'] = filtered_df['market_cap_musd'].fillna(0.1)
        filtered_df.loc[filtered_df['market_cap_musd'] < 0.1, 'market_cap_musd'] = 0.1
    
    fig = px.scatter(
        filtered_df,
        x='validator_util_pct',
        y='tao_score',
        size='market_cap_musd',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'validator_util_pct', 'tao_score'],
        title="Validator Utilization vs TAO-Score",
        labels={
            'validator_util_pct': 'Validator Utilization (%)',
            'tao_score': 'TAO-Score',
            'market_cap_musd': 'Market Cap (MUSD)',
            'primary_category': 'Category'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color='rgba(0,0,0,0.3)'), sizemin=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Validator Util: %{customdata[2]:.1f}%<br>" +
                     "TAO-Score: %{customdata[3]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig


@callback(
    Output("momentum-data-timestamp", "children"),
    Output("buy-signal-data-timestamp", "children"),
    Output("additional-data-timestamp", "children"),
    Input("buy-signal-refresh", "data")
)
def update_data_timestamps(_):
    """Update all data timestamps with fresh data."""
    try:
        # Load fresh data to get latest timestamp
        fresh_df = reload_data_with_buy_signals()
        latest_ts = fresh_df['metrics_timestamp'].max() if 'metrics_timestamp' in fresh_df.columns else None
        
        timestamp_text = f"Data updated: {latest_ts.strftime('%Y-%m-%d %H:%M UTC') if latest_ts else 'Unknown'}"
        return timestamp_text, timestamp_text, timestamp_text
    except Exception as e:
        error_text = f"Data updated: Error loading timestamp"
        return error_text, error_text, error_text

# Callback for collapsible quick start guide
@callback(
    Output("screener-quick-start-collapse", "is_open"),
    Output("screener-quick-start-icon", "className"),
    Input("screener-quick-start-toggle", "n_clicks"),
    State("screener-quick-start-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_screener_quick_start(n_clicks, is_open):
    if n_clicks:
        new_state = not is_open
        icon_class = "bi bi-chevron-up ms-2" if new_state else "bi bi-chevron-down ms-2"
        return new_state, icon_class
    return is_open, "bi bi-chevron-down ms-2"