"""BigQuery (research) — client + ชื่อตาราง ตัวเดียวสำหรับ publication และ track_evaluation (G17)"""
from __future__ import annotations

import os

from helpers.connect_db.config import bigquery_config, bigquery_dataset, env


def bigquery_client():
    """google.cloud.bigquery.Client จาก .env — ตรวจว่าไฟล์ key มีจริง (expanduser) ก่อนสร้าง client"""
    from google.cloud import bigquery  # import ช้า/หนัก — โหลดเมื่อใช้จริงเท่านั้น

    cfg = bigquery_config()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cfg["key_path"]
    return bigquery.Client(project=cfg["project_id"])


def bigquery_tables(staging_env: str, staging_default: str, prod_env: str, prod_default: str) -> tuple[str, str]:
    """(staging_fqn, prod_fqn) = project.dataset.table — ชื่อตารางจาก env ที่ระบุ มี default ต่อ pipeline"""
    cfg = bigquery_dataset()          # ชื่อตารางไม่ต้องมี key file (reconcile/test ใช้ client ที่ inject มาได้)
    prefix = f"{cfg['project_id']}.{cfg['dataset_id']}"
    return f"{prefix}.{env(staging_env, staging_default)}", f"{prefix}.{env(prod_env, prod_default)}"
