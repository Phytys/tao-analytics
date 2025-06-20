import dash
import dash_bootstrap_components as dbc
from dash_app.pages.explorer import layout, register_callbacks

def create_dash(flask_app):
    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname="/dash/",
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        title="Subnet Explorer",
    )
    dash_app.layout = layout
    register_callbacks(dash_app)
    return dash_app 