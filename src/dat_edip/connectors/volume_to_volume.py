"""
Basic Volume-to-Volume connector.

Copies files from a source Databricks Volume path to a target (processing)
Volume path, using Spark's dbutils.fs (when running on Databricks) or plain
shutil (for local/offline learning runs without a cluster).
"""
from __future__ import annotations

import os
import shutil


def copy_volume_to_volume(source_path: str, target_path: str, dbutils=None) -> int:
    """
    Copy all files from source_path to target_path.

    Returns the number of files copied. If dbutils is provided (i.e. running
    inside a Databricks notebook), dbutils.fs.cp is used; otherwise falls
    back to local filesystem copy so this can be learned/tested off-platform.
    """
    if dbutils is not None:
        # Volumes do not materialize empty subdirectories. Create the landing
        # directory on first use so an empty input does not fail the job.
        dbutils.fs.mkdirs(source_path)
        source_entries = dbutils.fs.ls(source_path)
        if not source_entries:
            dbutils.fs.mkdirs(target_path)
            return 0
        dbutils.fs.mkdirs(target_path)
        dbutils.fs.cp(source_path, target_path, recurse=True)
        files = dbutils.fs.ls(target_path)
        return len(files)

    os.makedirs(target_path, exist_ok=True)
    copied = 0
    for entry in os.listdir(source_path):
        src_file = os.path.join(source_path, entry)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, os.path.join(target_path, entry))
            copied += 1
    return copied
