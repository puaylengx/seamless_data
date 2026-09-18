"""
PostgreSQL connection — รองรับทั้ง SSH tunnel และ direct (psycopg2)

G17: ค่า config ทั้งหมดมาจาก .env ผ่าน helpers.connect_db.config.postgres_config() — ไม่มี fallback
เป็นที่อยู่ infra ในโค้ด; ขาดค่าไหน MissingConfigError บอกชื่อครบก่อนเปิด connection
"""
import logging
import warnings
from contextlib import contextmanager

import psycopg2
import sshtunnel
from cryptography.utils import CryptographyDeprecationWarning
from dotenv import load_dotenv

from helpers.connect_db.config import postgres_config

warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
load_dotenv(override=True)

logger = logging.getLogger(__name__)


# ── public API ────────────────────────────────────────────────────────────────

def connect_to_db(database_name: str = None):
    """
    เชื่อมต่อ PostgreSQL แบบ SSH tunnel หรือ direct ตาม DB_CONNECTION_MODE

    Returns:
        (conn, tunnel) — tunnel เป็น None เมื่อใช้ direct
    Raises:
        MissingConfigError ก่อนแตะ network ถ้า .env ไม่ครบ
    """
    cfg = postgres_config(database_name)
    tunnel = None
    conn = None
    try:
        if cfg["mode"] == "ssh":
            conn, tunnel = _connect_ssh(cfg)
        else:
            conn = _connect_direct(cfg)
        logger.info("[%s] Connected to '%s' successfully", cfg["mode"].upper(), cfg["database"])
        return conn, tunnel
    except Exception as e:
        logger.error("Connection error (%s): %s", cfg["mode"], e)
        _safe_close(conn, tunnel)
        raise


def close_connection(conn=None, tunnel=None):
    """ปิด connection และ SSH tunnel อย่างปลอดภัย"""
    _safe_close(conn, tunnel)
    logger.info("Connection closed")


@contextmanager
def db_session(database_name: str = None):
    """Context manager — commit อัตโนมัติ, rollback เมื่อเกิด exception"""
    conn, tunnel = connect_to_db(database_name)
    try:
        yield conn, tunnel
        conn.commit()
    except Exception:
        if conn and not conn.closed:
            conn.rollback()
        raise
    finally:
        _safe_close(conn, tunnel)


# ── internal ──────────────────────────────────────────────────────────────────

def _psycopg2_kwargs(cfg: dict, host: str, port: int) -> dict:
    return dict(
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        host=host,
        port=port,
        connect_timeout=cfg["connect_timeout"],
        application_name=cfg["application_name"],
        keepalives=1,
        keepalives_idle=cfg["keepalives_idle"],
        keepalives_interval=cfg["keepalives_interval"],
        keepalives_count=cfg["keepalives_count"],
    )


def _connect_ssh(cfg: dict):
    tunnel_kwargs = dict(
        ssh_address_or_host=(cfg["ssh_host"], cfg["ssh_port"]),
        ssh_username=cfg["ssh_username"],
        remote_bind_address=(cfg["host"], cfg["port"]),
        local_bind_address=("127.0.0.1", 0),
    )
    if cfg["ssh_pkey"]:
        tunnel_kwargs["ssh_pkey"] = cfg["ssh_pkey"]
        tunnel_kwargs["ssh_private_key_password"] = cfg["ssh_pkey_password"]
    else:
        tunnel_kwargs["ssh_password"] = cfg["ssh_password"]

    tunnel = sshtunnel.SSHTunnelForwarder(**tunnel_kwargs)
    tunnel.start()
    conn = psycopg2.connect(**_psycopg2_kwargs(cfg, "127.0.0.1", tunnel.local_bind_port))
    return conn, tunnel


def _connect_direct(cfg: dict):
    return psycopg2.connect(**_psycopg2_kwargs(cfg, cfg["host"], cfg["port"]))


def _safe_close(conn=None, tunnel=None):
    if conn:
        try:
            conn.close()
        except Exception:
            pass
    if tunnel:
        try:
            tunnel.stop()
        except Exception:
            pass
