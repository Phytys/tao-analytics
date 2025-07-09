"""
Dash app initialization for TAO Analytics.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_app.pages.explorer import layout as explorer_layout
from dash_app.pages.system_info import layout as system_info_layout
from dash_app.pages.subnet_detail import layout as subnet_detail_layout
from dash_app.pages.sdk_poc import layout as sdk_poc_layout
from dash_app.pages.screener import layout as screener_layout
from dash_app.pages.insights import layout as insights_layout

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
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
            "https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap",
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
        ],
        suppress_callback_exceptions=True,
        title="Bittensor Subnet Explorer - TAO Analytics",
        assets_folder='assets'
    )
    
    # Custom index template with favicon
    app.index_string = '''
    <!DOCTYPE html>
    <html lang="en">
        <head>
            {%metas%}
            <title>Bittensor Subnet Explorer - TAO Analytics</title>
            
            <!-- SEO Meta Tags -->
            <meta name="description" content="Explore Bittensor subnets with AI-powered insights and real-time analytics. Comprehensive subnet data, bittensor on-chain data analysis, and intelligent filtering powered by GPT-4.">
            <meta name="keywords" content="Bittensor, subnet explorer, TAO, AI analytics, decentralized AI, subnet data, bittensor on-chain data">
            <meta name="author" content="TAO Analytics">
            <meta name="robots" content="index, follow">
            
            <!-- Open Graph / Facebook -->
            <meta property="og:type" content="website">
            <meta property="og:url" content="{{ request.url }}">
            <meta property="og:title" content="Bittensor Subnet Explorer - TAO Analytics">
            <meta property="og:description" content="Explore Bittensor subnets with AI-powered insights and real-time analytics.">
            <meta property="og:image" content="/static/favicon.png">
            
            <!-- Twitter -->
            <meta property="twitter:card" content="summary_large_image">
            <meta property="twitter:url" content="{{ request.url }}">
            <meta property="twitter:title" content="Bittensor Subnet Explorer - TAO Analytics">
            <meta property="twitter:description" content="Explore Bittensor subnets with AI-powered insights and real-time analytics.">
            <meta property="twitter:image" content="/static/favicon.png">
            
            <!-- Canonical URL -->
            <link rel="canonical" href="{{ request.url }}">
            
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
            
            <script>
                // Update page title based on current URL
                function updatePageTitle() {
                    const pathname = window.location.pathname;
                    if (pathname === '/dash/system-info') {
                        document.title = 'System Information - TAO Analytics';
                    } else if (pathname === '/dash/explorer' || pathname === '/dash/') {
                        document.title = 'Bittensor Subnet Explorer - TAO Analytics';
                    } else {
                        document.title = 'TAO Analytics Dashboard';
                    }
                }
                
                // Update title on page load
                updatePageTitle();
                
                // Update title when URL changes (for SPA navigation)
                window.addEventListener('popstate', updatePageTitle);
                
                // Monitor for URL changes in Dash
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList') {
                            updatePageTitle();
                        }
                    });
                });
                
                // Start observing when DOM is ready
                document.addEventListener('DOMContentLoaded', function() {
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            </script>
        </body>
    </html>
    '''
    
    # App layout with custom navigation
    app.layout = html.Div([
        # Custom Navigation bar
        html.Nav([
            html.Div([
                html.A("TAO Analytics", href="/", className="nav-brand"),
                
                # Global Search Bar
                html.Div([
                    html.Div([
                        html.I(className="fas fa-search search-icon"),
                        dcc.Input(
                            id="global-search-input",
                            type="text",
                            placeholder="Search subnets...",
                            className="search-input",
                            n_submit=0
                        ),
                        html.Div(id="search-results", className="search-results")
                    ], className="search-container")
                ], className="search-wrapper"),
                
                html.Button([
                    html.Span(className="hamburger-line"),
                    html.Span(className="hamburger-line"),
                    html.Span(className="hamburger-line")
                ], className="mobile-menu-btn", id="mobile-menu-btn", n_clicks=0),
                html.Div([
                    # Close button for mobile menu
                    html.Button("×", id="mobile-menu-close", className="mobile-menu-close-btn", n_clicks=0),
                    html.A("Explorer", href="/dash/explorer", className="nav-link"),
                    html.A("Screener", href="/dash/screener", className="nav-link"),
                    html.A("Insights", href="/dash/insights", className="nav-link"),
                    html.A("Correlation", href="/dash/correlation", className="nav-link"),
                    html.A("About", href="/about", className="nav-link", id="about-nav-link"),
                    html.A("System Info", href="/dash/system-info", className="nav-link", id="system-info-nav-link"),
                    html.A("Home", href="/", className="nav-link")
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
    from dash_app.pages.subnet_detail import register_callbacks as register_subnet_detail_callbacks
    from dash_app.pages.correlation import register_callbacks as register_correlation_callbacks
    
    register_explorer_callbacks(app)
    register_system_info_callbacks(app)
    register_subnet_detail_callbacks(app)
    register_correlation_callbacks(app)
    
    # Mobile menu toggle callback
    @app.callback(
        dash.Output("nav-links", "className"),
        dash.Output("mobile-menu-btn", "className"),
        dash.Output("menu-state", "data"),
        dash.Input("mobile-menu-btn", "n_clicks"),
        dash.Input("mobile-menu-close", "n_clicks"),
        dash.State("menu-state", "data"),
        prevent_initial_call=True
    )
    def toggle_mobile_menu(n_hamburger, n_close, menu_state):
        ctx = dash.callback_context
        if not ctx.triggered:
            return "nav-links", "mobile-menu-btn", menu_state
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if btn_id == "mobile-menu-close":
            return "nav-links", "mobile-menu-btn", {"open": False}
        # Hamburger button toggles open/close
        is_open = menu_state.get("open", False)
        if not is_open:
            return "nav-links nav-open", "mobile-menu-btn active", {"open": True}
        else:
            return "nav-links", "mobile-menu-btn", {"open": False}
    
    # URL routing callback with authentication check
    @app.callback(
        dash.Output("page-content", "children"),
        dash.Input("url", "pathname"),
        dash.Input("url", "search")
    )
    def display_page(pathname, search):
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
        
        if pathname == "/dash/subnet-detail":
            return subnet_detail_layout
        
        if pathname == "/dash/sdk-poc":
            return sdk_poc_layout()
        
        if pathname == "/dash/screener":
            return screener_layout
        
        if pathname == "/dash/insights":
            return insights_layout()
        
        if pathname == "/dash/correlation":
            from dash_app.pages.correlation import layout
            return layout()
        
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
    
    # Global search callback
    @app.callback(
        dash.Output("search-results", "children"),
        dash.Output("global-search-input", "value"),
        dash.Input("global-search-input", "value"),
        dash.Input("global-search-input", "n_submit"),
        dash.State("global-search-input", "value"),
        prevent_initial_call=True
    )
    def handle_global_search(search_value, n_submit, current_value):
        ctx = dash.callback_context
        if not ctx.triggered:
            return [], ""
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Clear results if search is empty
        if not search_value or len(search_value.strip()) < 2:
            return [], search_value
        
        # If Enter was pressed, navigate to first result
        if trigger_id == "global-search-input" and n_submit > 0:
            if search_value:
                # Find the first matching subnet
                from services.db import get_db
                from models import SubnetMeta, MetricsSnap
                
                session = get_db()
                try:
                    # Search by netuid (if numeric) or subnet name
                    if search_value.isdigit():
                        netuid = int(search_value)
                        subnet = session.query(SubnetMeta).filter(SubnetMeta.netuid == netuid).first()
                    else:
                        # Search by name (case-insensitive, partial match)
                        subnet = session.query(SubnetMeta).filter(
                            SubnetMeta.subnet_name.ilike(f"%{search_value}%")
                        ).first()
                    
                    if subnet:
                        # Clear search and let the link handle navigation
                        return [], ""
                    else:
                        return [], search_value
                finally:
                    session.close()
        
        # Show search results
        from services.db import get_db
        from models import SubnetMeta, MetricsSnap
        from sqlalchemy import desc
        
        session = get_db()
        try:
            results = []
            
            # Search by netuid (if numeric)
            if search_value.isdigit():
                netuid = int(search_value)
                subnet = session.query(SubnetMeta).filter(SubnetMeta.netuid == netuid).first()
                if subnet:
                    results.append({
                        'netuid': subnet.netuid,
                        'name': subnet.subnet_name or f"Subnet {subnet.netuid}",
                        'category': getattr(subnet, 'primary_category', None)
                    })
            
            # Search by name (case-insensitive, partial match)
            name_results = session.query(SubnetMeta).filter(
                SubnetMeta.subnet_name.ilike(f"%{search_value}%")
            ).limit(5).all()
            
            for subnet in name_results:
                if not any(r['netuid'] == subnet.netuid for r in results):
                    results.append({
                        'netuid': subnet.netuid,
                        'name': subnet.subnet_name or f"Subnet {subnet.netuid}",
                        'category': getattr(subnet, 'primary_category', None)
                    })
            
            # Create result items
            if results:
                result_items = []
                for result in results[:5]:  # Limit to 5 results
                    category_badge = ""
                    if result['category']:
                        category_badge = html.Span(
                            result['category'], 
                            className="search-result-category"
                        )
                    
                    result_items.append(
                        html.A([
                            html.Div([
                                html.Strong(f"Subnet {result['netuid']}"),
                                html.Br(),
                                html.Span(result['name'], className="search-result-name"),
                                category_badge
                            ], className="search-result-content")
                        ], 
                        href=f"/dash/subnet-detail?netuid={result['netuid']}", 
                        className="search-result-item")
                    )
                
                return result_items, search_value
            else:
                return [
                    html.Div("No subnets found", className="search-no-results")
                ], search_value
                
        finally:
            session.close()
    
    return app 