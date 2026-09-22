"""
Basic Stage Manager.

Reads from the Raw table, runs the validation suite described in the
contract, writes clean rows to the Stage table and rejected rows to the
quarantine table.
"""
from __future__ import annotations

from dat_edip.contract_loader import DataContract
from dat_edip import validations as v


def load_stage(spark, contract: DataContract):
    """
    Orchestrate: read raw -> trim -> not-null check -> primary key check ->
    data type check -> allowed values -> range check -> write good rows to
    stage, bad rows to quarantine. Returns (good_count, bad_count, notes).
    """
    raw_table = _full_table_name(contract.target["raw"])
    df = spark.table(raw_table)

    notes = []
    quarantined_frames = []

    if contract.validations.get("trim_columns", True):
        df, trim_notes = v.apply_trim(df, contract)
        notes.extend(trim_notes)

    if contract.validations.get("not_null_check", True):
        df, bad, msg = v.check_not_null(df, contract)
        quarantined_frames.append(bad)
        notes.extend(msg)

    if contract.validations.get("primary_key_check", True):
        df, bad, msg = v.check_primary_key(df, contract)
        quarantined_frames.append(bad)
        notes.extend(msg)

    if contract.validations.get("data_type_check", True):
        df, bad, msg = v.check_data_types(df, contract)
        quarantined_frames.append(bad)
        notes.extend(msg)

    df, bad, msg = v.check_allowed_values(df, contract)
    quarantined_frames.append(bad)
    notes.extend(msg)

    df, bad, msg = v.check_range(df, contract)
    quarantined_frames.append(bad)
    notes.extend(msg)

    good_df = df
    stage_table = _full_table_name(contract.target["stage"])
    good_df.write.mode("append").format("delta").saveAsTable(stage_table)

    quarantine_table = _full_table_name(contract.target["quarantine"])
    bad_df = _union_all(quarantined_frames)
    if bad_df is not None:
        bad_df.write.mode("append").format("delta").saveAsTable(quarantine_table)

    good_count = good_df.count()
    bad_count = bad_df.count() if bad_df is not None else 0
    return good_count, bad_count, notes


def _union_all(frames):
    frames = [f for f in frames if f is not None]
    if not frames:
        return None
    result = frames[0]
    for f in frames[1:]:
        result = result.unionByName(f, allowMissingColumns=True)
    return result.dropDuplicates()


def _full_table_name(table_cfg: dict) -> str:
    return f"{table_cfg['catalog']}.{table_cfg['schema']}.{table_cfg['table']}"
