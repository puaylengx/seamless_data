import logging
import os
import re
from contextlib import contextmanager
from urllib.parse import quote

import pandas as pd
import sshtunnel
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(override=True)
logger = logging.getLogger(__name__)


def _str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v.strip() if v and v.strip() else default


def _int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v and v.strip() else default


def _sanitize_name(name: str) -> str:
    """แปลงชื่อตารางให้เป็น snake_case ที่ PostgreSQL รองรับ"""
    sanitized = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")
    if sanitized and sanitized[0].isdigit():
        sanitized = "t_" + sanitized
    return sanitized or "unnamed"


@contextmanager
def _engine_session(db_name: str):
    """Context manager สร้าง SQLAlchemy engine รองรับ SSH tunnel และ direct"""
    mode = _str("DB_CONNECTION_MODE", "ssh").lower()
    tunnel = None
    engine = None
    try:
        if mode == "ssh":
            tunnel_kwargs = dict(
                ssh_address_or_host=(_str("SSH_HOST"), _int("SSH_PORT", 22)),
                ssh_username=_str("SSH_USERNAME"),
                remote_bind_address=(_str("DB_HOST", "localhost"), _int("DB_PORT", 5432)),
                local_bind_address=("127.0.0.1", 0),
            )
            pkey = _str("SSH_PKEY")
            if pkey:
                tunnel_kwargs["ssh_pkey"] = pkey
                pkey_pass = _str("SSH_PKEY_PASSWORD")
                if pkey_pass:
                    tunnel_kwargs["ssh_private_key_password"] = pkey_pass
            else:
                tunnel_kwargs["ssh_password"] = _str("SSH_PASSWORD")

            tunnel = sshtunnel.SSHTunnelForwarder(**tunnel_kwargs)
            tunnel.start()
            host, port = "127.0.0.1", tunnel.local_bind_port
        else:
            host = _str("DB_HOST", "localhost")
            port = _int("DB_PORT", 5432)

        url = (
            f"postgresql+psycopg2://{_str('DB_USERNAME')}:{quote(_str('DB_PASSWORD'))}"
            f"@{host}:{port}/{db_name}"
        )
        engine = create_engine(url, future=True)
        logger.info("[%s] Connected to PostgreSQL '%s'", mode.upper(), db_name)
        yield engine

    finally:
        if engine:
            engine.dispose()
        if tunnel:
            tunnel.stop()


def load_all(tables: dict[str, pd.DataFrame], db_name: str | None = None) -> None:
    """
    Insert ทุกตารางใน dict เข้า PostgreSQL
    ใช้ env vars: ZEAL_DB_NAME, ZEAL_SCHEMA, ZEAL_INSERT_MODE
    """
    db_name = db_name or _str("ZEAL_DB_NAME")
    if not db_name:
        raise ValueError("ระบุ ZEAL_DB_NAME ใน .env หรือส่ง db_name argument")

    schema = _str("ZEAL_SCHEMA", "public") or "public"
    insert_mode = _str("ZEAL_INSERT_MODE", "replace") or "replace"

    if insert_mode not in ("replace", "append"):
        raise ValueError(f"ZEAL_INSERT_MODE ต้องเป็น 'replace' หรือ 'append' ได้รับ: '{insert_mode}'")

    with _engine_session(db_name) as engine:
        for original_name, df in tables.items():
            table_name = _sanitize_name(original_name)
            df.to_sql(
                name=table_name,
                con=engine,
                schema=schema,
                if_exists=insert_mode,
                index=False,
                chunksize=1000,
            )
            logger.info(
                "✅ %s.%s ← '%s' %d แถว (mode=%s)",
                schema, table_name, original_name, len(df), insert_mode,
            )
