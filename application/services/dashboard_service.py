"""
Dashboard service module
"""

import json
import time
import logging
import pandas as pd
from flask import jsonify
from application.db import get_collection
from core_lib.utils.global_config import Config


class DashboardService:
    """
    Service for Dashboard histograms data gathering
    """

    def __init__(self):
        self.logger = logging.getLogger()

    def process_relval_transitions(self, flask_app):
        """
        Background job to query database and process Relval transitions
        """
        with flask_app.app_context():
            start_time = time.time()
            relvals_collection = get_collection("relvals")

            query = {"workflows": {"$ne": []}}
            projection = {
                "_id": 0,
                "batch_name": 1,
                "workflows.name": 1,
                "workflows.status_history": 1,
            }

            all_events = []
            for doc in relvals_collection.find(query, projection):
                for workflow in doc.get("workflows", []):
                    for history_event in workflow.get("status_history", []):
                        all_events.append(
                            {
                                "workflow_name": workflow.get("name"),
                                "batch_name": doc.get("batch_name"),
                                "status": history_event.get("status"),
                                "time": history_event.get("time"),
                            }
                        )

            if not all_events:
                self.logger.debug("No statuses found in DB to process.")
                return

            df = pd.DataFrame(all_events)
            transitions = []
            for _, group in df.groupby("workflow_name"):
                group_transitions = pd.DataFrame(
                    {
                        "from": group["status"],
                        "to": group["status"].shift(-1),
                        "start": group["time"],
                        "batch_name": group["batch_name"],
                        "duration_seconds": group["time"].shift(-1) - group["time"],
                    }
                )

                group_transitions.dropna(
                    inplace=True, subset=["to", "duration_seconds"]
                )
                group_transitions["duration_seconds"] = group_transitions[
                    "duration_seconds"
                ].astype(int)
                transitions.extend(group_transitions.to_dict("records"))

            with open(Config.get("relval_transition_file"), "w", encoding="UTF-8") as f:
                json.dump(transitions, f)

            self.logger.info(
                "--- RelVal transition fetching finished in %s seconds ---",
                time.time() - start_time,
            )

            return jsonify(transitions)
