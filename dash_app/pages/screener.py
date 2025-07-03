import dash
from dash import html, dcc, callback, Output, Input
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
    engine = create_engine('sqlite:///tao.sqlite', future=True)
    Session = sessionmaker(bind=engine, autoflush=False, future=True)
    with Session() as session:
        price_row = session.query(CoinGeckoPrice).order_by(CoinGeckoPrice.fetched_at.desc()).first()
        tao_price_usd = float(price_row.price_usd) if price_row and price_row.price_usd else 0.0
except Exception:
    tao_price_usd = 0.0

# Load data once for initial test (will be replaced with callback/caching)
df = load_screener_frame()
latest_ts = df['metrics_timestamp'].max() if 'metrics_timestamp' in df.columns else None

# Add buy signal scores from GPT insights
from services.gpt_insight import get_buy_signal_for_subnet
df['buy_signal'] = df['netuid'].apply(get_buy_signal_for_subnet)

# Add market_cap_usd column (in millions)
if 'market_cap_tao' in df.columns:
    df['market_cap_usd'] = df['market_cap_tao'] * tao_price_usd
    df['market_cap_usd'] = df['market_cap_usd'].fillna(0)
    df.loc[df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
    # Convert to millions USD for display
    df['market_cap_musd'] = df['market_cap_usd'] / 1_000_000

# Bubble scatter chart with better styling
fig = px.scatter(
    df,
    x='price_7d_change',
    y='price_30d_change',
    size='market_cap_musd',
    color='primary_category',
    hover_data=['subnet_name', 'netuid', 'tao_score', 'metrics_timestamp', 'primary_category', 'market_cap_musd'],
    title="Price Momentum: 7-Day vs 30-Day Change",
    labels={
        'price_7d_change': '7-Day Price Change (%)',
        'price_30d_change': '30-Day Price Change (%)',
        'market_cap_musd': 'Market Cap (MUSD)',
        'primary_category': 'Category'
    },
    size_max=40
)

# Add borders and improve dot visibility
fig.update_traces(
    marker=dict(
        line=dict(width=1, color='rgba(0,0,0,0.3)'),
        sizemin=8  # Minimum dot size
    ),
    hovertemplate="<b>%{customdata[0]}</b><br>" +
                 "NetUID: %{customdata[1]}<br>" +
                 "Category: %{customdata[4]}<br>" +
                 "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                 "7d: %{x:.1f}%<br>" +
                 "30d: %{y:.1f}%<br>" +
                 "TAO-Score: %{customdata[2]:.1f}<br>" +
                 "Data: %{customdata[3]}<br>" +
                 "<extra></extra>"
)

# Add quadrant lines
fig.add_hline(y=0, line_dash="dash", line_color="gray")
fig.add_vline(x=0, line_dash="dash", line_color="gray")

# Get available categories for dropdown
categories = sorted(df['primary_category'].dropna().unique().tolist())
category_options = [{"label": "All Categories", "value": "All"}] + [
    {"label": cat, "value": cat} for cat in categories
]

# Compute max market cap for slider (set to 1000 MUSD)
mcap_max = 1000

# Create additional charts for the second section
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
    # Create a copy and ensure market_cap_musd is calculated
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        # Convert to millions USD for display
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
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Validator Util: %{customdata[2]:.1f}%<br>" +
                     "TAO-Score: %{customdata[3]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig

def create_stake_quality_analysis():
    """Create stake quality vs market cap analysis."""
    # Create a copy and ensure market_cap_musd is calculated
    viz_df = df.copy()
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        # Convert to millions USD for display
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    fig = px.scatter(
        viz_df,
        x='stake_quality',
        y='market_cap_musd',
        size='tao_score',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'stake_quality', 'market_cap_musd', 'tao_score'],
        title="Stake Quality vs Market Cap",
        labels={
            'stake_quality': 'Stake Quality',
            'market_cap_musd': 'Market Cap (MUSD)',
            'tao_score': 'TAO-Score',
            'primary_category': 'Category'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Stake Quality: %{customdata[2]:.1f}<br>" +
                     "Market Cap: $%{customdata[3]:.1f}M USD<br>" +
                     "TAO-Score: %{customdata[4]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig

def create_buy_signal_analysis():
    """Create TAO-Score vs net flow analysis with buy signal heatmap."""
    # Create a copy of the dataframe for visualization
    viz_df = df.copy()
    
    # Ensure market_cap_musd is calculated
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        # Convert to millions USD for display
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    # Create color mapping: buy signal if available, grey if not
    # Use buy_signal as color, but handle missing values
    viz_df['color_value'] = viz_df['buy_signal'].fillna(0)  # 0 for grey (no signal)
    
    # Create custom color scale: grey for 0, then heatmap colors for 1-5
    import plotly.colors as pc
    
    # Create custom colorscale: grey for 0, then sequential colors for 1-5
    colorscale = [
        [0, 'lightgrey'],      # 0 = no signal (grey)
        [0.2, '#ff7f7f'],      # 1 = red (avoid)
        [0.4, '#ffbf7f'],      # 2 = orange (weak)
        [0.6, '#ffff7f'],      # 3 = yellow (neutral)
        [0.8, '#7fff7f'],      # 4 = light green (good)
        [1.0, '#007f00']       # 5 = dark green (strong buy)
    ]
    
    fig = px.scatter(
        viz_df,
        x='tao_score',
        y='flow_24h',
        size='market_cap_tao',
        color='color_value',
        hover_data=[
            'subnet_name',    # 0
            'netuid',         # 1
            'buy_signal',     # 2
            'tao_score',      # 3
            'flow_24h',       # 4
            'market_cap_tao'  # 5
        ],
        title="TAO-Score vs Net Flow (Buy Signal Heatmap)",
        labels={
            'tao_score': 'TAO-Score',
            'flow_24h': 'Net Flow 24h (TAO)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'color_value': 'Buy Signal'
        },
        size_max=30,
        color_continuous_scale=colorscale,
        range_color=[0, 5]
    )
    
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Buy Signal: %{customdata[2]}/5 (Click to generate)<br>" +
                     "TAO-Score: %{x:.1f}<br>" +
                     "Net Flow: %{y:,.0f} TAO<br>" +
                     "Market Cap: %{marker.size:.0f} TAO<br>" +
                     "<extra></extra>"
    )
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=50, line_dash="dash", line_color="gray")  # Neutral TAO-Score
    
    # Update colorbar title and ticks
    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Buy Signal",
            tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5],
            ticktext=['No Signal', '1 (Avoid)', '2 (Weak)', '3 (Neutral)', '4 (Good)', '5 (Strong)']
        )
    )
    
    return fig

