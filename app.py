from __future__ import annotations

import argparse
import atexit
import time
from typing import List, Tuple

from flask import Flask, Response, jsonify, render_template, request

from config import AppConfig
from core.pipeline import VideoPipeline


def create_app(source: str):
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    cfg = AppConfig()
    pipeline = VideoPipeline(cfg, source)
    pipeline.start()

    @atexit.register
    def _cleanup():
        pipeline.stop()

    @app.route("/")
    def index():
        return render_template("index.html", active="monitor")

    @app.route("/alerts")
    def alerts_page():
        return render_template("alerts.html", active="alerts")

    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html", active="dashboard")

    @app.route("/video_feed")
    def video_feed():
        def gen():
            while True:
                frame = pipeline.get_frame_jpeg()
                if frame is None:
                    if pipeline.has_failed():
                        time.sleep(0.2)
                    else:
                        time.sleep(0.03)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/alerts")
    def api_alerts():
        try:
            limit = int(request.args.get("limit", 100))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "limit must be an integer"}), 400
        limit = max(1, min(limit, 500))
        event_type = request.args.get("type")
        rows = pipeline.store.list_events(limit=limit, event_type=event_type)
        return jsonify({"items": rows, "count": len(rows)})

    @app.route("/api/alerts/summary")
    def api_alerts_summary():
        return jsonify(pipeline.store.get_summary())

    @app.route("/api/fence", methods=["POST"])
    def api_fence():
        payload = request.get_json(force=True)
        polygon = payload.get("polygon", [])
        if not isinstance(polygon, list) or len(polygon) < 3:
            return jsonify({"ok": False, "error": "polygon requires at least 3 points"}), 400

        parsed: List[Tuple[int, int]] = []
        for p in polygon:
            if not isinstance(p, list) and not isinstance(p, tuple):
                return jsonify({"ok": False, "error": "point must be [x,y]"}), 400
            if len(p) != 2:
                return jsonify({"ok": False, "error": "point must be [x,y]"}), 400
            parsed.append((int(p[0]), int(p[1])))

        pipeline.set_fence_polygon(parsed)
        return jsonify({"ok": True, "polygon": parsed})

    @app.route("/api/stats")
    def api_stats():
        return jsonify(pipeline.get_stats())

    @app.route("/api/dashboard")
    def api_dashboard():
        return jsonify(
            {
                "stats": pipeline.get_stats(),
                "summary": pipeline.store.get_summary(),
                "recent_alerts": pipeline.store.list_events(limit=8),
            }
        )

    @app.route("/api/rules", methods=["POST"])
    def api_rules():
        payload = request.get_json(force=True) or {}
        pipeline.set_rules(payload)
        return jsonify({"ok": True, "rules": payload})

    return app


def main():
    parser = argparse.ArgumentParser(description="Smart Security P0")
    parser.add_argument("--source", default="0", help="camera index (0) or video path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()

    app = create_app(args.source)
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
