"""
Subnet Detail Page - Investor-focused analytics.
Sprint 5: Enhanced with price action, flow metrics, and peer comparisons.
"""

import dash
from dash import html, dcc, Input, Output, callback, State
import dash_bootstrap_components as dbc
from services.db import get_db
from services.gpt_insight import gpt_insight_service
from services.taoapp_cache import taoapp_cache_service
from models import MetricsSnap, SubnetMeta, CategoryStats
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def create_header_bar(netuid: int) -> dbc.Card:
    """Create the header bar with subnet logo, name, category, and external links."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H3(f"Subnet {netuid}", className="mb-1"),
                    html.Span(id="subnet-name", children="Loading...", className="text-primary fw-bold")
                ], width=6),
                dbc.Col([
                    html.Div([
                        dbc.Badge(id="subnet-category", children="Loading...", color="primary", className="me-2"),
                        html.A(
                            "Visit site ↗",
                            id="visit-site-link",
                            href="#",
                            className="text-decoration-none me-2",
                            target="_blank"
                        ),
                        html.A(
                            "GitHub",
                            id="github-link",
                            href="#",
                            className="text-decoration-none",
                            target="_blank"
                        )
                    ], className="text-end")
                ], width=6)
            ])
        ])
    ], className="mb-3")

def create_overview_card(netuid: int) -> dbc.Card:
    """Create the overview card with price, FDV, market cap, and TAO stake."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span(id="overview-chevron", children="▼", className="me-2", style={"fontSize": "1.2rem", "color": "#007bff", "cursor": "pointer", "fontWeight": "bold"}),
                html.H5("Overview", className="mb-0", style={"cursor": "pointer"})
            ], id="overview-toggle", style={"cursor": "pointer"}),
            html.Div([
                html.Small(id="overview-timestamp", children="Loading...", className="text-muted")
            ], className="text-end")
        ], className="d-flex justify-content-between align-items-start", style={"backgroundColor": "#f8f9fa"}),
        dbc.Collapse([
            dbc.CardBody([
                html.Div(id="overview-content", children=[
                    dbc.Spinner(html.Div("Loading overview data..."), size="sm")
                ])
            ], className="overview-card")
        ], id="overview-collapse", is_open=True)
    ], className="mb-3")

def create_volume_flow_card(netuid: int) -> dbc.Card:
    """Create the volume and flow card with trading activity metrics."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span(id="volume-flow-chevron", children="▼", className="me-2", style={"fontSize": "1.2rem", "color": "#007bff", "cursor": "pointer", "fontWeight": "bold"}),
                html.H5("Volume & Flow", className="mb-0", style={"cursor": "pointer"})
            ], id="volume-flow-toggle", style={"cursor": "pointer"}),
            html.Div([
                html.Small(id="volume-flow-timestamp", children="Loading...", className="text-muted")
            ], className="text-end")
        ], className="d-flex justify-content-between align-items-start", style={"backgroundColor": "#f8f9fa"}),
        dbc.Collapse([
            dbc.CardBody([
                html.Div(id="volume-flow-content", children=[
                    dbc.Spinner(html.Div("Loading volume data..."), size="sm")
                ])
            ])
        ], id="volume-flow-collapse", is_open=True)
    ], className="mb-3")

def create_geckoterminal_pool_widget(netuid: int) -> dbc.Card:
    """Create GeckoTerminal pool data widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Live Market Data", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div([
                html.P("Loading market data...", className="text-muted"),
                html.Iframe(
                    src=f"https://www.geckoterminal.com/bittensor/pools/0-{netuid}",
                    style={
                        'width': '100%',
                        'height': '600px',
                        'border': 'none',
                        'borderRadius': '8px'
                    },
                    title=f"GeckoTerminal Pool Data for Subnet {netuid}"
                ),
                html.Div([
                    html.Small(
                        "Data provided by GeckoTerminal",
                        className="text-muted"
                    ),
                    html.Br(),
                    html.A(
                        "View on GeckoTerminal ↗",
                        href=f"https://www.geckoterminal.com/bittensor/pools/0-{netuid}",
                        target="_blank",
                        className="text-decoration-none"
                    )
                ], className="mt-2 text-center")
            ])
        ])
    ], className="mb-3")