# Create the additional charts
tao_score_fig = create_tao_score_distribution()
validator_fig = create_validator_utilization()
stake_quality_fig = create_stake_quality_analysis()
buy_signal_fig = create_buy_signal_analysis()

layout = html.Div([
    html.H2("Subnet Screener", className="mt-4 mb-2"),
    html.P("Visual one-glance hunt for undervalued / high-momentum subnets.", className="mb-3"),
    
    # Section 1: Price Momentum Analysis
    dbc.Card([
        dbc.CardHeader([
            html.H4("Price Momentum Analysis", className="mb-0", id="price-momentum-header"),
            html.Small("7-Day vs 30-Day Price Changes", className="text-muted")
        ]),
        dbc.CardBody([
            # Filters
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id="category-filter",
                        options=category_options,
                        value="All",
                        clearable=False,
                        placeholder="Category"
                    )
                ], width=3),
                dbc.Col([
                    html.Small("TAO-Score Filter", className="text-muted mb-1 d-block"),
                    dbc.ButtonGroup([
                        dbc.Button("All", id="score-all", color="outline-primary", n_clicks=0),
                        dbc.Button("≥70", id="score-high", color="outline-success", n_clicks=0),
                        dbc.Button("≥40", id="score-medium", color="outline-warning", n_clicks=0),
                    ])
                ], width=3),
                dbc.Col([
                    html.Small("Market Cap Range (MUSD)", className="text-muted mb-1 d-block"),
                    dcc.RangeSlider(
                        id="mcap-slider",
                        min=0,
                        max=mcap_max,
                        step=10,
                        value=[0, mcap_max],
                        marks={0: '0', int(mcap_max): f"${int(mcap_max)}M"},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], width=4),
            ], className="mb-3"),
            
            # Data timestamp
            html.Div([
                html.Small(f"Data updated: {latest_ts.strftime('%Y-%m-%d %H:%M UTC') if latest_ts else 'Unknown'}", id="data-timestamp", className="text-muted")
            ], className="mb-3"),
            
            # Chart
            dcc.Graph(id="bubble-scatter-chart", figure=fig, style={"height": "600px"}),
        ])
    ], className="mb-4"),
    
    # Section 2: Buy Signal Analysis
    dbc.Card([
        dbc.CardHeader([
            html.H4("Buy Signal Analysis", className="mb-0", id="buy-signal-header"),
            html.Small("TAO-Score vs Net Flow with AI-Generated Buy Signals", className="text-muted"),
            html.Div([
                html.P("💡 Click on any grey dot to generate AI insights. Insights will appear below the graph.", 
                       className="text-danger mb-1", style={"fontSize": "14px"}),
                html.P("⏱️ Please wait a few seconds for the AI analysis to complete.", 
                       className="text-danger mb-0", style={"fontSize": "14px"})
            ], className="mt-2")
        ]),
        dbc.CardBody([
            # Buy Signal Chart
            dcc.Graph(
                id="buy-signal-analysis",
                figure=buy_signal_fig,
                style={"height": "500px"}
            ),
            # Insight display area
            html.Div(id="insight-display", className="mt-3")
        ])
    ], className="mb-4"),
    
    # Section 3: Additional Analysis
    dbc.Card([
        dbc.CardHeader([
            html.H4("Additional Analysis", className="mb-0", id="additional-analysis-header"),
            html.Small("Network Health & Performance Metrics", className="text-muted")
        ]),
        dbc.CardBody([
            # First row: TAO-Score Distribution and Validator Utilization
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
                        id="validator-utilization",
                        figure=validator_fig,
                        style={"height": "400px"}
                    )
                ], width=6),
            ], className="mb-4"),
            
            # Second row: Stake Quality Analysis
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="stake-quality-analysis",
                        figure=stake_quality_fig,
                        style={"height": "400px"}
                    )
                ], width=12),
            ], className="mb-4"),
        ])
    ], className="mb-4"),
    # Store for buy signal refresh
    dcc.Store(id="buy-signal-refresh"),
    # Tooltips for section headers
    dbc.Tooltip(
        "Scatter plot showing 7-day vs 30-day price changes. Dot size represents market cap. "
        "Quadrants: Top-right (bullish), Top-left (short-term momentum), "
        "Bottom-right (recovery), Bottom-left (bearish).",
        target="price-momentum-header",
        placement="top"
    ),
    dbc.Tooltip(
        "Scatter plot showing TAO-Score vs 24h net flow. Color indicates AI-generated buy signal: "
        "Grey = No signal, Red = Avoid (1), Orange = Weak (2), Yellow = Neutral (3), "
        "Light Green = Good (4), Dark Green = Strong Buy (5). Click dots to generate insights.",
        target="buy-signal-header",
        placement="top"
    ),
    dbc.Tooltip(
        "Additional metrics: TAO-Score distribution histogram, validator utilization vs TAO-Score, "
        "and stake quality vs market cap analysis.",
        target="additional-analysis-header",
        placement="top"
    ),
])

