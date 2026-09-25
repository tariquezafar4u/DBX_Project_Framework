# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - Stage Manager
# MAGIC Reads the Raw table, runs the validation suite described in the data
# MAGIC contract (primary key, not-null, trim, data-type, allowed values, range),
# MAGIC writes good rows to the Stage table and rejected rows to the quarantine
# MAGIC table.

# COMMAND ----------
dbutils.widgets.text("product_name", "customer_orders")
dbutils.widgets.text("contract_repo_root", "/Workspace/Shared/data_contract_repo")
dbutils.widgets.text("framework_root", "/Workspace/Users/tariquemdzafar@outlook.com/dat_edip_framework")

product_name = dbutils.widgets.get("product_name")
contract_repo_root = dbutils.widgets.get("contract_repo_root")
framework_root = dbutils.widgets.get("framework_root")

# COMMAND ----------
import sys
sys.path.insert(0, f"{framework_root}/src")

from dat_edip.contract_loader import load_contract
from dat_edip.stage_manager import load_stage

contract = load_contract(contract_repo_root, product_name)

# COMMAND ----------
for layer_key in ("stage", "quarantine"):
    cfg = contract.target[layer_key]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cfg['catalog']}.{cfg['schema']}")

good_count, bad_count, notes = load_stage(spark, contract)

print(f"Stage load complete for '{contract.product_name}'.")
print(f"  Good rows -> stage table: {good_count}")
print(f"  Rejected rows -> quarantine table: {bad_count}")
print("  Validations applied:")
for note in notes:
    print(f"   - {note}")
