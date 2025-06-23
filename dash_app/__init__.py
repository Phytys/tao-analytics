"""
Dash app initialization for TAO Analytics.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_app.pages.explorer import layout as explorer_layout
from dash_app.pages.system_info import layout as system_info_layout
from flask import session, redirect

def create_dash(server):
    """Create and configure Dash app."""
    
    # Initialize Dash app
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/',
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
        ],
        suppress_callback_exceptions=True
    )
    
    # App layout with navigation
    app.layout = html.Div([
        # Navigation bar
        dbc.Navbar(
            dbc.Container([
                dbc.NavbarBrand(
                    html.A("TAO Analytics", href="/", className="text-decoration-none text-white"),
                    className="fw-bold"
                ),
                dbc.Nav([
                    dbc.NavItem(
                        dbc.NavLink("Subnet Explorer", href="/dash/explorer", className="text-white")
                    ),
                    # System Info link - only show when authenticated
                    dbc.NavItem(
                        dbc.NavLink("System Info", href="/dash/system-info", className="text-white"),
                        id="system-info-nav-item",
                        style={"display": "none"}  # Hidden by default
                    ),
                ], className="ms-auto"),
            ]),
            color="primary",
            dark=True,
            className="mb-4"
        ),
        
        # Page content
        html.Div(id="page-content"),
        
        # URL routing
        dcc.Location(id="url", refresh=False),
    ])
    
    # Import and register callbacks
    from dash_app.pages.explorer import register_callbacks as register_explorer_callbacks
    from dash_app.pages.system_info import register_callbacks as register_system_info_callbacks
    
    register_explorer_callbacks(app)
    register_system_info_callbacks(app)
    
    # URL routing callback with authentication check
    @app.callback(
        dash.Output("page-content", "children"),
        dash.Input("url", "pathname")
    )
    def display_page(pathname):
        # Check authentication for system-info access
        if pathname == "/dash/system-info":
            if not session.get('admin_authenticated'):
                return html.Div([
                    html.H1("Access Denied", className="text-center mt-5 text-danger"),
                    html.P("You must be logged in as admin to access this page.", className="text-center"),
                    html.A("Go to Login", href="/admin/login", className="btn btn-primary d-block mx-auto mt-3")
                ])
            return system_info_layout
        
        if pathname == "/dash/explorer" or pathname == "/dash/":
            return explorer_layout
        else:
            return html.Div([
                html.H1("404 - Page Not Found", className="text-center mt-5"),
                html.P("The page you're looking for doesn't exist.", className="text-center"),
                html.A("Go to Explorer", href="/dash/explorer", className="btn btn-primary d-block mx-auto mt-3")
            ])
    
    # Callback to show/hide system-info link based on authentication
    @app.callback(
        dash.Output("system-info-nav-item", "style"),
        dash.Input("url", "pathname")
    )
    def update_navbar_visibility(pathname):
        if session.get('admin_authenticated'):
            return {"display": "block"}
        else:
            return {"display": "none"}
    
    return app 