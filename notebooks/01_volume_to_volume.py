# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Volume to Volume Connector
# MAGIC Copies newly landed files from the source Volume (where files are dropped)
# MAGIC into the processing Volume that the Raw Manager reads from.
# MAGIC
# MAGIC Widgets let this notebook be reused for any product defined in the data
# MAGIC contract repository.

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
from dat_edip.connectors.volume_to_volume import copy_volume_to_volume

contract = load_contract(contract_repo_root, product_name)
print(f"Loaded contract for product: {contract.product_name} (owner: {contract.developer_name})")

# COMMAND ----------
source_path = contract.source["path"]
target_path = contract.target["volume"]["path"]

copied_count = copy_volume_to_volume(source_path, target_path, dbutils=dbutils)
print(f"Copied {copied_count} file(s) from {source_path} to {target_path}")