# Callback to update chart based on all filters
@callback(
    Output("bubble-scatter-chart", "figure"),
    Input("category-filter", "value"),
    Input("score-all", "n_clicks"),
    Input("score-high", "n_clicks"),
    Input("score-medium", "n_clicks"),
    Input("mcap-slider", "value")
)
def update_chart(category, score_all, score_high, score_medium, mcap_range):
    """Update chart based on all filters."""
    # Determine which score filter is active
    ctx = dash.callback_context
    score_filter = "All"
    if ctx.triggered:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id == "score-high":
            score_filter = "≥70"
        elif triggered_id == "score-medium":
            score_filter = "≥40"
    
    # Apply category filter
    if category == "All" or category is None:
        filtered_df = df
    else:
        filtered_df = df[df['primary_category'] == category]
    
    # Apply TAO-Score filter
    if score_filter == "≥70":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 70]
    elif score_filter == "≥40":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 40]
    
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
    
    # Create updated figure
    fig = px.scatter(
        filtered_df,
        x='price_7d_change',
        y='price_30d_change',
        size='market_cap_musd',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'tao_score', 'metrics_timestamp', 'primary_category', 'market_cap_musd'],
        title="Price Momentum: 7-Day vs 30-Day Change",
        labels={
            'price_7d_change': '7-Day Price Change (%)',
            'price_30d_change': '30-Day Price Change (%)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'primary_category': 'Category'
        },
        size_max=40
    )
    
    # Add borders and improve dot visibility
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=8  # Minimum dot size
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Category: %{customdata[4]}<br>" +
                     "Market Cap: $%{customdata[5]:.1f}M USD<br>" +
                     "7d: %{x:.1f}%<br>" +
                     "30d: %{y:.1f}%<br>" +
                     "TAO-Score: %{customdata[2]:.1f}<br>" +
                     "Data: %{customdata[3]}<br>" +
                     "<extra></extra>"
    )
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    return fig

