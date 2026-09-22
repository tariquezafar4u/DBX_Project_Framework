"""
Loads a data contract (contract.yaml) into a plain Python object the rest of
the framework can use. Kept dependency-light: only PyYAML is required.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnDef:
    name: str
    data_type: str
    nullable: bool
    trim: bool = False


@dataclass
class DataContract:
    product_name: str
    developer_name: str
    source: dict
    target: dict
    primary_key: list
    columns: list
    validations: dict = field(default_factory=dict)

    def column_names(self) -> list:
        return [c.name for c in self.columns]

    def not_null_columns(self) -> list:
        return [c.name for c in self.columns if not c.nullable]


def _load_yaml(path: str) -> dict:
    import yaml  # local import so the framework only needs PyYAML at runtime

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_contract(contract_repo_root: str, product_name: str) -> DataContract:
    """
    Read contracts/<product_name>/contract.yaml under the given contract repo
    root and return a DataContract instance.
    """
    contract_path = os.path.join(
        contract_repo_root, "contracts", product_name, "contract.yaml"
    )
    if not os.path.exists(contract_path):
        raise FileNotFoundError(f"No contract found for product '{product_name}' at {contract_path}")

    raw: dict[str, Any] = _load_yaml(contract_path)

    columns = [
        ColumnDef(
            name=c["name"],
            data_type=c["data_type"],
            nullable=c.get("nullable", True),
            trim=c.get("trim", False),
        )
        for c in raw.get("columns", [])
    ]

    return DataContract(
        product_name=raw["product_name"],
        developer_name=raw["owner"]["developer_name"],
        source=raw["source"],
        target=raw["target"],
        primary_key=raw.get("primary_key", []),
        columns=columns,
        validations=raw.get("validations", {}),
    )
