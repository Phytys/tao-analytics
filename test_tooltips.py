#!/usr/bin/env python
"""
Simple test to verify tooltips are working.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from dash import Dash, html
import dash_bootstrap_components as dbc

def test_tooltip():
    """Test if tooltips are working."""
    app = Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
        ]
    )
    
    app.layout = html.Div([
        html.H1("Tooltip Test"),
        
        # Test tooltip with icon
        html.Div([
            html.H3("Test Section"),
            html.I(className="bi bi-info-circle ms-2", id="test-tooltip", style={"cursor": "pointer"})
        ]),
        
        # Tooltip
        dbc.Tooltip(
            "This is a test tooltip to verify Bootstrap Icons and tooltips are working correctly!",
            target="test-tooltip",
            placement="top",
            style={"fontSize": "14px", "maxWidth": "300px"}
        )
    ])
    
    print("✅ Tooltip test created successfully!")
    print("If you can see the info icon and tooltip on hover, everything is working.")
    
    return app

if __name__ == "__main__":
    test_tooltip() 