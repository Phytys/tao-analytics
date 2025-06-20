import dash_bootstrap_components as dbc
from dash import html, dcc
from services.db import load_subnet_frame

CATS = ["All"] + sorted(
    load_subnet_frame()["primary_category"].dropna().unique().tolist()
)

layout = dbc.Container(
    [
        # --- header filter row ---
        dbc.Row(
            [
                dbc.Col(html.H2("Bittensor Subnet Explorer"), md=4),
                dbc.Col(
                    dcc.Dropdown(
                        id="cat-drop",
                        options=[{"label": c, "value": c} for c in CATS],
                        value="All",
                        clearable=False,
                    ),
                    md=3,
                ),
                dbc.Col(
                    dcc.Input(
                        id="search-box",
                        type="text",
                        placeholder="Search name or tag...",
                        debounce=True,
                        style={"width": "100%"},
                    ),
                    md=3,
                ),
                dbc.Col(html.Span(id="refresh-stamp"), md=2),
            ],
            className="my-2",
        ),
        # --- KPI strip ---
        dbc.Row(id="kpi-strip", className="my-2"),
        # --- charts ---
        dbc.Row(
            dbc.Col(
                dcc.Tabs(
                    id="charts-tab",
                    value="count",
                    children=[
                        dcc.Tab(label="Subnets per Category", value="count"),
                        dcc.Tab(label="Market-cap by Category", value="mcap"),
                    ],
                )
            )
        ),
        dbc.Row(dbc.Col(dcc.Graph(id="chart-fig"))),
        # --- card grid ---
        dbc.Row(id="card-grid", className="gy-3"),
        dcc.Store(id="cache-df"),
    ],
    fluid=True,
)

# Callbacks
from dash import Input, Output, State, callback, html
import plotly.express as px
import dash_bootstrap_components as dbc
from services.db import load_subnet_frame
import pandas as pd, datetime as dt, json, os

@callback(
    Output("cache-df", "data"),
    Output("refresh-stamp", "children"),
    Input("cat-drop", "value"),
    Input("search-box", "value"),
)
def refresh_df(cat, search):
    df = load_subnet_frame(cat, search or "")
    stamp = f"Refreshed {dt.datetime.utcnow().strftime('%H:%M:%S')} UTC"
    return df.to_json(date_unit="s", orient="split"), stamp


@callback(
    Output("kpi-strip", "children"),
    Input("cache-df", "data"),
)
def render_kpis(json_df):
    df = pd.read_json(json_df, orient="split")
    total = len(df)
    cats = df["primary_category"].nunique()
    privacy = (df["privacy_security_flag"] == True).mean() * 100
    badges = [
        dbc.Badge(f"{total} subnets", color="primary", className="me-2"),
        dbc.Badge(f"{cats} categories", color="secondary", className="me-2"),
        dbc.Badge(f"{privacy:0.0f}% privacy-focused", color="warning"),
    ]
    return dbc.Col(badges)


@callback(
    Output("chart-fig", "figure"),
    Input("cache-df", "data"),
    Input("charts-tab", "value"),
)
def render_chart(json_df, mode):
    df = pd.read_json(json_df, orient="split")
    if mode == "count":
        fig = px.pie(
            df.groupby("primary_category").size().reset_index(name="count"),
            names="primary_category",
            values="count",
            title="Subnets per Category",
        )
    else:
        fig = px.bar(
            df.groupby("primary_category")["mcap_tao"].sum().reset_index(),
            x="primary_category",
            y="mcap_tao",
            title="Total Market-cap (TAO) by Category",
        )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=380)
    return fig


@callback(
    Output("card-grid", "children"),
    Input("cache-df", "data"),
)
def render_cards(json_df):
    df = pd.read_json(json_df, orient="split").sort_values("mcap_tao", ascending=False)
    def make_card(row):
        # Handle secondary_tags as comma-separated string
        if pd.isna(row.secondary_tags) or not row.secondary_tags:
            tags = []
        else:
            tags = [tag.strip() for tag in str(row.secondary_tags).split(',') if tag.strip()]
        
        chips = [
            dbc.Badge(tag, color="light", className="me-1 mb-1 subt-chip")
            for tag in tags[:6]  # Limit to 6 tags
        ]
        privacy = (
            dbc.Badge("Privacy", color="danger", className="ms-1")
            if row.privacy_security_flag
            else ""
        )
        body = dbc.CardBody(
            [
                html.H5(row.subnet_name, className="card-title mb-1"),
                html.Small(row.tagline or "No description available", className="text-muted"),
                html.Br(),
                *chips,
                privacy,
            ]
        )
        return dbc.Col(
            dbc.Card(
                [
                    dbc.CardImg(src="/dash/assets/subnet_placeholder.svg", top=True),
                    body,
                ],
                style={"min-width": "18rem"},
            ),
            lg=4,
            md=6,
        )
    return [make_card(r) for _, r in df.iterrows()]

def register_callbacks(dash_app):
    """Register all callbacks with the dash app."""
    pass  # Callbacks are already registered via decorators 