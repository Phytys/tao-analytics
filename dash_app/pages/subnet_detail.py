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
                    html.Span(id="subnet-name", children="Loading...", className="text-muted")
                ], width=6),
                dbc.Col([
                    html.Div([
                        dbc.Badge(id="subnet-category", children="Loading...", color="primary", className="me-2"),
                        html.A(
                            "Visit site ↗",
                            href="#",
                            className="text-decoration-none me-2"
                        ),
                        html.A(
                            "GitHub",
                            href="#",
                            className="text-decoration-none"
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
            html.H5("Overview", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="overview-content", children=[
                dbc.Spinner(html.Div("Loading overview data..."), size="sm")
            ])
        ])
    ], className="mb-3")

def create_metrics_grid(netuid: int) -> dbc.Card:
    """Create the key metrics grid with 5 tiles for investor metrics."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Key Metrics", className="mb-0")
        ]),
        dbc.CardBody([
            # First row: Stake Quality, Reserve Momentum, Active Validators
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Stake Quality", className="card-title", id="stake-quality-label"),
                            html.H4(id="stake-quality", children="--"),
                            html.Small("vs category median", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Reserve Momentum", className="card-title", id="reserve-momentum-label"),
                            html.H4(id="reserve-momentum", children="--"),
                            html.Small("Δ TAO-in 24h / supply", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Active Validators", className="card-title", id="active-validators-label"),
                            html.H4(id="active-validators", children="--"),
                            html.Small("of 256 UIDs", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4)
            ], className="mb-3"),
            
            # Second row: Consensus Alignment, Trust Score, Annual Inflation
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Consensus Alignment", className="card-title", id="consensus-alignment-label"),
                            html.H4(id="consensus-alignment", children="--"),
                            html.Small("stake-weighted %", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Trust Score", className="card-title", id="trust-score-label"),
                            html.H4(id="trust-score", children="--"),
                            html.Small("0-1 scale", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Annual Inflation", className="card-title", id="annual-inflation-label"),
                            html.H4(id="annual-inflation", children="--"),
                            html.Small("α-token supply growth", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=4)
            ], className="mb-3"),
            
            # Third row: Emission Progress
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Emission Progress", className="card-title", id="emission-progress-label"),
                            html.Div(id="emission-progress-gauge", children="--"),
                            html.Small("of max α-supply", className="text-muted")
                        ])
                    ], className="text-center")
                ], width=12)
            ])
        ]),
        
        # Tooltips
        dbc.Tooltip(
            "Decentralisation score (0–100). Derived from stake-HHI; higher = more evenly distributed stake.",
            target="stake-quality-label",
            placement="top"
        ),
        dbc.Tooltip(
            "24 h net change in TAO reserves, normalised by market-cap. Positive = inflow, negative = outflow.",
            target="reserve-momentum-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Active validators ÷ 256 slots. Low utilisation may signal under-secured network.",
            target="active-validators-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Stake-weighted % of validators whose consensus value is within ±2 σ of the subnet mean.",
            target="consensus-alignment-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Stake-weighted mean trust (0–1). Higher = validators more often agree with the canonical chain.",
            target="trust-score-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Projected α-token supply growth over the next 12 months, assuming the current mint schedule.",
            target="annual-inflation-label",
            placement="top"
        ),
        dbc.Tooltip(
            "Share of the fully-diluted α-supply already minted.",
            target="emission-progress-label",
            placement="top"
        )
    ], className="mb-3")

def create_gpt_insight_panel(netuid: int) -> dbc.Card:
    """Create the GPT insight panel with peer comparisons."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("AI Analysis", className="mb-0"),
            html.Small("Powered by GPT-4o", className="text-muted")
        ]),
        dbc.CardBody([
            html.Div(id="gpt-insight", children=[
                dbc.Spinner(html.Div("Generating AI insight..."), size="sm"),
                html.Small("This may take a few seconds", className="text-muted d-block mt-2")
            ])
        ])
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

