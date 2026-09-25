# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Raw Manager
# MAGIC Reads the files staged in the processing Volume using the schema defined in
# MAGIC the data contract, and appends them into the Raw Delta table. No data
# MAGIC validation happens at this layer - Raw is a faithful copy of the source.

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
from dat_edip.raw_manager import load_raw

contract = load_contract(contract_repo_root, product_name)

# COMMAND ----------
raw_catalog = contract.target["raw"]["catalog"]
raw_schema = contract.target["raw"]["schema"]
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {raw_catalog}.{raw_schema}")

df = load_raw(spark, contract)
print(f"Loaded {df.count()} row(s) into raw table "
      f"{contract.target['raw']['catalog']}.{contract.target['raw']['schema']}.{contract.target['raw']['table']}")