def create_metrics_grid(netuid: int) -> dbc.Card:
    """Create the key metrics grid with 5 tiles for investor metrics."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span(id="metrics-chevron", children="▼", className="me-2", style={"fontSize": "1.2rem", "color": "#007bff", "cursor": "pointer", "fontWeight": "bold"}),
                html.H5("Key Metrics", className="mb-0", style={"cursor": "pointer"})
            ], id="metrics-toggle", style={"cursor": "pointer"}),
            html.Div([
                html.Small(id="metrics-timestamp", children="Loading...", className="text-muted")
            ], className="text-end")
        ], className="d-flex justify-content-between align-items-start", style={"backgroundColor": "#f8f9fa"}),
        dbc.Collapse([
        dbc.CardBody([
            # First row: TAO-Score, Stake Quality, Reserve Momentum
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("TAO-Score", className="card-title", id="tao-score-label"),
                            html.H5(id="tao-score", children="--", className="mb-1"),
                            html.Small("composite metric", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Stake Quality", className="card-title", id="stake-quality-label"),
                            html.H5(id="stake-quality", children="--", className="mb-1"),
                            html.Small("vs category median", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Reserve Momentum", className="card-title", id="reserve-momentum-label"),
                            html.H5(id="reserve-momentum", children="--", className="mb-1"),
                            html.Small("Δ TAO-in 24h / supply", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4)
            ], className="mb-3"),
            
            # Second row: Validator Utilization, Consensus Alignment, Active-Stake Ratio
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Validator Util", className="card-title", id="validator-util-label"),
                            html.H5(id="validator-util", children="--", className="mb-1"),
                            html.Small("active / max (utilization %)", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Consensus Alignment", className="card-title", id="consensus-alignment-label"),
                            html.H5(id="consensus-alignment", children="--", className="mb-1"),
                            html.Small("stake-weighted %", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Active-Stake Ratio", className="card-title", id="active-stake-label"),
                            html.H5(id="active-stake", children="--", className="mb-1"),
                            html.Small("% of total stake", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4)
            ], className="mb-3"),
            
            # Third row: Annual Inflation, Emission Progress
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Annual Inflation", className="card-title", id="annual-inflation-label"),
                            html.H5(id="annual-inflation", children="--", className="mb-1"),
                            html.Small("α-token supply growth", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Emission Progress", className="card-title", id="emission-progress-label"),
                            html.Div(id="emission-progress-gauge", children="--"),
                            html.Small("of max α-supply", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=6)
            ], className="mb-3")
        ], className="metrics-grid"),
        
        # Tooltips - Updated to match v1.1 spec exactly
        dbc.Tooltip(
            "TAO-Score 0-100 – composite health index. 35% decentralisation, 20% validator-utilisation, 15% consensus integrity, 15% active-stake, 10% inflation sanity (8% target), 5% 7-day price momentum. Weights auto-rebalance if some data is missing. ≥70 green, 40-70 amber, <40 red.",
            target="tao-score-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Decentralisation (0-100). Higher = more even stake distribution.",
            target="stake-quality-label",
            placement="top"
        ),
        dbc.Tooltip(
            "24h net TAO-reserve change ÷ market-cap. ↑ inflow, ↓ outflow.",
            target="reserve-momentum-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Active validators ÷ max allowed (64). Shows capacity usage.",
            target="validator-util-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Stake-weighted % of validators whose consensus score is within two standard deviations of the subnet mean.",
            target="consensus-alignment-label",
            placement="top"
        ),
        dbc.Tooltip(
            "% of all bonded TAO that sits on validators currently online (validator-permit = True). A low ratio means most stake is idle.",
            target="active-stake-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Projected α-supply growth if current mint schedule continues.",
            target="annual-inflation-label",
            placement="top"
        ),
        dbc.Tooltip(
            "% of max α-supply already minted.",
            target="emission-progress-label",
            placement="top"
        )
        ], id="metrics-collapse", is_open=True)
    ], className="mb-3")

def create_gpt_insight_panel(netuid: int) -> dbc.Card:
    """Create the GPT insight panel with peer comparisons."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span(id="gpt-insight-chevron", children="▲", className="me-2", style={"fontSize": "1.2rem", "color": "#007bff", "cursor": "pointer", "fontWeight": "bold"}),
                html.H5("AI Analysis", className="mb-0", style={"cursor": "pointer"}),
                html.Small("Powered by GPT-4o (v5)", className="text-muted")
            ], id="gpt-insight-toggle", style={"cursor": "pointer"}),
            html.Div([
                html.Small(id="gpt-insight-timestamp", children="Loading...", className="text-muted")
            ], className="text-end")
        ], className="d-flex justify-content-between align-items-start", style={"backgroundColor": "#f8f9fa"}),
        dbc.Collapse([
            dbc.CardBody([
                html.Div(id="gpt-insight", children=[
                    dbc.Spinner(html.Div("Generating AI insight..."), size="sm"),
                    html.Small("This may take a few seconds", className="text-muted d-block mt-2")
                ])
            ])
        ], id="gpt-insight-collapse", is_open=False)
    ], className="mb-3")

