import logging


class RelvalParsingService:
    DEAD_WORKFLOW_STATUS = {
        "rejected",
        "aborted",
        "failed",
        "rejected-archived",
        "aborted-archived",
        "failed-archived",
        "aborted-completed",
    }

    def __init__(self):
        self.logger = logging.getLogger()

    def get_output_datasets(self, steps: list, all_workflows: dict) -> list:
        """
        Return a list of sorted output datasets for RelVal from given workflows
        """
        output_datatiers = []
        for step in steps:
            output_datatiers.extend(step.get("driver")["datatier"])

        output_datatiers_set = set(output_datatiers)
        output_datasets_tree = {k: {} for k in output_datatiers}
        for workflow_name, workflow in all_workflows.items():
            if workflow.get("RequestType", "").lower() == "resubmission":
                continue

            status_history = set(
                x["Status"] for x in workflow.get("RequestTransition", [])
            )
            if self.DEAD_WORKFLOW_STATUS & status_history:
                self.logger.debug("Ignoring %s", workflow_name)
                continue

            for output_dataset in workflow.get("OutputDatasets", []):
                output_dataset_parts = [x.strip() for x in output_dataset.split("/")]
                output_dataset_datatier = output_dataset_parts[-1]
                output_dataset_no_datatier = "/".join(output_dataset_parts[:-1])
                output_dataset_no_version = "-".join(
                    output_dataset_no_datatier.split("-")[:-1]
                )
                if output_dataset_datatier in output_datatiers_set:
                    datatier_tree = output_datasets_tree[output_dataset_datatier]
                    if output_dataset_no_version not in datatier_tree:
                        datatier_tree[output_dataset_no_version] = []

                    datatier_tree[output_dataset_no_version].append(output_dataset)

        output_datasets = []
        for _, datasets_without_versions in output_datasets_tree.items():
            for _, datasets in datasets_without_versions.items():
                if datasets:
                    output_datasets.append(sorted(datasets)[-1])

        def tier_level_comparator(dataset):
            dataset_tier = dataset.split("/")[-1:][0]
            if dataset_tier in output_datatiers_set:
                return output_datatiers.index(dataset_tier)

            return -1

        output_datasets = sorted(output_datasets, key=tier_level_comparator)
        return output_datasets

    def pick_workflow(self, all_workflows: dict, output_datasets):
        """
        Pick, process and sort workflows from computing based on output datasets
        """
        new_workflows = []
        self.logger.info(
            "Picking workflows %s for datasets %s",
            [x["RequestName"] for x in all_workflows.values()],
            output_datasets,
        )
        for _, workflow in all_workflows.items():
            new_workflow = {
                "name": workflow["RequestName"],
                "type": workflow["RequestType"],
                "output_datasets": [],
                "status_history": [],
            }
            for output_dataset in output_datasets:
                history_entries = workflow.get("EventNumberHistory", [])
                if not history_entries:
                    history_entries = []
                for history_entry in reversed(history_entries):
                    if output_dataset in history_entry["Datasets"]:
                        dataset_dict = history_entry["Datasets"][output_dataset]
                        new_workflow["output_datasets"].append(
                            {
                                "name": output_dataset,
                                "type": dataset_dict["Type"],
                                "events": dataset_dict["Events"],
                            }
                        )
                        break

            for request_transition in workflow.get("RequestTransition", []):
                new_workflow["status_history"].append(
                    {
                        "time": request_transition["UpdateTime"],
                        "status": request_transition["Status"],
                    }
                )

            new_workflows.append(new_workflow)

        new_workflows = sorted(
            new_workflows, key=lambda w: "_".join(w["name"].split("_")[-3:])
        )
        self.logger.info(
            "Picked workflows:\n%s", ", ".join([w["name"] for w in new_workflows])
        )
        return new_workflows
