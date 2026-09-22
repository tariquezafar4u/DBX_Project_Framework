"""
Basic Raw Manager.

Reads the landed files (from the processing Volume) using the schema defined
in the data contract and appends them, as-is, into the Raw Delta table. No
validation happens here - Raw is intentionally a faithful copy of the source.
"""
from __future__ import annotations

from dat_edip.contract_loader import DataContract

_SPARK_TYPE_MAP = {
    "string": "StringType",
    "date": "DateType",
    "timestamp": "TimestampType",
    "double": "DoubleType",
    "float": "FloatType",
    "int": "IntegerType",
    "long": "LongType",
    "boolean": "BooleanType",
}


def build_spark_schema(contract: DataContract):
    """Build a PySpark StructType from the contract's column definitions."""
    from pyspark.sql.types import (
        BooleanType,
        DateType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    type_lookup = {
        "StringType": StringType(),
        "DateType": DateType(),
        "TimestampType": TimestampType(),
        "DoubleType": DoubleType(),
        "FloatType": FloatType(),
        "IntegerType": IntegerType(),
        "LongType": LongType(),
        "BooleanType": BooleanType(),
    }

    fields = []
    for col in contract.columns:
        spark_type_name = _SPARK_TYPE_MAP.get(col.data_type.lower(), "StringType")
        fields.append(StructField(col.name, type_lookup[spark_type_name], col.nullable))
    return StructType(fields)


def load_raw(spark, contract: DataContract):
    """
    Read files from the target processing Volume path (contract.target.volume)
    and append into the raw table (contract.target.raw), using the contract
    schema. Returns the DataFrame that was written for convenience in tests.
    """
    schema = build_spark_schema(contract)
    volume_path = contract.target["volume"]["path"]
    file_format = contract.source.get("file_format", "csv")
    options = contract.source.get("options", {})

    reader = spark.read.format(file_format).schema(schema)
    for key, value in options.items():
        reader = reader.option(key, value)
    df = reader.load(volume_path)

    raw_table = _full_table_name(contract.target["raw"])
    df.write.mode("append").format("delta").saveAsTable(raw_table)
    return df


def _full_table_name(table_cfg: dict) -> str:
    return f"{table_cfg['catalog']}.{table_cfg['schema']}.{table_cfg['table']}"