def create_enriched_description(netuid: int) -> dbc.Card:
    """Create the enriched description panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Description", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="description", children=[
                dbc.Spinner(html.Div("Loading description..."), size="sm")
            ])
        ])
    ], className="mb-3")

def create_tabs(netuid: int) -> dbc.Card:
    """Create the tabbed interface."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Tabs([
                dbc.Tab([
                    html.Div(id="holders-content", children=[
                        html.P("Click to load holders data", className="text-muted text-center py-4")
                    ])
                ], label="Holders", tab_id="holders"),
                dbc.Tab([
                    html.Div(id="validators-content", children=[
                        html.P("Click to load validators data", className="text-muted text-center py-4")
                    ])
                ], label="Validators", tab_id="validators")
            ], id="tabs")
        ])
    ], className="mb-3")

def create_footer(netuid: int) -> html.Div:
    """Create the footer with timestamp."""
    return html.Div([
        html.Small(id="footer", children="Loading...", className="text-muted")
    ], className="text-center mt-4")

def create_holders_validators_section(netuid: int) -> dbc.Card:
    """Create the holders and validators section."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Holders & Validators", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="holders-validators-content", children="Loading...")
        ])
    ], className="mb-4")

def create_subnet_detail_layout(netuid: int | None = None) -> html.Div:
    """Create the complete subnet detail layout."""
    if netuid is None:
        return html.Div([
            html.P("Select a subnet to view detailed analytics.", className="text-center text-muted mt-5"),
            html.Div(id="subnet-detail-content")
        ])
    
    return html.Div([
        # Header bar
        create_header_bar(netuid),
        
        # GPT insight panel (moved above Overview)
        create_gpt_insight_panel(netuid),
        
        # Overview card
        create_overview_card(netuid),
        
        # Volume & Flow card
        create_volume_flow_card(netuid),
        
        # GeckoTerminal Pool Data Widget
        create_geckoterminal_pool_widget(netuid),
        
        # Metrics grid
        create_metrics_grid(netuid),
        
        # Enriched description
        create_enriched_description(netuid),
        
        # Tabs
        create_tabs(netuid),
        
        # Footer
        create_footer(netuid)
    ])

# Callbacks
@callback(
    Output("subnet-detail-content", "children"),
    Input("url", "search")
)
def update_subnet_detail(search):
    """Update the subnet detail content based on URL search parameters."""
    if not search:
        return html.Div("No subnet selected", className="text-center py-5")
    
    # Parse netuid from search parameters
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return html.Div("Invalid subnet ID", className="text-center py-5")
        
        return create_subnet_detail_layout(netuid)
        
    except (ValueError, KeyError, IndexError):
        return html.Div("Invalid subnet ID", className="text-center py-5")

@callback(
    Output("subnet-name", "children"),
    Input("url", "search")
)
def update_subnet_name(search):
    """Update the subnet name in the header."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Get subnet metadata
        with get_db() as session:
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            if not subnet_meta or subnet_meta.subnet_name is None:
                return "Unnamed Subnet"
            
            return subnet_meta.subnet_name
        
    except Exception as e:
        logger.error(f"Error updating subnet name: {e}")
        return "Error loading name"

