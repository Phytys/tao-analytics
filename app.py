from flask import Flask, render_template_string
from dash_app import create_dash

def create_app():
    server = Flask(__name__)
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    # simple landing page
    @server.route("/")
    def index():
        return render_template_string(
            "<h3>TAO-Analytics prototype</h3>"
            "<p><a href='/dash/'>Open Subnet Explorer</a></p>"
        )

    create_dash(server)      # mounts at /dash/
    return server

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000) 