def create_subnet_detail_layout(netuid: int) -> html.Div:
    """Create the complete subnet detail layout."""
    return html.Div([
        # Header bar
        create_header_bar(netuid),
        
        # Overview card
        create_overview_card(netuid),
        
        # Metrics grid
        create_metrics_grid(netuid),
        
        # GPT insight panel
        create_gpt_insight_panel(netuid),
        
        # Enriched description
        create_enriched_description(netuid),
        
        # Tabs
        create_tabs(netuid),
        
        # Holders & Validators section
        create_holders_validators_section(netuid),
        
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
    Output("overview-content", "children"),
    Input("url", "search")
)
def update_overview(search):
    """Update the overview card with price action and flow data."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
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
            
            return html.Div([
                # First row: Price, Market Cap, FDV, Total Stake Weight
                dbc.Row([
                    dbc.Col([
                        html.H6("Price (Alpha)", className="text-muted", id="price-label"),
                        html.H4([
                            f"{price_formatted} TAO" if price_formatted != "--" else "--",
                            html.Br(),
                            html.Span(price_usd_formatted, className="text-muted fs-6") if price_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("Market Cap (TAO)", className="text-muted", id="market-cap-label"),
                        html.H4([
                            f"{market_cap_formatted} TAO" if market_cap_formatted != "--" else "--",
                            html.Br(),
                            html.Span(market_cap_usd_formatted, className="text-muted fs-6") if market_cap_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("FDV (TAO)", className="text-muted", id="fdv-label"),
                        html.H4([
                            f"{fdv_formatted} TAO" if fdv_formatted != "--" else "--",
                            html.Br(),
                            html.Span(fdv_usd_formatted, className="text-muted fs-6") if fdv_usd_formatted else ""
                        ])
                    ], width=3),
                    dbc.Col([
                        html.H6("Total Stake Weight", className="text-muted", id="total-stake-label"),
                        html.H4(f"{total_stake_formatted} TAO" if total_stake_formatted != "--" else "--")
                    ], width=3)
                ], className="mb-3"),
                
                # Second row: Price changes and flow data
                dbc.Row([
                    dbc.Col([
                        html.H6("24h Δ", className="text-muted", id="price-1d-label"),
                        html.H5(price_1d_formatted, className=price_1d_color)
                    ], width=2),
                    dbc.Col([
                        html.H6("7d Δ", className="text-muted", id="price-7d-label"),
                        html.H5(price_7d_formatted, className=price_7d_color)
                    ], width=2),
                    dbc.Col([
                        html.H6("30d Δ", className="text-muted", id="price-30d-label"),
                        html.H5(price_30d_formatted, className=price_30d_color)
                    ], width=2),
                    dbc.Col([
                        html.H6("Buy Vol (24 h)", className="text-muted", id="buy-volume-label"),
                        html.H5(f"{buy_volume_formatted} TAO" if buy_volume_formatted != "--" else "--")
                    ], width=3),
                    dbc.Col([
                        html.H6("TAO Reserves", className="text-muted", id="tao-reserves-label"),
                        html.H5(f"{tao_in_formatted} TAO" if tao_in_formatted != "--" else "--")
                    ], width=3)
                ]),
                
                # Tooltips
                dbc.Tooltip(
                    "Last traded price of the subnet's α-token, quoted in TAO.",
                    target="price-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Circulating α-supply × price. Measures economic size of the subnet token.",
                    target="market-cap-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "α-price × max α-supply; theoretical fully-diluted valuation, useful for upside comparison.",
                    target="fdv-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Validator bond weight measured in TAO-equivalent units. Historical weights can exceed circulating TAO.",
                    target="total-stake-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change of the α-token over the stated window.",
                    target="price-1d-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change of the α-token over the stated window.",
                    target="price-7d-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "Price change of the α-token over the stated window.",
                    target="price-30d-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "TAO value of α-tokens bought in the last 24 h. Gauges demand.",
                    target="buy-volume-label",
                    placement="top"
                ),
                dbc.Tooltip(
                    "TAO held in the subnet reserve (α↔TAO pool). Used for liquidity and emissions.",
                    target="tao-reserves-label",
                    placement="top"
                )
            ])
        
    except Exception as e:
        logger.error(f"Error updating overview: {e}")
        return "Error loading overview data"

@callback(
    [Output("stake-quality", "children"),
     Output("reserve-momentum", "children"),
     Output("active-validators", "children"),
     Output("consensus-alignment", "children"),
     Output("trust-score", "children"),
     Output("annual-inflation", "children"),
     Output("emission-progress-gauge", "children")],
    Input("url", "search")
)
def update_metrics_grid(search):
    """Update the metrics grid with peer comparisons and ranking badges."""
    if not search:
        return "--", "--", "--"
    
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
            
            # Format trust score
            trust_score = latest_metrics.trust_score
            if trust_score is not None:
                trust_formatted = f"{trust_score:.3f}"
            else:
                trust_formatted = "--"
            
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
            
            return stake_quality_formatted, momentum_formatted, validators_formatted, consensus_formatted, trust_formatted, inflation_formatted, progress_formatted
        
    except Exception as e:
        logger.error(f"Error updating metrics grid: {e}")
        return "--", "--", "--", "--", "--", "--", "--"

@callback(
    Output("gpt-insight", "children"),
    Input("url", "search")
)
def update_gpt_insight(search):
    """Update the GPT insight panel with peer comparisons."""
    if not search:
        return "No subnet selected"
    
    try:
        import urllib.parse
        params = urllib.parse.parse_qs(search.lstrip('?'))
        netuid = int(params.get('netuid', [None])[0])
        
        if netuid is None:
            return "Invalid subnet ID"
        
        # Get insight from service
        insight = gpt_insight_service['get_insight'](netuid)
        return html.P(insight, className="mb-0", style={"whiteSpace": "pre-wrap"})
        
    except Exception as e:
        logger.error(f"Error getting GPT insight: {e}")
        return "Error loading AI insight"

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

# Main layout
layout = html.Div([
    html.H2("Subnet Detail", className="mb-4"),
    html.Div(id="subnet-detail-content", children=[
        html.Div("Select a subnet to view details", className="text-center py-5")
    ])
])

def register_callbacks(dash_app):
    """Register callbacks for subnet detail page."""
    pass  # Callbacks are already registered via decorators 