@callback(
    Output("subnet-category", "children"),
    Input("url", "search")
)
def update_subnet_category(search):
    """Update the subnet category in the header."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Get subnet metadata
        with get_db() as session:
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            if not subnet_meta or subnet_meta.primary_category is None:
                return "Uncategorized"
            
            return subnet_meta.primary_category
        
    except Exception as e:
        logger.error(f"Error updating subnet category: {e}")
        return "Error loading category"

@callback(
    [Output("overview-content", "children"),
     Output("overview-timestamp", "children")],
    Input("url", "search")
)
def update_overview(search):
    """Update the overview card with price action and flow data."""
    if not search:
        return "No subnet selected", "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID", "Invalid subnet ID"
        
        # Get latest metrics from database
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics:
                return html.Div("No overview data available", className="text-muted")
            
            # Get latest TAO price in USD for conversions
            from models import CoinGeckoPrice
            tao_price_row = session.query(CoinGeckoPrice).order_by(CoinGeckoPrice.fetched_at.desc()).first()
            tao_price_usd = tao_price_row.price_usd if tao_price_row else 0
            
            # Format price data
            price = latest_metrics.price_tao
            price_formatted = f"{price:.3f}" if price is not None else "--"
            price_usd = price * tao_price_usd if price is not None and tao_price_usd > 0 else None
            price_usd_formatted = f"(${price_usd:.2f})" if price_usd is not None else ""
            
            # Format market cap
            market_cap = latest_metrics.market_cap_tao
            market_cap_formatted = f"{market_cap:,.0f}" if market_cap is not None else "--"
            market_cap_usd = market_cap * tao_price_usd if market_cap is not None and tao_price_usd > 0 else None
            market_cap_usd_formatted = f"(${market_cap_usd:,.0f})" if market_cap_usd is not None else ""
            
            # Format FDV
            fdv = latest_metrics.fdv_tao
            fdv_formatted = f"{fdv:,.0f}" if fdv is not None else "--"
            fdv_usd = fdv * tao_price_usd if fdv is not None and tao_price_usd > 0 else None
            fdv_usd_formatted = f"(${fdv_usd:,.0f})" if fdv_usd is not None else ""
            
            # Format total stake
            total_stake = latest_metrics.total_stake_tao
            total_stake_formatted = f"{total_stake:,.0f}" if total_stake is not None else "--"
            
            # Format UIDs
            uid_count = latest_metrics.uid_count
            uid_count_formatted = f"{uid_count:,}" if uid_count is not None else "--"
            
            # Format active validators
            active_validators = latest_metrics.active_validators
            active_validators_formatted = f"{active_validators}" if active_validators is not None else "--"
            
            # Format price changes
            price_1d = latest_metrics.price_1d_change
            price_7d = latest_metrics.price_7d_change
            price_30d = latest_metrics.price_30d_change
            
            price_1d_formatted = f"{price_1d:+.1f}%" if price_1d is not None else "--"
            price_7d_formatted = f"{price_7d:+.1f}%" if price_7d is not None else "--"
            price_30d_formatted = f"{price_30d:+.1f}%" if price_30d is not None else "--"
            
            # Format flow data
            tao_in = latest_metrics.tao_in
            tao_in_formatted = f"{tao_in:,.0f}" if tao_in is not None else "--"
            
            buy_volume = latest_metrics.buy_volume_tao_1d
            sell_volume = latest_metrics.sell_volume_tao_1d
            
            buy_volume_formatted = f"{buy_volume:,.0f}" if buy_volume is not None else "--"
            sell_volume_formatted = f"{sell_volume:,.0f}" if sell_volume is not None else "--"
            
            # Determine price change colors
            price_1d_color = "text-success" if price_1d is not None and float(price_1d) > 0 else "text-danger" if price_1d is not None and float(price_1d) < 0 else ""
            price_7d_color = "text-success" if price_7d is not None and float(price_7d) > 0 else "text-danger" if price_7d is not None and float(price_7d) < 0 else ""
            price_30d_color = "text-success" if price_30d is not None and float(price_30d) > 0 else "text-danger" if price_30d is not None and float(price_30d) < 0 else ""
            
            # Get timestamp for overview data
            timestamp_str = f"Updated: {latest_metrics.timestamp.strftime('%Y-%m-%d %H:%M UTC')}" if latest_metrics and latest_metrics.timestamp else "No data available"
            
            return html.Div([
                # First row: Price, Market Cap, FDV, Total Stake Weight
                dbc.Row([
                    dbc.Col([
                        html.H6("Price (α)", className="text-muted", id="price-label"),
                        html.H5([
                            f"{price_formatted} TAO" if price_formatted != "--" else "--",
                            html.Br(),
                            html.Span(price_usd_formatted, className="text-muted fs-6") if price_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("Market Cap (TAO)", className="text-muted", id="market-cap-label"),
                        html.H5([
                            f"{market_cap_formatted} TAO" if market_cap_formatted != "--" else "--",
                            html.Br(),
                            html.Span(market_cap_usd_formatted, className="text-muted fs-6") if market_cap_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("FDV (TAO)", className="text-muted", id="fdv-label"),
                        html.H5([
                            f"{fdv_formatted} TAO" if fdv_formatted != "--" else "--",
                            html.Br(),
                            html.Span(fdv_usd_formatted, className="text-muted fs-6") if fdv_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("Total-Stake Weight", className="text-muted", id="total-stake-label"),
                        html.H5(f"{total_stake_formatted} TAO" if total_stake_formatted != "--" else "--")
                    ], width=3)
                ], className="mb-3"),
                
                # Second row: Price changes and reserves
                dbc.Row([
                    dbc.Col([
                        html.H6("24 h Δ", className="text-muted", id="price-1d-label"),
                        html.H5(price_1d_formatted, className=price_1d_color)
                    ], width=3),
                    dbc.Col([
                        html.H6("7 d Δ", className="text-muted", id="price-7d-label"),
                        html.H5(price_7d_formatted, className=price_7d_color)
                    ], width=3),
                    dbc.Col([
                        html.H6("30 d Δ", className="text-muted", id="price-30d-label"),
                        html.H5(price_30d_formatted, className=price_30d_color)
                    ], width=3),
                    dbc.Col([
                        html.H6("TAO Reserves", className="text-muted", id="tao-reserves-label"),
                        html.H5(f"{tao_in_formatted} TAO" if tao_in_formatted != "--" else "--")
                    ], width=3)
                ]),
                
                # Tooltips
                dbc.Tooltip(
                    "Last traded α-token price, quoted in TAO.",
                    target="price-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Circulating α-supply × price. Economic size of the subnet token.",
                    target="market-cap-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "α-price × max α-supply (fully-diluted valuation).",
                    target="fdv-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Total validator bond weight. > circulating TAO is normal because weights include locked supply.",
                    target="total-stake-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change over 24h.",
                    target="price-1d-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change over 7 days.",
                    target="price-7d-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change over 30 days.",
                    target="price-30d-label",
                    placement="top"
                ),

                dbc.Tooltip(
                    "TAO locked in the subnet's reserve pool.",
                    target="tao-reserves-label",
                    placement="top"
                )
            ]), timestamp_str
        
    except Exception as e:
        logger.error(f"Error updating overview: {e}")
        return "Error loading overview data", "Error loading timestamp"

@callback(
    [Output("tao-score", "children"),
     Output("stake-quality", "children"),
     Output("reserve-momentum", "children"),
     Output("validator-util", "children"),
     Output("consensus-alignment", "children"),
     Output("active-stake", "children"),
     Output("annual-inflation", "children"),
     Output("emission-progress-gauge", "children"),
     Output("metrics-timestamp", "children")],
    Input("url", "search")
)
def update_metrics_grid(search):
    """Update the metrics grid with peer comparisons and ranking badges."""
    if not search:
        return "--", "--", "--", "--", "--", "--", "--", "--", "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "--", "--", "--"
        
        # Get latest metrics and category stats
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics:
                return "--", "--", "--"
            
            # Get category stats for peer comparison
            category_stats = None
            if latest_metrics.category is not None:
                category_stats = session.query(CategoryStats).filter(CategoryStats.category == latest_metrics.category).first()
            
            # Format stake quality with peer comparison and ranking badge
            stake_quality = latest_metrics.stake_quality
            if stake_quality is not None:
                # Main metric with peer comparison
                if category_stats is not None and category_stats.median_stake_quality is not None:
                    median = category_stats.median_stake_quality
                    if stake_quality > median:
                        stake_quality_formatted = f"{stake_quality:.1f} ↑"
                    elif stake_quality < median:
                        stake_quality_formatted = f"{stake_quality:.1f} ↓"
                    else:
                        stake_quality_formatted = f"{stake_quality:.1f} ="
                else:
                    stake_quality_formatted = f"{stake_quality:.1f}"
                
                # Add ranking badge if available
                if latest_metrics.stake_quality_rank_pct is not None:
                    rank_badge = html.Span(
                        f"Top {latest_metrics.stake_quality_rank_pct}%",
                        className="badge bg-success ms-2",
                        style={"fontSize": "0.7em"}
                    )
                    stake_quality_formatted = html.Div([
                        html.Span(stake_quality_formatted),
                        rank_badge
                    ])
            else:
                stake_quality_formatted = "--"
            
            # Format reserve momentum with ranking badge
            reserve_momentum = latest_metrics.reserve_momentum
            if reserve_momentum is not None:
                if reserve_momentum == 0.0:
                    momentum_formatted = "0.00"
                else:
                    momentum_formatted = f"{reserve_momentum:.2f}"
                
                # Add ranking badge if available
                if latest_metrics.momentum_rank_pct is not None:
                    rank_badge = html.Span(
                        f"Top {latest_metrics.momentum_rank_pct}%",
                        className="badge bg-info ms-2",
                        style={"fontSize": "0.7em"}
                    )
                    momentum_formatted = html.Div([
                        html.Span(momentum_formatted),
                        rank_badge
                    ])
            else:
                # Show n/a when momentum is None (indicating missing historical data)
                momentum_formatted = html.Span(
                    "n/a",
                    className="text-muted",
                    title="Momentum shown after 48h of data"
                )
            
            # Format active validators with utilization badge
            active_validators = latest_metrics.active_validators
            if active_validators is not None:
                validators_formatted = f"{active_validators}"
                
                # Add utilization badge if available
                if latest_metrics.validator_util_pct is not None:
                    util_badge = html.Span(
                        f"{latest_metrics.validator_util_pct}% util",
                        className="badge bg-warning ms-2",
                        style={"fontSize": "0.7em"}
                    )
                    validators_formatted = html.Div([
                        html.Span(validators_formatted),
                        util_badge
                    ])
            else:
                validators_formatted = "--"
            
            # Format consensus alignment
            consensus_alignment = latest_metrics.consensus_alignment
            if consensus_alignment is not None:
                consensus_formatted = f"{consensus_alignment:.1f}%"
            else:
                consensus_formatted = "--"
            
            # Format active stake ratio
            active_stake_ratio = latest_metrics.active_stake_ratio
            if active_stake_ratio is not None:
                active_stake_formatted = f"{active_stake_ratio:.1f}%"
            else:
                active_stake_formatted = "--"
            
            # Format annual inflation with color coding
            annual_inflation = latest_metrics.emission_pct
            if annual_inflation is not None:
                # Color coding: green if <3%, yellow 3-10%, red >10%
                if annual_inflation < 3:
                    inflation_color = "text-success"
                elif annual_inflation <= 10:
                    inflation_color = "text-warning"
                else:
                    inflation_color = "text-danger"
                
                inflation_formatted = html.Span(
                    f"{annual_inflation:.2f}%",
                    className=inflation_color
                )
            else:
                inflation_formatted = "--"
            
            # Format emission progress as a gauge
            emission_progress = latest_metrics.alpha_emitted_pct
            if emission_progress is not None:
                # Create a simple text-based gauge
                gauge_width = min(100, max(0, emission_progress))
                gauge_filled = "█" * int(gauge_width / 10)
                gauge_empty = "▌" * (10 - len(gauge_filled))
                gauge_display = gauge_filled + gauge_empty
                
                progress_formatted = html.Div([
                    html.Div(gauge_display, className="font-monospace fs-5 mb-1"),
                    html.Small(f"{emission_progress:.2f}% of FDV", className="text-muted")
                ])
            else:
                progress_formatted = "--"
            
            # Format TAO-Score with color coding
            tao_score = latest_metrics.tao_score
            if tao_score is not None:
                # Color coding: green if >70, amber 40-70, red <40
                if tao_score > 70:
                    tao_color = "text-success"
                elif tao_score >= 40:
                    tao_color = "text-warning"
                else:
                    tao_color = "text-danger"
                
                tao_score_formatted = html.Span(
                    f"{tao_score:.1f}",
                    className=tao_color
                )
            else:
                tao_score_formatted = "--"
            
            # Format validator utilization with new format and color coding
            active_validators = latest_metrics.active_validators
            max_validators = latest_metrics.max_validators or 64  # Default to 64 if not set
            validator_util_pct = latest_metrics.validator_util_pct
            
            if active_validators is not None and validator_util_pct is not None:
                # Color coding: green if ≥50%, amber 25-50%, red <25%
                if validator_util_pct >= 50:
                    util_color = "text-success"
                elif validator_util_pct >= 25:
                    util_color = "text-warning"
                else:
                    util_color = "text-danger"
                
                util_formatted = html.Span(
                    f"{validator_util_pct:.1f}% util ({active_validators} / {max_validators} validators)",
                    className=util_color
                )
            else:
                util_formatted = "--"
            
            # Get timestamp for metrics data
            timestamp_str = f"Updated: {latest_metrics.timestamp.strftime('%Y-%m-%d %H:%M UTC')}" if latest_metrics and latest_metrics.timestamp else "No data available"
            
            return tao_score_formatted, stake_quality_formatted, momentum_formatted, util_formatted, consensus_formatted, active_stake_formatted, inflation_formatted, progress_formatted, timestamp_str
        
    except Exception as e:
        logger.error(f"Error updating metrics grid: {e}")
        return "--", "--", "--", "--", "--", "--", "--", "--", "Error loading timestamp"

@callback(
    [Output("volume-flow-content", "children"),
     Output("volume-flow-timestamp", "children")],
    Input("url", "search")
)
def update_volume_flow(search):
    """Update the volume and flow card with trading activity metrics."""
    if not search:
        return "No subnet selected", "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID", "Invalid subnet ID"
        
        # Get latest metrics from database
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics:
                return "No data available", "No data available"
            
            # Format volume and flow data
            buy_volume = latest_metrics.buy_volume_tao_1d
            flow_24h = latest_metrics.flow_24h
            flow_7d = latest_metrics.net_volume_tao_7d
            
            buy_volume_formatted = f"{buy_volume:,.0f}" if buy_volume is not None else "--"
            flow_24h_formatted = f"{flow_24h:,.0f}" if flow_24h is not None else "--"
            flow_7d_formatted = f"{flow_7d:,.0f}" if flow_7d is not None else "--"
            
            # Determine colors for netflow (green for positive, red for negative)
            flow_24h_color = "text-success" if flow_24h is not None and flow_24h > 0 else "text-danger" if flow_24h is not None and flow_24h < 0 else ""
            flow_7d_color = "text-success" if flow_7d is not None and flow_7d > 0 else "text-danger" if flow_7d is not None and flow_7d < 0 else ""
            
            # Get timestamp
            timestamp_str = f"Updated: {latest_metrics.timestamp.strftime('%Y-%m-%d %H:%M UTC')}" if latest_metrics and latest_metrics.timestamp else "No data available"
            
            return html.Div([
                # Volume and flow metrics
                dbc.Row([
                    dbc.Col([
                        html.H6("Buy Volume (24h)", className="text-muted", id="buy-volume-label"),
                        html.H5(f"{buy_volume_formatted} TAO" if buy_volume_formatted != "--" else "--")
                    ], width=4),
                    dbc.Col([
                        html.H6("Netflow (24h)", className="text-muted", id="netflow-24h-label"),
                        html.H5(f"{flow_24h_formatted} TAO" if flow_24h_formatted != "--" else "--", className=flow_24h_color)
                    ], width=4),
                    dbc.Col([
                        html.H6("Netflow (7d)", className="text-muted", id="netflow-7d-label"),
                        html.H5(f"{flow_7d_formatted} TAO" if flow_7d_formatted != "--" else "--", className=flow_7d_color)
                    ], width=4)
                ]),
                
                # Tooltips
                dbc.Tooltip(
                    "TAO value of α bought in last 24h.",
                    target="buy-volume-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Net TAO flow over 24h (inflow - outflow). Positive = net inflow, negative = net outflow.",
                    target="netflow-24h-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Net TAO flow over 7 days (inflow - outflow). Positive = net inflow, negative = net outflow.",
                    target="netflow-7d-label",
                    placement="top"
                )
            ]), timestamp_str
        
    except Exception as e:
        logger.error(f"Error updating volume flow: {e}")
        return "Error loading volume data", "Error loading timestamp"

@callback(
    [Output("gpt-insight", "children"),
     Output("gpt-insight-timestamp", "children")],
    Input("url", "search")
)
def update_gpt_insight(search):
    """Update the GPT insight panel with peer comparisons."""
    if not search:
        return "No subnet selected", "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID", "Invalid subnet ID"
        
        # Get insight from service (use cache-aware function)
        insight = gpt_insight_service['get_insight'](netuid)
        
        # Get insight timestamp from cache
        from services.gpt_insight import get_insight_cache_info
        cache_info = get_insight_cache_info(netuid)
        insight_timestamp = cache_info.get('cached_insight_timestamp')
        
        if insight_timestamp:
            timestamp_str = f"Generated: {insight_timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
        else:
            timestamp_str = "Generated: Just now"
        
        # Extract and save buy signal to database
        from services.gpt_insight import extract_buy_signal_from_insight
        buy_signal = extract_buy_signal_from_insight(insight)
        if buy_signal is not None:
            with get_db() as session:
                snap = session.query(MetricsSnap).filter_by(netuid=netuid).order_by(MetricsSnap.timestamp.desc()).first()
                if snap:
                    snap.buy_signal = buy_signal
                    session.commit()
                    logger.info(f"Saved buy signal {buy_signal}/5 for subnet {netuid}")
        
        return html.P(insight, className="mb-0", style={"whiteSpace": "pre-wrap"}), timestamp_str
        
    except Exception as e:
        logger.error(f"Error getting GPT insight: {e}")
        return "Error loading AI insight", "Error loading timestamp"

@callback(
    Output("description", "children"),
    Input("url", "search")
)
def update_description(search):
    """Update the enriched description."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Get subnet metadata
        with get_db() as session:
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            if not subnet_meta:
                return html.Div("No description available", className="text-muted")
            
            return html.Div([
                html.P(subnet_meta.tagline or "No tagline available", className="mb-2"),
                html.P(subnet_meta.what_it_does or "No description available", className="text-muted")
            ])
        
    except Exception as e:
        logger.error(f"Error updating description: {e}")
        return "Error loading description"

