import os
import sys
from functools import wraps

# --- Determine environment ---
FROZEN = getattr(sys, "frozen", False)
BASE_DIR = sys._MEIPASS if FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# --- Load .env ---
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not FROZEN:
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv is optional; config can be set via real environment variables

from CheckmarxPythonSDK.api_client import ApiClient
from CheckmarxPythonSDK.configuration import Configuration
from CheckmarxPythonSDK.CxRestAPISDK import ProjectsAPI, TeamAPI
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# --- Config ---
def load_configuration():
    verify_raw = os.getenv("CXSAST_VERIFY", "True").strip()
    if verify_raw.lower() in ("false", "0", "no", "off"):
        verify = False
    elif verify_raw.lower() in ("true", "1", "yes"):
        verify = True
    else:
        verify = verify_raw
    base_url = os.getenv("CXSAST_BASE_URL", "https://desktop-rmvpboc").rstrip("/")
    return Configuration(
        server_base_url=base_url,
        token_url=f"{base_url}/cxrestapi/auth/identity/connect/token",
        username=os.getenv("CXSAST_USERNAME", ""),
        password=os.getenv("CXSAST_PASSWORD", ""),
        grant_type=os.getenv("CXSAST_GRANT_TYPE", "password"),
        scope=os.getenv("CXSAST_SCOPE", "sast_rest_api"),
        client_id=os.getenv("CXSAST_CLIENT_ID", "resource_owner_client"),
        client_secret=os.getenv("CXSAST_CLIENT_SECRET", "014DF517-39D1-4453-B7B3-9930C563627C"),
        verify=verify,
        timeout=60,
        max_retries=3,
    )


config = load_configuration()
api_client = ApiClient(configuration=config)
projects_api = ProjectsAPI(api_client=api_client)
team_api = TeamAPI(api_client=api_client)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# --- Optional API key auth ---
API_KEY = os.getenv("APP_API_KEY", "")


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


# --- Helpers ---
def _format_error(e):
    return str(e) or type(e).__name__


def _safe_sdk_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        return None, _format_error(e)


def get_all_projects():
    return projects_api.get_all_project_details()


def build_children_map(all_projects):
    children_map = {}
    for p in all_projects:
        parent_id = p.original_project_id
        if parent_id and parent_id != "":
            children_map.setdefault(int(parent_id), []).append(p.project_id)
    return children_map


def build_tree_node(project_id, projects_map, children_map, team_map):
    project = projects_map[project_id]
    child_ids = children_map.get(project_id, [])
    team_info = team_map.get(str(project.team_id) if project.team_id else "", {})
    orig_id = project.original_project_id
    if orig_id == "" or orig_id is None:
        orig_id = None
    else:
        try:
            orig_id = int(orig_id)
        except (TypeError, ValueError):
            orig_id = None

    return {
        "project_id": project.project_id,
        "name": project.name,
        "team_id": project.team_id,
        "team_name": team_info.get("name", ""),
        "team_full_name": team_info.get("full_name", ""),
        "is_public": project.is_public,
        "is_branched": project.is_branched or False,
        "original_project_id": orig_id,
        "branched_on_scan_id": project.branched_on_scan_id,
        "owner": project.owner,
        "is_deprecated": project.is_deprecated,
        "is_leaf": len(child_ids) == 0,
        "child_count": len(child_ids),
        "children": sorted(
            [build_tree_node(cid, projects_map, children_map, team_map) for cid in child_ids],
            key=lambda n: (n["name"] or ""),
        ),
    }


def build_full_tree():
    all_projects, err = _safe_sdk_call(get_all_projects)
    if err:
        raise RuntimeError(err)

    projects_map = {p.project_id: p for p in all_projects}
    children_map = build_children_map(all_projects)

    teams, err = _safe_sdk_call(team_api.get_all_teams)
    team_map = {}
    if err is None:
        team_map = {str(t.team_id): {"name": t.name, "full_name": t.full_name} for t in teams}

    all_project_ids = {p.project_id for p in all_projects}
    child_ids_set = set()
    for cids in children_map.values():
        child_ids_set.update(cids)

    # Parents that actually exist
    valid_parent_ids = child_ids_set & all_project_ids
    # Branches whose parent was deleted — treat them as roots
    dangling = child_ids_set - all_project_ids

    root_ids = (all_project_ids - child_ids_set) | dangling

    tree = sorted(
        [build_tree_node(rid, projects_map, children_map, team_map) for rid in root_ids],
        key=lambda n: (n["name"] or ""),
    )
    return {"projects": tree, "total_projects": len(all_projects)}


# --- Error handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# --- Routes ---
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health_check():
    projects, err = _safe_sdk_call(projects_api.get_all_project_details)
    if err:
        return jsonify({"status": "error", "message": err}), 500
    return jsonify({
        "status": "ok",
        "server": config.server_base_url,
        "project_count": len(projects),
    })


