import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
from dash_app.pages.explorer import layout as explorer_layout, register_callbacks as register_explorer_callbacks
from dash_app.pages.metrics import layout as metrics_layout, register_callbacks as register_metrics_callbacks

def create_dash(flask_app):
    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname="/dash/",
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        title="TAO Analytics",
    )
    
    # Navigation layout
    dash_app.layout = html.Div([
        # Navigation bar
        dbc.NavbarSimple(
            [
                dbc.NavItem(dbc.NavLink("Explorer", href="/dash/", id="nav-explorer")),
                dbc.NavItem(dbc.NavLink("Metrics", href="/dash/metrics", id="nav-metrics")),
            ],
            brand="TAO Analytics",
            brand_href="/dash/",
            color="primary",
            dark=True,
            className="mb-4"
        ),
        
        # Page content
        html.Div(id="page-content"),
        
        # URL routing
        dcc.Location(id="url", refresh=False),
    ])
    
    # URL routing callback
    @callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def display_page(pathname):
        if pathname == "/dash/metrics":
            return metrics_layout
        else:
            return explorer_layout
    
    # Register callbacks for both pages
    register_explorer_callbacks(dash_app)
    register_metrics_callbacks(dash_app)
    
    return dash_app 