@callback(
    Output("footer", "children"),
    Input("url", "search")
)
def update_footer(search):
    """Update the footer timestamp."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Get latest metrics timestamp
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics or latest_metrics.timestamp is None:
                return "No metrics data available"
            
            return f"Data as of {latest_metrics.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
        
    except Exception as e:
        logger.error(f"Error updating footer: {e}")
        return "Error loading timestamp"

@callback(
    Output("holders-validators-content", "children"),
    Input("url", "search")
)
def update_holders_validators(search):
    """Update the holders and validators section."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Placeholder content - to be implemented in future sprint
        return html.Div([
            html.P("Holders and validators data will be implemented in a future sprint.", className="text-muted"),
            html.P("This section will show detailed validator distribution and holder statistics.", className="text-muted")
        ])
        
    except Exception as e:
        logger.error(f"Error updating holders/validators: {e}")
        return "Error loading holders/validators data"

@callback(
    [Output("visit-site-link", "href"),
     Output("github-link", "href")],
    Input("url", "search")
)
def update_external_links(search):
    """Update the external links with actual URLs."""
    if not search:
        return "#", "#"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "#", "#"
        
        # Get subnet metadata
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics:
                return "#", "#"
            
            # Get URLs from screener data and format properly
            visit_site_url = latest_metrics.subnet_website or latest_metrics.subnet_url or "#"
            github_url = latest_metrics.github_repo or "#"
            
            # Add https:// protocol if missing for visit site URL
            if visit_site_url and visit_site_url != "#" and not visit_site_url.startswith(('http://', 'https://')):
                visit_site_url = f"https://{visit_site_url}"
            
            return visit_site_url, github_url
        
    except Exception as e:
        logger.error(f"Error updating external links: {e}")
        return "#", "#"