@app.route("/api/projects/tree")
@require_auth
def get_projects_tree():
    try:
        tree = build_full_tree()
        return jsonify(tree)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id):
    all_projects, err = _safe_sdk_call(get_all_projects)
    if err:
        return jsonify({"error": err}), 500

    children_map = build_children_map(all_projects)
    child_ids = children_map.get(project_id, [])
    if child_ids:
        projects_map = {p.project_id: p for p in all_projects}
        child_names = [
            f"#{cid} ({projects_map.get(cid).name if cid in projects_map else 'unknown'})"
            for cid in child_ids
        ]
        return jsonify({
            "error": f"Cannot delete project #{project_id}: it has {len(child_ids)} branched child(ren).",
            "details": f"Delete these branches first: {', '.join(child_names)}",
            "child_project_ids": child_ids,
        }), 400

    result, err = _safe_sdk_call(
        projects_api.delete_project_by_id, project_id, delete_running_scans=False
    )
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"success": result, "deleted_project_id": project_id})


@app.route("/api/projects/delete-batch", methods=["POST"])
@require_auth
def delete_batch_projects():
    data = request.get_json(silent=True)
    if not data or not isinstance(data.get("project_ids"), list):
        return jsonify({"error": "Request body must contain 'project_ids' as a list of integers."}), 400

    project_ids = data["project_ids"]
    if not project_ids:
        return jsonify({"error": "No project IDs provided."}), 400

    all_projects, err = _safe_sdk_call(get_all_projects)
    if err:
        return jsonify({"error": err}), 500

    projects_map = {p.project_id: p for p in all_projects}
    children_map = build_children_map(all_projects)

    invalid = []
    for pid in project_ids:
        child_ids = children_map.get(pid, [])
        if child_ids:
            invalid.append({
                "project_id": pid,
                "name": projects_map.get(pid).name if pid in projects_map else "unknown",
                "child_count": len(child_ids),
                "child_ids": child_ids,
            })

    if invalid:
        return jsonify({
            "error": "Some projects cannot be deleted because they have branched children.",
            "invalid_projects": invalid,
        }), 400

    deleted = []
    errors = []
    for pid in project_ids:
        _, err = _safe_sdk_call(
            projects_api.delete_project_by_id, pid, delete_running_scans=False
        )
        if err:
            errors.append({"project_id": pid, "error": err})
        else:
            deleted.append(pid)

    return jsonify({
        "success": len(errors) == 0,
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "errors": errors,
    })


@app.route("/api/teams")
def get_teams():
    teams, err = _safe_sdk_call(team_api.get_all_teams)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({
        "teams": [
            {"team_id": t.team_id, "name": t.name, "full_name": t.full_name, "parent_id": t.parent_id}
            for t in teams
        ]
    })


@app.route("/api/debug")
def debug_info():
    """Diagnostic endpoint: shows exactly what the SDK returns from CxSAST."""
    all_projects, err = _safe_sdk_call(get_all_projects)
    if err:
        return jsonify({"error": err}), 500

    teams, team_err = _safe_sdk_call(team_api.get_all_teams)

    # Build team id → full_name map
    team_map = {}
    if teams:
        for t in teams:
            team_map[str(t.team_id)] = t.full_name

    # Count projects per team
    per_team = {}
    for p in all_projects:
        tid = str(p.team_id) if p.team_id else "(none)"
        per_team.setdefault(tid, 0)
        per_team[tid] += 1

    # Check for expected teams that are missing
    all_team_names = [t.full_name for t in teams] if teams else []
    project_team_ids = {str(p.team_id) for p in all_projects if p.team_id}
    unknown_teams = [tid for tid in project_team_ids if tid not in team_map]
    empty_teams = [tn for tn in all_team_names if tn not in [
        team_map.get(str(p.team_id)) for p in all_projects
    ]]

    return jsonify({
        "total_projects": len(all_projects),
        "total_teams_in_api": len(teams) if teams else 0,
        "projects_per_team": dict(sorted(per_team.items())),
        "team_name_map": {str(k): v for k, v in sorted(team_map.items())},
        "unknown_team_ids": unknown_teams,
        "teams_with_no_projects": empty_teams,
        "server_base_url": config.server_base_url,
        "username": config.username,
    })


# --- Main ---
if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", "5000"))
    host = os.getenv("APP_HOST", "0.0.0.0")
    debug = os.getenv("APP_DEBUG", "0").lower() in ("1", "true", "yes")

    try:
        from waitress import serve
        print(f"Starting production server on {host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        print(f"Starting Flask dev server on {host}:{port} (install waitress for production)")
        app.run(host=host, port=port, debug=debug)
