import asyncio
import time

import logging
from contextlib import ExitStack
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from application.clients.reqmgr_client import ReqMgrClient
from application.db import get_collection
from application.services.relval_parsing_service import RelvalParsingService
from core_lib.utils.emailer import Emailer
from core_lib.utils.global_config import Config
from core_lib.utils.locker import Locker
from database.database import Database


class RelvalUpdateService:
    BATCH_SIZE = 100

    def __init__(self):
        self.service_url = Config.get("service_url")
        self.cmsweb_url = Config.get("cmsweb_url")
        self.is_development = Config.get("development")
        self.reqmgr_client = ReqMgrClient()
        self.relval_parsing_service = RelvalParsingService()
        self.emailer = Emailer()
        self.logger = logging.getLogger()
        self.locker = Locker()

    def check_workflow_status(self, app):
        """
        Monitors the status of RelVals and sends an email when the status changes to 'announced'.
        """
        db_relvals = self.__get_relvals_from_db()
        reqmgr_workflows = self.__get_workflows_from_reqmgr2(db_relvals)
        relvals_to_update = self.__find_relvals_to_update(db_relvals, reqmgr_workflows)
        with app.app_context():
            asyncio.run(self.__run_status_updates_async(relvals_to_update))

    def __get_relvals_from_db(self) -> list:
        relval_db = Database("relvals")
        relvals_collection = relval_db.collection

        projection = {"prepid": 1, "steps": 1, "history": 1, "workflows": 1}

        return list(relvals_collection.find({}, projection))

    def __get_workflows_from_reqmgr2(self, relvals: list) -> list:
        prepids = [x["prepid"] for x in relvals]
        masks = [
            "RequestName",
            "RequestStatus",
            "PrepID",
            "RequestType",
            "EventNumberHistory",
            "Datasets",
            "RequestTransition",
            "UpdateTime",
            "OutputDatasets",
        ]
        return self.reqmgr_client.get_batched_workflows_for_prepids(
            self.BATCH_SIZE, prepids, masks
        )

    def __find_relvals_to_update(
        self, db_relvals: list[dict], reqmgr_workflows: list[dict]
    ) -> dict:
        """
        {
            "PrepId1": {
                "relval": [],
                "all_workflows": {},
                "workflows_to_notify": []
            }
        }
        """

        def __group_reqmgr_workflows_by_prepid(reqmgr_workflows: list[dict]) -> dict:
            """
            Groups a flat dictionary of reqmgr workflows by their PrepID like:
            {
                "PrepId1": {
                    "workflow_id1": {},
                    "workflow_id2": {}
                }
            }
            """
            grouped = {}
            for reqmgr_wf in reqmgr_workflows:
                prepid = reqmgr_wf.get("PrepID")
                if isinstance(prepid, str):
                    grouped.setdefault(prepid, {})[
                        reqmgr_wf.get("RequestName")
                    ] = reqmgr_wf
                else:
                    self.logger.error("Failed to get single prepid %s", prepid)
            return grouped

        reqmgr_grouped_by_prepid = __group_reqmgr_workflows_by_prepid(reqmgr_workflows)
        changed_relvals = {}
        for relval in db_relvals:
            workflows_to_notify = []
            prepid = relval["prepid"]
            all_workflows = reqmgr_grouped_by_prepid.get(prepid, {})
            for workflow_id, reqmgr_wf in all_workflows.items():
                db_wf = next(
                    (
                        wf
                        for wf in relval.get("workflows", [])
                        if wf.get("name") == workflow_id
                    ),
                    None,
                )
                if not db_wf or self.__should_notify_about_workflow(db_wf, reqmgr_wf):
                    workflows_to_notify.append(workflow_id)
            if len(workflows_to_notify) > 0:
                changed_relvals[prepid] = {
                    "relval": relval,
                    "all_workflows": all_workflows,
                    "workflows_to_notify": workflows_to_notify,
                }
        return changed_relvals

    def __should_notify_about_workflow(
        self, db_workflow: dict, reqmgr_workflow: dict
    ) -> bool:
        latest_db_status = max(
            db_workflow.get("status_history", []), key=lambda item: item.get("time", 0), default={}
        ).get("status", "")
        reqmgr_statuses = {
            item.get("Status") for item in reqmgr_workflow.get("RequestTransition", [])
        }
        final_states = {"announced", "normal-archived"}

        if latest_db_status not in final_states and final_states.intersection(
            reqmgr_statuses
        ):
            return True
        return False

    async def __run_status_updates_async(self, relvals_to_update: dict):
        if len(relvals_to_update) == 0:
            self.logger.info("No relvals to update.")
            return
        fetch_task = self.__update_workflows(relvals_to_update)
        email_task = self.__send_email(relvals_to_update)

        await asyncio.gather(fetch_task, email_task)

    async def __update_workflows(self, relvals: dict):
        relvals_collection = get_collection("relvals")
        locks_to_acquire = [
            self.locker.get_lock(relval) for relval, _ in relvals.items()
        ]
        with ExitStack() as stack:
            for lock in locks_to_acquire:
                stack.enter_context(lock)

            operations = []
            current_timestamp = int(time.time())
            for prepid, details in relvals.items():

                output_datasets = self.relval_parsing_service.get_output_datasets(
                    details["relval"].get("steps"), details["all_workflows"]
                )
                workflows = self.relval_parsing_service.pick_workflow(
                    details["all_workflows"], output_datasets
                )
                operation = UpdateOne(
                    {"_id": prepid},
                    {
                        "$set": {
                            "workflows": workflows,
                            "output_datasets": output_datasets,
                            "last_update": current_timestamp,
                        }
                    },
                )
                operations.append(operation)
            try:
                result = relvals_collection.bulk_write(operations)
                self.logger.debug(
                    "Batch update successful. Matched: %s, Modified: %s",
                    result.matched_count,
                    result.modified_count,
                )
            except BulkWriteError as bwe:
                self.logger.error("A batch update error occurred: %s", bwe.details)
            except Exception as e:
                self.logger.error(
                    "An unexpected error occurred during the batch update: %s", e
                )

    async def __send_email(self, relvals_to_update: dict):
        """
        Notifies when a relval is updated to 'announced' or 'normal-archived'.
        """
        subject = f"{len(relvals_to_update)} Relvals Updated"
        if self.is_development:
            self.logger.info(subject)
            return

        body = "Hello,\n\nThe status of RelVal workflows were updated.\n\n"
        recipients = []
        for prepid, workflows in relvals_to_update.items():
            body += f'Updated Relval: <a href="{self.service_url}/relvals?prepid={prepid}">{prepid}</a>\n'
            for workflow in workflows["workflows_to_notify"]:
                body += f'Relevant workflow: <a href="{self.cmsweb_url}/reqmgr2/fetch?rid={workflow}">{workflow}</a>\n'
            relval = workflows["relval"]
            body += "\n"
            # Workaround for logging in Emailer:36
            relval_obj = RelvalWithMethods(relval)
            recipients += self.emailer.get_recipients(relval_obj)

        recipients = set(recipients)
        self.emailer.send_with_mime(subject, body, recipients)
        self.logger.debug(
            "Email sent to %s about the status update of RelVal '%s' to 'announced'.",
            recipients,
            list(relvals_to_update.keys()),
        )


# Workaround for logging in Emailer:36
class RelvalWithMethods(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_prepid(self):
        return self.get("prepid", "N/A")