# Main layout
layout = html.Div([
    html.Div(id="subnet-detail-content", children=[
        html.Div("Select a subnet to view details", className="text-center py-5")
    ])
])

@callback(
    [Output("gpt-insight-collapse", "is_open"),
     Output("gpt-insight-chevron", "children")],
    Input("gpt-insight-toggle", "n_clicks"),
    State("gpt-insight-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_gpt_insight_collapse(n_clicks, is_open):
    """Toggle the GPT insight collapse."""
    logger.info(f"Collapse callback triggered: n_clicks={n_clicks}, is_open={is_open}")
    if n_clicks:
        new_state = not is_open
        chevron_text = "▲" if new_state else "▼"
        logger.info(f"Toggling collapse: new_state={new_state}, chevron_text={chevron_text}")
        return new_state, chevron_text
    chevron_text = "▲" if is_open else "▼"
    return is_open, chevron_text

@callback(
    [Output("overview-collapse", "is_open"),
     Output("overview-chevron", "children")],
    Input("overview-toggle", "n_clicks"),
    State("overview-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_overview_collapse(n_clicks, is_open):
    """Toggle the overview collapse."""
    if n_clicks:
        new_state = not is_open
        chevron_text = "▲" if new_state else "▼"
        return new_state, chevron_text
    chevron_text = "▲" if is_open else "▼"
    return is_open, chevron_text

@callback(
    [Output("volume-flow-collapse", "is_open"),
     Output("volume-flow-chevron", "children")],
    Input("volume-flow-toggle", "n_clicks"),
    State("volume-flow-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_volume_flow_collapse(n_clicks, is_open):
    """Toggle the volume & flow collapse."""
    if n_clicks:
        new_state = not is_open
        chevron_text = "▲" if new_state else "▼"
        return new_state, chevron_text
    chevron_text = "▲" if is_open else "▼"
    return is_open, chevron_text

@callback(
    [Output("metrics-collapse", "is_open"),
     Output("metrics-chevron", "children")],
    Input("metrics-toggle", "n_clicks"),
    State("metrics-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_metrics_collapse(n_clicks, is_open):
    """Toggle the metrics collapse."""
    if n_clicks:
        new_state = not is_open
        chevron_text = "▲" if new_state else "▼"
        return new_state, chevron_text
    chevron_text = "▲" if is_open else "▼"
    return is_open, chevron_text

def register_callbacks(dash_app):
    """Register callbacks for subnet detail page."""
    # The callbacks are already registered via decorators, but we need to ensure
    # the collapsible callback is properly registered
    pass 