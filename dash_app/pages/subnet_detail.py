"""
Subnet Detail Page - Deep dive into individual subnet data.
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from services.db import load_subnet_frame
import pandas as pd

def layout():
    """Layout for subnet detail page."""
    return html.Div([
        # URL parameter store
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="subnet-data"),
        
        # Header
        html.Div([
            html.H1("Subnet Detail", className="mb-3"),
            html.P("Deep dive into subnet metrics and performance", className="text-muted mb-4"),
            # Back button
            html.A(
                "← Back to Explorer", 
                href="/dash/explorer", 
                className="btn btn-outline-primary mb-4"
            )
        ], className="mb-4"),
        
        # Dynamic content area
        html.Div(id="subnet-content", className="container")
    ], className="container mt-4")

@callback(
    Output("subnet-content", "children"),
    Input("url", "search")
)
def update_subnet_content(search):
    """Update content based on URL parameters."""
    if not search:
        return html.Div([
            html.H3("No subnet selected", className="text-muted"),
            html.P("Please select a subnet from the explorer to view details.")
        ])
    
    # Parse netuid from URL
    try:
        # Extract netuid from ?netuid=1 format
        netuid = search.split("=")[1] if "=" in search else None
        if not netuid:
            return html.Div([
                html.H3("Invalid subnet ID", className="text-danger"),
                html.P("Please select a valid subnet from the explorer.")
            ])
        
        # Load subnet data
        df = load_subnet_frame()
        subnet = df[df['netuid'] == int(netuid)]
        
        if subnet.empty:
            return html.Div([
                html.H3(f"Subnet {netuid} not found", className="text-danger"),
                html.P("This subnet may not exist or may not be in our database.")
            ])
        
        row = subnet.iloc[0]
        
        # Display subnet details
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H3(f"Subnet {row.netuid} - {row.subnet_name or 'Unnamed'}", className="card-title"),
                    html.P(f"Category: {row.primary_category or 'Uncategorized'}", className="card-text"),
                    html.P(f"Market Cap: {row.market_cap:,.0f} TAO" if pd.notna(row.market_cap) else "Market Cap: Unknown", className="card-text"),
                    html.P(f"Confidence: {row.confidence:.0f}%" if pd.notna(row.confidence) else "Confidence: Unknown", className="card-text"),
                    html.P(f"Tagline: {row.tagline or 'No description available'}", className="card-text"),
                    
                    # What it does section
                    html.H5("What it does:", className="mt-3"),
                    html.P(row.what_it_does or "No detailed description available.", className="card-text"),
                    
                    # Links section
                    html.H5("Links:", className="mt-3"),
                    html.Div([
                        html.A("🌐 Website", href=row.website_url, target="_blank", className="btn btn-outline-primary me-2") if pd.notna(row.website_url) else html.Div(),
                        html.A("📁 GitHub", href=row.github_url, target="_blank", className="btn btn-outline-secondary") if pd.notna(row.github_url) else html.Div(),
                    ]) if (pd.notna(row.website_url) or pd.notna(row.github_url)) else html.P("No links available", className="text-muted"),
                    
                    # Future content placeholder
                    html.Hr(),
                    html.H5("Future Content Areas:", className="text-muted"),
                    html.Ul([
                        html.Li("Detailed metrics and charts"),
                        html.Li("Validator performance"),
                        html.Li("Historical data"),
                        html.Li("Team information"),
                        html.Li("Technical specifications")
                    ], className="text-muted")
                ])
            ])
        ])
        
    except Exception as e:
        return html.Div([
            html.H3("Error loading subnet", className="text-danger"),
            html.P(f"An error occurred: {str(e)}")
        ])

def register_callbacks(dash_app):
    """Register callbacks for subnet detail page."""
    pass  # Callbacks are already registered via decorators 