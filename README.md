# DAT-EDIP Framework (Learning Project)

A **simplified learning version** of the DAT-EDIP framework. It shows the core
architecture — Volume→Volume connector, Raw Manager, Stage Manager, and
validations — driven by a data contract from the companion `data-contract-repo`.

## Flow

```
Data Contract Repo  --->  DAT-EDIP Framework  --->  GitHub Actions
        |                                                  |
        v                                                  v
  contract.yaml                                    Databricks Job
        |                                                  |
        +------------------> Volume-to-Volume Connector <--+
                                     |
                                     v
                               Raw Manager (raw table)
                                     |
                                     v
                          Stage Manager + Validations
                                     |
                                     v
                               Stage table (clean data)
```

## Repository layout

```
.github/workflows/deploy.yml     GitHub Actions workflow -> deploys job to Databricks
config/framework_config.yaml     Framework-level settings (workspace, catalog defaults)
scripts/deploy_and_run.ps1       Reads contract + framework config, creates/updates the
                                  Databricks job, and triggers a run
notebooks/
  01_volume_to_volume.py         Notebook: copies files from source Volume to target Volume
  02_raw_manager.py              Notebook: loads landed files into the Raw table
  03_stage_manager.py            Notebook: validates Raw data and loads it into Stage
src/dat_edip/
  contract_loader.py             Loads and parses contract.yaml into a Python object
  connectors/volume_to_volume.py Volume-to-volume copy connector
  raw_manager.py                 Raw layer load logic
  stage_manager.py                Stage layer load + orchestration of validations
  validations.py                 PK / not-null / trim / data-type / range checks
```

## Learning flow (matches the overall objective)

1. Deploy `data-contract-repo` first (just needs to exist somewhere the framework
   can read from — a Databricks Repo, Volume, or local checkout for this exercise).
2. Deploy this `dat-edip-framework` repo (GitHub Actions workflow -> Databricks).
3. Authenticate the Databricks CLI and review the bundle plan:
   ```bat
   databricks auth login --host "https://adb-7405614984857704.4.azuredatabricks.net/" --profile dev
   deploy_learning.bat plan
   ```
4. Deploy the bundle with `deploy_learning.bat`.
5. For the legacy product-specific workflow, run
   `deploy_learning.bat customer_orders`.
   - It reads `contracts/customer_orders/contract.yaml` from the contract repo.
   - It reads `config/framework_config.yaml` from this repo.
   - It creates/updates a Databricks Job made of the three notebooks in order.
   - It triggers a run of that job.
6. The Databricks Job runs: Volume→Volume copy -> Raw Manager -> Stage Manager
   (with validations) -> data lands in the Stage table.

## Notes

This is intentionally minimal: no multi-environment promotion, no secret
scopes, no retries/alerting. It exists purely so you can see how the pieces
connect end-to-end before looking at the real production framework.
