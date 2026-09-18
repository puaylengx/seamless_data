"""
ตรวจค่า .env ที่จำเป็นก่อนเปิด connection ใดๆ (G17 — ไม่มี fallback เป็นที่อยู่ infra อีกต่อไป)

เดิม connection.py มี default ฝังในโค้ด (SSH_HOST=192.168.64.2, DB_NAME=ic_finance, DB_HOST=localhost)
→ เครื่องที่ลืม copy .env จะ "ต่อได้" ไปผิดที่โดยไม่รู้ตัว หรือ error จาก driver ที่อ่านไม่รู้เรื่อง
ตอนนี้: ขาดตัวไหน → MissingConfigError บอกชื่อ env var ทั้งหมดที่ขาดในครั้งเดียว + วิธีแก้
ค่าที่ยังมี default คือ protocol default เท่านั้น: SSH_PORT=22, DB_PORT=5432, DB_SCHEMA=public
"""
from __future__ import annotations

import os

ENV_EXAMPLE_HINT = "คัดลอก .env.example → .env แล้วกรอกค่า (ดู README.md หัวข้อ Setup)"


class MissingConfigError(RuntimeError):
    def __init__(self, missing: list[str], context: str):
        self.missing = missing
        super().__init__(
            f"{context}: ไม่ได้ตั้งค่า env var ที่จำเป็น {len(missing)} ตัว → {', '.join(missing)}\n"
            f"วิธีแก้: {ENV_EXAMPLE_HINT}"
        )


def env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v and v.strip() else default


def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v and v.strip() else default


def require(keys: list[str], context: str, any_of: list[str] | None = None) -> dict[str, str]:
    """
    คืน {key: value} ของ keys ที่ตั้งครบ; raise MissingConfigError รายชื่อที่ขาดทั้งหมดในครั้งเดียว
    any_of: อย่างน้อยหนึ่งตัวต้องมี (เช่น SSH_PKEY หรือ SSH_PASSWORD)
    """
    missing = [k for k in keys if env(k) is None]
    if any_of and not any(env(k) for k in any_of):
        missing.append(" หรือ ".join(any_of))
    if missing:
        raise MissingConfigError(missing, context)
    return {k: env(k) for k in keys}


def postgres_config(database_name: str | None = None) -> dict:
    """ค่าที่ connect_to_db ต้องใช้ ตาม DB_CONNECTION_MODE — ตรวจครบก่อนแตะ network"""
    mode = (env("DB_CONNECTION_MODE", "ssh") or "ssh").lower()
    if mode not in ("ssh", "direct"):
        raise MissingConfigError([f"DB_CONNECTION_MODE (ต้องเป็น ssh หรือ direct ได้รับ '{mode}')"], "PostgreSQL")
    base = ["DB_USERNAME", "DB_PASSWORD", "DB_HOST"] + ([] if database_name else ["DB_NAME"])
    if mode == "ssh":
        cfg = require(base + ["SSH_HOST", "SSH_USERNAME"], "PostgreSQL ผ่าน SSH tunnel", any_of=["SSH_PKEY", "SSH_PASSWORD"])
    else:
        cfg = require(base, "PostgreSQL direct")
    return {
        "mode": mode,
        "database": database_name or cfg["DB_NAME"],
        "user": cfg["DB_USERNAME"],
        "password": cfg["DB_PASSWORD"],
        "host": cfg["DB_HOST"],
        "port": env_int("DB_PORT", 5432),
        "ssh_host": cfg.get("SSH_HOST"),
        "ssh_port": env_int("SSH_PORT", 22),
        "ssh_username": cfg.get("SSH_USERNAME"),
        "ssh_pkey": env("SSH_PKEY"),
        "ssh_pkey_password": env("SSH_PKEY_PASSWORD"),
        "ssh_password": env("SSH_PASSWORD"),
        "connect_timeout": env_int("DB_CONNECT_TIMEOUT", 10),
        "application_name": env("DB_APP_NAME", "python-client"),
        "keepalives_idle": env_int("DB_KEEPALIVES_IDLE", 30),
        "keepalives_interval": env_int("DB_KEEPALIVES_INTERVAL", 10),
        "keepalives_count": env_int("DB_KEEPALIVES_COUNT", 5),
    }


def mssql_config() -> dict:
    cfg = require(["LOCAL_HOST", "LOCAL_USERNAME", "LOCAL_PASSWORD", "RESEARCH_DATABASE", "SCHEMA_DEFAULT"], "MSSQL research")
    return {**cfg, "driver": env("MSSQL_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")}


def bigquery_config() -> dict:
    cfg = require(["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT_ID", "GCP_DATASET_ID"], "BigQuery")
    key_path = os.path.expanduser(cfg["GOOGLE_APPLICATION_CREDENTIALS"])
    if not os.path.exists(key_path):
        raise MissingConfigError(
            [f"GOOGLE_APPLICATION_CREDENTIALS (ไฟล์ไม่พบ: {key_path})"],
            "BigQuery — key ต้องอยู่นอก repo เช่น ~/.config/seamless_data/",
        )
    return {"key_path": key_path, "project_id": cfg["GCP_PROJECT_ID"], "dataset_id": cfg["GCP_DATASET_ID"]}
