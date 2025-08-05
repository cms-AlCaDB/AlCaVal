import requests
from core_lib.utils.global_config import Config


class ReqMgrClient:

    def __init__(self):
        self.session = requests.Session()
        self.cmsweb_url = Config.get("cmsweb_url")
        self.grid_cert = Config.get("grid_user_cert")
        self.grid_key = Config.get("grid_user_key")
        self.headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
        }

    def get_batched_workflows_for_prepids(
        self, batch_size: int, prep_ids: list, masks: list = None
    ) -> list:
        workflow_statuses = []
        for i in range(0, len(prep_ids), batch_size):
            batch = prep_ids[i : i + batch_size]
            params = {"prep_id": batch}
            if masks is not None:
                params["mask"] = masks
            response = self.session.get(
                self.cmsweb_url + "/reqmgr2/data/request",
                params=params,
                timeout=60,
                cert=(self.grid_cert, self.grid_key),
                verify=False,
            )
            response.raise_for_status()

            result_list = response.json().get("result", [])

            if not isinstance(result_list, list) or len(result_list) == 0:
                continue

            for _, details in result_list[0].items():
                if not isinstance(details, dict):
                    continue

                workflow_statuses.append(details)
        return workflow_statuses