# Additional callbacks for the new charts
@callback(
    Output("tao-score-distribution", "figure"),
    Input("category-filter", "value"),
    Input("score-all", "n_clicks"),
    Input("score-high", "n_clicks"),
    Input("score-medium", "n_clicks"),
    Input("mcap-slider", "value")
)
def update_tao_score_distribution(category, score_all, score_high, score_medium, mcap_range):
    """Update TAO-Score distribution based on filters."""
    # Apply same filtering logic as main chart
    ctx = dash.callback_context
    score_filter = "All"
    if ctx.triggered:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id == "score-high":
            score_filter = "≥70"
        elif triggered_id == "score-medium":
            score_filter = "≥40"
    
    if category == "All" or category is None:
        filtered_df = df
    else:
        filtered_df = df[df['primary_category'] == category]
    
    if score_filter == "≥70":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 70]
    elif score_filter == "≥40":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 40]
    
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
    Input("category-filter", "value"),
    Input("score-all", "n_clicks"),
    Input("score-high", "n_clicks"),
    Input("score-medium", "n_clicks"),
    Input("mcap-slider", "value")
)
def update_validator_utilization(category, score_all, score_high, score_medium, mcap_range):
    """Update validator utilization chart based on filters."""
    # Apply same filtering logic
    ctx = dash.callback_context
    score_filter = "All"
    if ctx.triggered:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id == "score-high":
            score_filter = "≥70"
        elif triggered_id == "score-medium":
            score_filter = "≥40"
    
    if category == "All" or category is None:
        filtered_df = df
    else:
        filtered_df = df[df['primary_category'] == category]
    
    if score_filter == "≥70":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 70]
    elif score_filter == "≥40":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 40]
    
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
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Validator Util: %{customdata[2]:.1f}%<br>" +
                     "TAO-Score: %{customdata[3]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig

