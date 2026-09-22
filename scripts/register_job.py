"""
Creates (or updates) the DAT-EDIP Databricks Job from config/framework_config.yaml.
Used both by the GitHub Actions workflow and by scripts/deploy_and_run.ps1.

Requires: databricks-cli (or databricks-sdk) configured with DATABRICKS_HOST /
DATABRICKS_TOKEN environment variables.
"""
from __future__ import annotations

import argparse
import json
import os

import yaml


def load_job_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_job_spec(cfg: dict, notebook_root: str, product_name: str, contract_repo_root: str) -> dict:
    """Turn the framework_config.yaml job section into a Databricks Jobs API v2.1 payload."""
    job_cfg = cfg["job"]
    cluster_cfg = cfg["databricks"]["cluster"]

    tasks = []
    for nb in job_cfg["notebooks"]:
        task = {
            "task_key": nb["key"],
            "notebook_task": {
                "notebook_path": f"{notebook_root}/{nb['path']}",
                "base_parameters": {
                    "product_name": product_name,
                    "contract_repo_root": contract_repo_root,
                },
            },
            "new_cluster": {
                "node_type_id": cluster_cfg["node_type_id"],
                "spark_version": cluster_cfg["spark_version"],
                "num_workers": cluster_cfg["num_workers"],
                "autotermination_minutes": cluster_cfg["autotermination_minutes"],
            },
        }
        if "depends_on" in nb:
            task["depends_on"] = [{"task_key": dep} for dep in nb["depends_on"]]
        tasks.append(task)

    return {
        "name": f"{job_cfg['name']}_{product_name}",
        "tasks": tasks,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-config", required=True)
    parser.add_argument("--notebook-root", required=True)
    parser.add_argument("--product-name", default="customer_orders")
    parser.add_argument("--contract-repo-root", default="/Workspace/Shared/data_contract_repo")
    parser.add_argument("--print-only", action="store_true",
                         help="Print the job spec instead of calling the Databricks API")
    args = parser.parse_args()

    cfg = load_job_config(args.job_config)
    job_spec = build_job_spec(cfg, args.notebook_root, args.product_name, args.contract_repo_root)

    if args.print_only:
        print(json.dumps(job_spec, indent=2))
        return

    # Deferred import: only needed when actually talking to Databricks.
    from databricks_cli.sdk.api_client import ApiClient
    from databricks_cli.jobs.api import JobsApi

    client = ApiClient(host=os.environ["DATABRICKS_HOST"], token=os.environ["DATABRICKS_TOKEN"])
    jobs_api = JobsApi(client)

    existing = [j for j in jobs_api.list_jobs().get("jobs", []) if j["settings"]["name"] == job_spec["name"]]
    if existing:
        job_id = existing[0]["job_id"]
        jobs_api.reset_job({"job_id": job_id, "new_settings": job_spec})
        print(f"Updated existing job_id={job_id} ({job_spec['name']})")
    else:
        result = jobs_api.create_job(job_spec)
        job_id = result["job_id"]
        print(f"Created new job_id={job_id} ({job_spec['name']})")

    print(job_id)


if __name__ == "__main__":
    main()
