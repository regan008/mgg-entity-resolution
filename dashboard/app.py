"""
MGG Entity Resolution Dashboard — unified control panel over the pipeline, and
the home of the human-review UIs (pair review and venue-group review, which
replaced the retired standalone review_app.py / venue_review_app.py). Reads the
CSVs the pipeline scripts produce, launches those scripts as subprocesses, and
writes the human-review / venue-edit CSVs. The batch pipeline scripts,
config.py, and the mgg.db schema are not modified by this app.

Usage:
    python dashboard/app.py            # serves on port 5050
    python dashboard/app.py --port 5051
"""
import argparse
import os
import sys

from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes.dashboard_routes import dashboard_bp  # noqa: E402
from routes.review_routes import review_bp  # noqa: E402
from routes.venue_routes import venue_bp  # noqa: E402


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(venue_bp)
    return app


app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MGG Entity Resolution Dashboard")
    parser.add_argument("--port", type=int, default=5050)
    args = parser.parse_args()
    print(f"\nMGG Entity Resolution Dashboard")
    print(f"Open http://localhost:{args.port} in your browser\n")
    app.run(debug=False, port=args.port)
