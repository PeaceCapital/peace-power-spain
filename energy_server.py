#!/usr/bin/env python3
"""Peace* Energy — production server for Railway.

Serves the React dashboard (energy-dashboard/dist/) and the /live_data.json
endpoint which is refreshed hourly in a background thread.

Set ESIOS_TOKEN in Railway environment variables.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import pathlib

from flask import Flask, send_from_directory, jsonify, make_response

REPO_ROOT   = pathlib.Path(__file__).resolve().parent
DIST_DIR    = REPO_ROOT / "energy-dashboard" / "dist"
DATA_FILE   = REPO_ROOT / "energy-dashboard" / "public" / "live_data.json"
REFRESH_S   = 3600  # hourly

app = Flask(__name__, static_folder=None)


# ── live_data.json ──────────────────────────────────────────────────────────

def run_refresh() -> bool:
    """Run refresh_live_data.py + export_json.py. Returns True on success."""
    scripts = [
        REPO_ROOT / "scripts" / "refresh_live_data.py",
        REPO_ROOT / "scripts" / "export_json.py",
    ]
    for script in scripts:
        try:
            result = subprocess.run(
                ["python", str(script)],
                capture_output=True, text=True, timeout=300, cwd=str(REPO_ROOT)
            )
            if result.returncode != 0:
                print(f"[refresh] FAILED {script.name}: {result.stderr[-500:]}")
                return False
            print(f"[refresh] OK {script.name}")
        except Exception as exc:
            print(f"[refresh] ERROR {script.name}: {exc}")
            return False
    return True


def background_refresh():
    """Refresh immediately on startup, then every REFRESH_S seconds."""
    print("[refresh] Initial data pull starting…")
    run_refresh()
    while True:
        time.sleep(REFRESH_S)
        print("[refresh] Hourly refresh…")
        run_refresh()


@app.route("/live_data.json")
def live_data():
    """Serve the most recent data file with no-cache headers."""
    if not DATA_FILE.exists():
        return jsonify({"error": "data not yet available — refresh in progress"}), 503
    with open(DATA_FILE) as f:
        data = json.load(f)
    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"]        = "no-cache"
    return resp


# ── React static files ───────────────────────────────────────────────────────

@app.route("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(DIST_DIR / "assets", filename)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path: str):
    target = DIST_DIR / path
    if path and target.exists() and target.is_file():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


# ── Startup ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    # Start background data refresh thread
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()

    print(f"[server] Peace* Energy dashboard starting on :{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
