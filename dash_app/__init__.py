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
    
    # App layout with custom navigation
    app.layout = html.Div([
        # Custom Navigation bar
        html.Nav([
            html.Div([
                html.A("TAO Analytics", href="/", className="nav-brand"),
                html.Button([
                    html.Span(className="hamburger-line"),
                    html.Span(className="hamburger-line"),
                    html.Span(className="hamburger-line")
                ], className="mobile-menu-btn", id="mobile-menu-btn", n_clicks=0),
                html.Div([
                    html.A("Subnet Explorer", href="/dash/explorer", className="nav-link"),
                    html.A("System Info", href="/dash/system-info", className="nav-link", id="system-info-nav-link"),
                    html.A("Back to Home", href="/", className="nav-link")
                ], className="nav-links", id="nav-links")
            ], className="nav-container")
        ], className="navbar"),
        
        # Page content
        html.Div(id="page-content"),
        
        # URL routing
        dcc.Location(id="url", refresh=False),
        
        # Store for menu state
        dcc.Store(id="menu-state", data={"open": False})
    ])
    
    # Import and register callbacks
    from dash_app.pages.explorer import register_callbacks as register_explorer_callbacks
    from dash_app.pages.system_info import register_callbacks as register_system_info_callbacks
    
    register_explorer_callbacks(app)
    register_system_info_callbacks(app)
    
    # Mobile menu toggle callback
    @app.callback(
        dash.Output("nav-links", "className"),
        dash.Output("mobile-menu-btn", "className"),
        dash.Output("menu-state", "data"),
        dash.Input("mobile-menu-btn", "n_clicks"),
        dash.State("menu-state", "data"),
        prevent_initial_call=True
    )
    def toggle_mobile_menu(n_clicks, menu_state):
        if n_clicks is None:
            return "nav-links", "mobile-menu-btn", menu_state
        
        is_open = menu_state.get("open", False)
        new_state = not is_open
        
        if new_state:
            return "nav-links nav-open", "mobile-menu-btn active", {"open": True}
        else:
            return "nav-links", "mobile-menu-btn", {"open": False}
    
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
        dash.Output("system-info-nav-link", "style"),
        dash.Input("url", "pathname")
    )
    def update_navbar_visibility(pathname):
        if session.get('admin_authenticated'):
            return {"display": "block"}
        else:
            return {"display": "none"}
    
    return app 