from flask import Flask, render_template
from dash_app import create_dash
from services.metrics import metrics_service

def create_app():
    server = Flask(__name__)
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    # Tesla-inspired landing page
    @server.route("/")
    def index():
        # Get cached KPIs for landing page
        try:
            kpis = metrics_service.get_landing_kpis()
        except Exception as e:
            # Fallback values if metrics service fails
            kpis = {
                'total_subnets': 124,
                'enriched_subnets': 94,
                'categories': 12,
                'avg_confidence': 85.2
            }
        return render_template("index.html", kpis=kpis)

    create_dash(server)      # mounts at /dash/
    return server

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000) 