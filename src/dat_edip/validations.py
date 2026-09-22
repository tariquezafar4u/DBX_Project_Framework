"""
Validation checks used by the Stage Manager. Kept simple and framework
agnostic where possible - each function takes a Spark DataFrame and a
contract and returns (good_df, bad_df, list_of_issue_descriptions).
"""
from __future__ import annotations

from dat_edip.contract_loader import DataContract


def check_primary_key(df, contract: DataContract):
    """Flag rows whose primary key columns are null or duplicated."""
    from pyspark.sql import functions as F

    pk_cols = contract.primary_key
    if not pk_cols:
        return df, df.limit(0), ["no primary key defined - skipped"]

    null_pk = F.lit(False)
    for c in pk_cols:
        null_pk = null_pk | F.col(c).isNull()

    dup_counts = df.groupBy(*pk_cols).count().filter(F.col("count") > 1)
    dup_keys = dup_counts.select(*pk_cols)

    flagged = df.join(dup_keys, on=pk_cols, how="left_semi")
    bad = df.filter(null_pk).unionByName(flagged).dropDuplicates()
    good = df.subtract(bad)
    return good, bad, [f"primary_key_check on {pk_cols}"]


def check_not_null(df, contract: DataContract):
    """Flag rows where any required (non-nullable) column is null."""
    from pyspark.sql import functions as F

    required_cols = contract.not_null_columns()
    if not required_cols:
        return df, df.limit(0), ["no not-null columns defined - skipped"]

    condition = F.lit(False)
    for c in required_cols:
        condition = condition | F.col(c).isNull()

    bad = df.filter(condition)
    good = df.filter(~condition)
    return good, bad, [f"not_null_check on {required_cols}"]


def apply_trim(df, contract: DataContract):
    """Trim whitespace on all string columns flagged trim=true in the contract."""
    from pyspark.sql import functions as F

    trim_cols = [c.name for c in contract.columns if c.trim]
    for c in trim_cols:
        df = df.withColumn(c, F.trim(F.col(c)))
    return df, [f"trim applied on {trim_cols}"] if trim_cols else []


def check_data_types(df, contract: DataContract):
    """
    Basic data-type validation: attempt to cast each column to its contract
    type and flag rows where the cast produces a null from a non-null input
    (i.e. the value did not actually match the expected type).
    """
    from pyspark.sql import functions as F

    _cast_map = {
        "string": "string",
        "int": "int",
        "long": "bigint",
        "double": "double",
        "float": "float",
        "boolean": "boolean",
        "date": "date",
        "timestamp": "timestamp",
    }

    condition = F.lit(False)
    checked_cols = []
    for col in contract.columns:
        cast_type = _cast_map.get(col.data_type.lower())
        if not cast_type or col.data_type.lower() == "string":
            continue
        checked_cols.append(col.name)
        cast_failed = F.col(col.name).isNotNull() & F.col(col.name).cast(cast_type).isNull()
        condition = condition | cast_failed

    bad = df.filter(condition)
    good = df.filter(~condition)
    return good, bad, [f"data_type_check on {checked_cols}"] if checked_cols else []


def check_allowed_values(df, contract: DataContract):
    """Flag rows whose value in a column is outside the contract's allowed list."""
    from pyspark.sql import functions as F

    allowed_values = contract.validations.get("allowed_values", {})
    if not allowed_values:
        return df, df.limit(0), []

    condition = F.lit(False)
    for col_name, allowed in allowed_values.items():
        condition = condition | (~F.col(col_name).isin(allowed) & F.col(col_name).isNotNull())

    bad = df.filter(condition)
    good = df.filter(~condition)
    return good, bad, [f"allowed_values_check on {list(allowed_values.keys())}"]


def check_range(df, contract: DataContract):
    """Flag rows with numeric values outside the contract's min/max range."""
    from pyspark.sql import functions as F

    range_checks = contract.validations.get("range_checks", [])
    if not range_checks:
        return df, df.limit(0), []

    condition = F.lit(False)
    checked_cols = []
    for rule in range_checks:
        col_name = rule["column"]
        checked_cols.append(col_name)
        if "min" in rule:
            condition = condition | (F.col(col_name) < rule["min"])
        if "max" in rule:
            condition = condition | (F.col(col_name) > rule["max"])

    bad = df.filter(condition)
    good = df.filter(~condition)
    return good, bad, [f"range_check on {checked_cols}"]
