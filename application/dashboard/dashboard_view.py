"""
Dashboard routes
"""
import json
import os
from flask import Blueprint, jsonify, render_template
from application import get_userinfo
from core_lib.utils.global_config import Config

dashboard_blueprint = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
)
TRANSITIONS_FILE = Config.get("relval_transition_file")


@dashboard_blueprint.route("", strict_slashes=False, methods=["GET"])
def show_dashboard():
    """
    Show Dashboard Jinja page
    """
    get_userinfo()
    return render_template("Dashboard.html.jinja")


@dashboard_blueprint.route("/dashboard-data", methods=["GET"])
def get_dashboard_data():
    """
    Checks the age of the data file and returns its contents if it's fresh.
    """
    try:
        file_mod_time = os.path.getmtime(TRANSITIONS_FILE)

        with open(TRANSITIONS_FILE, "r", encoding="UTF-8") as f:
            data = json.load(f)
        return jsonify({"last_updated": int(file_mod_time), "results": data})

    except FileNotFoundError:
        return (
            jsonify(
                {"error": "Data not available yet. Wait for the first job to run."}
            ),
            404,
        )
