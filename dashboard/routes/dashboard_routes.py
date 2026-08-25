"""
Routes for: states map (/), state pipeline view (/state/<code>), stats &
calibration / API cost dashboard (/costs), and the shared job-launcher API.
"""
import os
import sys

from flask import Blueprint, jsonify, redirect, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data  # noqa: E402
import jobs  # noqa: E402

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def states_map():
    return render_template(
        "states_map.html",
        active_nav="states_map",
        active_state=None,
        summary=data.global_summary(),
        states=data.list_states(),
        unprocessed=data.unprocessed_states(),
    )


@dashboard_bp.route("/api/states/unprocessed")
def api_unprocessed_states():
    return jsonify(data.unprocessed_states())


@dashboard_bp.route("/state-redirect")
def state_redirect():
    code = request.args.get("code", "").strip().upper()
    if not code or not code.isalpha() or len(code) != 2:
        return redirect("/")
    return redirect(f"/state/{code}")


@dashboard_bp.route("/state/<code>")
def state_pipeline(code):
    code = code.upper()
    return render_template(
        "state_pipeline.html",
        active_nav="pipeline_view",
        active_state=code,
        state=code,
        stages=data.stage_status(code),
        current_stage_num=data.current_stage(code),
        record_count=data._preprocess_record_count(code),
    )


@dashboard_bp.route("/costs")
def costs():
    api_df = data.load_api_calls(limit=None)
    stats_df = data.load_pipeline_stats()

    total_cost = float(api_df["total_cost_usd"].sum()) if not api_df.empty else 0.0
    total_calls = len(api_df)
    avg_cost = total_cost / total_calls if total_calls else 0.0
    total_input = int(api_df["input_tokens"].sum()) if not api_df.empty else 0
    total_output = int(api_df["output_tokens"].sum()) if not api_df.empty else 0
    active_model = api_df.iloc[0]["model"] if not api_df.empty else "—"

    # Cost by day (last 7 days present in the data)
    daily = {}
    if not api_df.empty:
        tmp = api_df.copy()
        tmp["day"] = tmp["timestamp"].str.slice(0, 10)
        daily_series = tmp.groupby("day")["total_cost_usd"].sum().sort_index()
        daily = daily_series.tail(7).to_dict()

    # Cost by state
    by_state = {}
    if not api_df.empty:
        by_state = api_df.groupby("state")["total_cost_usd"].sum().to_dict()

    ledger = api_df.head(50).to_dict("records") if not api_df.empty else []

    return render_template(
        "costs.html",
        active_nav="costs",
        active_state=None,
        total_cost=total_cost,
        total_calls=total_calls,
        avg_cost=avg_cost,
        total_input=total_input,
        total_output=total_output,
        active_model=active_model,
        daily=daily,
        by_state=by_state,
        ledger=ledger,
        states=sorted(api_df["state"].unique().tolist()) if not api_df.empty else [],
        stats_rows=stats_df.to_dict("records") if not stats_df.empty else [],
    )


@dashboard_bp.route("/state/<code>/block-map")
def block_map(code):
    code = code.upper()
    return render_template(
        "block_map.html",
        active_nav="pipeline_view",
        active_state=code,
        state=code,
    )


@dashboard_bp.route("/api/state/<code>/block-map-data")
def api_block_map_data(code):
    return jsonify(data.block_map_data(code.upper()))


@dashboard_bp.route("/api/states")
def api_states():
    return jsonify(data.list_states())


@dashboard_bp.route("/api/state/<code>/stage/<stage_key>")
def api_stage_detail(code, stage_key):
    code = code.upper()
    detail = data.stage_detail(code, stage_key)
    if stage_key == "commit":
        # Surface unapproved venue-review edits here: assign_ids.py --commit
        # reads the approved snapshot, so a stale snapshot would commit the
        # wrong data. The script refuses in that case; warn before they click.
        from routes.venue_routes import approval_status
        detail["approval"] = approval_status(data.state_dir(code))
    return jsonify(detail)


@dashboard_bp.route("/api/state/<code>/run", methods=["POST"])
def api_run_stage(code):
    code = code.upper()
    body = request.json or {}
    script_key = body.get("script")
    flags = body.get("flags", [])
    try:
        job_id = jobs.start_job(code, script_key, flags)
    except jobs.JobConflict as e:
        return jsonify({"error": str(e)}), 409
    except jobs.UnknownScript as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"job_id": job_id, "status": "started"})


@dashboard_bp.route("/api/state/<code>/reset", methods=["POST"])
def api_reset_state(code):
    """Delete all pipeline data for a state so it can be re-run from scratch."""
    code = code.upper()
    if jobs.get_job_for_state(code) is not None:
        return jsonify({"error": "A job is running for this state. Wait for it to finish before resetting."}), 409
    result = data.reset_state(code)
    from routes.venue_routes import clear_cache
    clear_cache(code)
    return jsonify({"status": "reset", **result})


@dashboard_bp.route("/api/jobs/<job_id>/log")
def api_job_log(job_id):
    since = int(request.args.get("since", 0))
    log = jobs.get_log(job_id, since)
    if log is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(log)


@dashboard_bp.route("/api/state/<code>/job")
def api_state_job(code):
    """Return the currently-running job for a state, if any (for page reload)."""
    job = jobs.get_job_for_state(code.upper())
    if job is None:
        return jsonify({"running": False})
    return jsonify({"running": True, "job_id": job["id"], "script": job["script"]})