@callback(
    Output("stake-quality-analysis", "figure"),
    Input("category-filter", "value"),
    Input("score-all", "n_clicks"),
    Input("score-high", "n_clicks"),
    Input("score-medium", "n_clicks"),
    Input("mcap-slider", "value")
)
def update_stake_quality_analysis(category, score_all, score_high, score_medium, mcap_range):
    """Update stake quality analysis chart based on filters."""
    # Apply same filtering logic
    ctx = dash.callback_context
    score_filter = "All"
    if ctx.triggered:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id == "score-high":
            score_filter = "≥70"
        elif triggered_id == "score-medium":
            score_filter = "≥40"
    
    if category == "All" or category is None:
        filtered_df = df
    else:
        filtered_df = df[df['primary_category'] == category]
    
    if score_filter == "≥70":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 70]
    elif score_filter == "≥40":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 40]
    
    if mcap_range and len(mcap_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
            (filtered_df['market_cap_musd'] <= mcap_range[1])
        ]
    
    # Ensure tao_score is at least 1 for sizing
    if 'tao_score' in filtered_df.columns:
        filtered_df['tao_score'] = filtered_df['tao_score'].fillna(1)
        filtered_df.loc[filtered_df['tao_score'] < 1, 'tao_score'] = 1
    
    fig = px.scatter(
        filtered_df,
        x='stake_quality',
        y='market_cap_musd',
        size='tao_score',
        color='primary_category',
        hover_data=['subnet_name', 'netuid', 'stake_quality', 'market_cap_musd', 'tao_score'],
        title="Stake Quality vs Market Cap",
        labels={
            'stake_quality': 'Stake Quality',
            'market_cap_musd': 'Market Cap (MUSD)',
            'tao_score': 'TAO-Score',
            'primary_category': 'Category'
        },
        size_max=30
    )
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Stake Quality: %{customdata[2]:.1f}<br>" +
                     "Market Cap: $%{customdata[3]:.1f}M USD<br>" +
                     "TAO-Score: %{customdata[4]:.1f}<br>" +
                     "<extra></extra>"
    )
    return fig

@callback(
    Output("buy-signal-analysis", "figure"),
    Input("category-filter", "value"),
    Input("score-all", "n_clicks"),
    Input("score-high", "n_clicks"),
    Input("score-medium", "n_clicks"),
    Input("mcap-slider", "value"),
    Input("buy-signal-refresh", "data")
)
def update_buy_signal_analysis(category, score_all, score_high, score_medium, mcap_range, _):
    """Update buy signal analysis chart based on filters."""
    # Apply same filtering logic
    ctx = dash.callback_context
    score_filter = "All"
    if ctx.triggered:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id == "score-high":
            score_filter = "≥70"
        elif triggered_id == "score-medium":
            score_filter = "≥40"
    
    if category == "All" or category is None:
        filtered_df = df
    else:
        filtered_df = df[df['primary_category'] == category]
    
    if score_filter == "≥70":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 70]
    elif score_filter == "≥40":
        filtered_df = filtered_df[filtered_df['tao_score'] >= 40]
    
    if mcap_range and len(mcap_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['market_cap_musd'] >= mcap_range[0]) & 
            (filtered_df['market_cap_musd'] <= mcap_range[1])
        ]
    
    # Use filtered_df directly (like Price Momentum chart) instead of copying
    viz_df = filtered_df
    
    # Reload buy signals from database to get latest values
    viz_df['buy_signal'] = viz_df['netuid'].apply(get_buy_signal_for_subnet)
    
    # Ensure market_cap_musd and market_cap_tao are calculated if not already present
    if 'market_cap_tao' not in viz_df.columns and 'market_cap_musd' in viz_df.columns:
        # Calculate market_cap_tao from market_cap_musd
        viz_df['market_cap_tao'] = (viz_df['market_cap_musd'] * 1_000_000) / tao_price_usd
        viz_df['market_cap_tao'] = viz_df['market_cap_tao'].fillna(0)
        viz_df.loc[viz_df['market_cap_tao'] < 0, 'market_cap_tao'] = 0
    elif 'market_cap_musd' not in viz_df.columns and 'market_cap_tao' in viz_df.columns:
        # Calculate market_cap_musd from market_cap_tao
        viz_df['market_cap_usd'] = viz_df['market_cap_tao'] * tao_price_usd
        viz_df['market_cap_usd'] = viz_df['market_cap_usd'].fillna(0)
        viz_df.loc[viz_df['market_cap_usd'] < 0, 'market_cap_usd'] = 0
        # Convert to millions USD for display
        viz_df['market_cap_musd'] = viz_df['market_cap_usd'] / 1_000_000
    
    # Create color mapping: buy signal if available, grey if not
    viz_df['color_value'] = viz_df['buy_signal'].fillna(0)  # 0 for grey (no signal)
    
    # Create custom color scale: grey for 0, then heatmap colors for 1-5
    colorscale = [
        [0, 'lightgrey'],      # 0 = no signal (grey)
        [0.2, '#ff7f7f'],      # 1 = red (avoid)
        [0.4, '#ffbf7f'],      # 2 = orange (weak)
        [0.6, '#ffff7f'],      # 3 = yellow (neutral)
        [0.8, '#7fff7f'],      # 4 = light green (good)
        [1.0, '#007f00']       # 5 = dark green (strong buy)
    ]
    
    # Ensure market_cap_tao is at least 1 for sizing
    if 'market_cap_tao' in viz_df.columns:
        viz_df['market_cap_tao'] = viz_df['market_cap_tao'].fillna(1)
        viz_df.loc[viz_df['market_cap_tao'] < 1, 'market_cap_tao'] = 1
    
    fig = px.scatter(
        viz_df,
        x='tao_score',
        y='flow_24h',
        size='market_cap_tao',
        color='color_value',
        hover_data=[
            'subnet_name',    # 0
            'netuid',         # 1
            'buy_signal',     # 2
            'tao_score',      # 3
            'flow_24h',       # 4
            'market_cap_tao'  # 5
        ],
        title="TAO-Score vs Net Flow (Buy Signal Heatmap)",
        labels={
            'tao_score': 'TAO-Score',
            'flow_24h': 'Net Flow 24h (TAO)',
            'market_cap_musd': 'Market Cap (MUSD)',
            'color_value': 'Buy Signal'
        },
        size_max=30,
        color_continuous_scale=colorscale,
        range_color=[0, 5]
    )
    
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color='rgba(0,0,0,0.3)'),
            sizemin=5
        ),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                     "NetUID: %{customdata[1]}<br>" +
                     "Buy Signal: %{customdata[2]}/5 (Click to generate)<br>" +
                     "TAO-Score: %{x:.1f}<br>" +
                     "Net Flow: %{y:,.0f} TAO<br>" +
                     "Market Cap: %{marker.size:.0f} TAO<br>" +
                     "<extra></extra>"
    )
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=50, line_dash="dash", line_color="gray")  # Neutral TAO-Score
    
    # Update colorbar title and ticks
    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Buy Signal",
            tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5],
            ticktext=['No Signal', '1 (Avoid)', '2 (Weak)', '3 (Neutral)', '4 (Good)', '5 (Strong)']
        )
    )
    
    return fig

