import dash
from dash import dcc, html, Output, Input
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
import sys, os

# Add project root to path for import
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from services.bittensor.metrics import calculate_subnet_metrics

# Subnet to display
NETUID = 64

# Note: Page registration handled in dash_app/__init__.py via custom routing

def get_metrics():
    metrics = calculate_subnet_metrics(NETUID)
    return metrics

def layout():
    metrics = get_metrics()
    emission_split = metrics.get("emission_split", {"owner": 0, "miners": 0, "validators": 0})
    donut_labels = ["Owner", "Miners", "Validators"]
    donut_values = [emission_split["owner"], emission_split["miners"], emission_split["validators"]]
    donut_text = "N/A" if sum(donut_values) == 0 else None
    return dbc.Container([
        html.H2("Bittensor SDK PoC (Subnet 64)", className="mt-4 mb-4"),
        dbc.Row([
            dbc.Col([
                html.H4("Total TAO Staked"),
                html.H1(f"{metrics.get('total_stake_tao', 0):,.0f}", style={"color": "#2b7cff"}),
            ], width=3),
            dbc.Col([
                html.H4("Stake HHI (0-10,000)"),
                dcc.Graph(
                    figure=go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=metrics.get("stake_hhi", 0),
                        gauge={"axis": {"range": [0, 10000]}, "bar": {"color": "#2b7cff"}},
                        number={"font": {"size": 36}},
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": "HHI"}
                    )).update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200),
                    config={"displayModeBar": False},
                ),
            ], width=3),
            dbc.Col([
                html.H4("Total Emission (last block)"),
                html.H1(f"{metrics.get('total_emission_tao', 0):.2e} TAO", style={"color": "#20bf6b"}),
            ], width=3),
            dbc.Col([
                html.H4("Current Block Emission Split"),
                dcc.Graph(
                    figure=go.Figure(
                        data=[go.Pie(
                            labels=donut_labels,
                            values=donut_values,
                            hole=0.5,
                            textinfo="label+percent",
                            marker=dict(colors=["#f7b731", "#20bf6b", "#3867d6"]),
                            hoverinfo="label+percent",
                        )],
                        layout=go.Layout(
                            annotations=[dict(text=donut_text, x=0.5, y=0.5, font_size=20, showarrow=False)] if donut_text else [],
                            margin=dict(l=0, r=0, t=0, b=0),
                            height=220
                        )
                    ),
                    config={"displayModeBar": False},
                ),
            ], width=3),
        ], className="mb-4"),
        
        # Info badge about emission split limitations
        dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "Owner share can be 0% on α-only blocks. Rolling averages smooth this volatility."
        ], color="warning", className="mb-4"),
        
        # Rolling window emission split (when SDK supports it)
        dbc.Row([
            dbc.Col([
                html.H4("Rolling Window Emission Split"),
                html.P("(3-block average - Ultra-fast PoC)", className="text-muted small"),
                dcc.Graph(
                    figure=go.Figure(
                        data=[go.Pie(
                            labels=donut_labels,
                            values=[metrics.get("emission_split_rolling", {}).get("owner", 0),
                                   metrics.get("emission_split_rolling", {}).get("miners", 0),
                                   metrics.get("emission_split_rolling", {}).get("validators", 0)],
                            hole=0.5,
                            textinfo="label+percent",
                            marker=dict(colors=["#f7b731", "#20bf6b", "#3867d6"]),
                            hoverinfo="label+percent",
                        )],
                        layout=go.Layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            height=220
                        )
                    ),
                    config={"displayModeBar": False},
                ),
            ], width=6),
            dbc.Col([
                html.H4("Rolling Window Info"),
                html.Ul([
                    html.Li("Fetches last 3 blocks (ultra-fast PoC)"),
                    html.Li("5-minute cache prevents repeated calculations"),
                    html.Li("Shows basic rolling average concept"),
                    html.Li("Fast enough for interactive PoC testing"),
                ], className="small"),
            ], width=6),
        ], className="mb-4"),
        dcc.Interval(id="sdk-poc-interval", interval=30*1000, n_intervals=0),
        html.Div(id="sdk-poc-metrics-store", style={"display": "none"}),
    ], fluid=True)

# Callback for live refresh
dash.callback(
    Output("sdk-poc-metrics-store", "children"),
    Output("sdk-poc-interval", "disabled"),
    Input("sdk-poc-interval", "n_intervals"),
)(
    lambda n: (str(get_metrics()), False)
) 