from flask import Flask, render_template
from dash_app import create_dash

def create_app():
    server = Flask(__name__)
    server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    # Tesla-inspired landing page
    @server.route("/")
    def index():
        return render_template("index.html")

    create_dash(server)      # mounts at /dash/
    return server

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000) 