@callback(
    Output("insight-display", "children"),
    Output("buy-signal-refresh", "data"),
    Input("buy-signal-analysis", "clickData")
)
def handle_buy_signal_click(click_data):
    """Handle clicks on buy signal chart to generate GPT insights and update buy signal."""
    if not click_data or 'points' not in click_data:
        return html.Div("Click on a subnet dot to generate AI insights", className="text-muted"), None
    try:
        # Extract subnet info from click data
        point = click_data['points'][0]
        netuid = point['customdata'][1]  # netuid is in customdata[1]
        subnet_name = point['customdata'][0]  # subnet_name is in customdata[0]
        # Generate GPT insight
        insight = get_insight(netuid)
        # Extract buy signal from insight
        buy_signal = extract_buy_signal_from_insight(insight)
        # Save buy signal to latest metrics_snap for this netuid
        if buy_signal is not None:
            with get_db() as session:
                snap = session.query(MetricsSnap).filter_by(netuid=netuid).order_by(MetricsSnap.timestamp.desc()).first()
                if snap:
                    snap.buy_signal = buy_signal
                    session.commit()
        # Format the insight display
        return html.Div([
            html.H5(f"AI Analysis for {subnet_name} (NetUID: {netuid})", className="mb-3"),
            html.Div([
                html.P(insight, className="mb-0", style={"whiteSpace": "pre-wrap", "fontSize": "14px"})
            ], className="p-3 bg-light rounded")
        ]), time.time()  # Use timestamp to force refresh
    except Exception as e:
        return html.Div([
            html.H5("Error Generating Insight", className="mb-3 text-danger"),
            html.P(f"Could not generate insight: {str(e)}", className="text-muted")
        ]), None 