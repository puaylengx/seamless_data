"""
PostgreSQL connection — รองรับทั้ง SSH tunnel และ direct
"""
import os
import warnings
from contextlib import contextmanager

import psycopg2
import sshtunnel
from colorama import Fore, Style
from cryptography.utils import CryptographyDeprecationWarning
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
load_dotenv(override=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _str(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v and v.strip() else default


def _int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v and v.strip() else default


# ── public API ────────────────────────────────────────────────────────────────

def connect_to_db(database_name: str = None):
    """
    เชื่อมต่อ PostgreSQL แบบ SSH tunnel หรือ direct ตาม DB_CONNECTION_MODE

    Returns:
        (conn, tunnel) — tunnel เป็น None เมื่อใช้ direct
    """
    db_name = database_name or _str("DB_NAME", "ic_finance")
    mode = (_str("DB_CONNECTION_MODE", "ssh") or "ssh").lower()

    tunnel = None
    conn = None

    try:
        if mode == "ssh":
            conn, tunnel = _connect_ssh(db_name)
        else:
            conn = _connect_direct(db_name)

        print(f"{Fore.GREEN}[{mode.upper()}] Connected to '{db_name}' successfully!{Style.RESET_ALL}")
        return conn, tunnel

    except Exception as e:
        print(f"{Fore.RED}Connection error ({mode}): {e}{Style.RESET_ALL}")
        _safe_close(conn, tunnel)
        raise


def close_connection(conn=None, tunnel=None):
    """ปิด connection และ SSH tunnel อย่างปลอดภัย"""
    _safe_close(conn, tunnel)
    print(f"{Fore.YELLOW}Connection closed{Style.RESET_ALL}")


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

def _connect_ssh(db_name: str):
    tunnel_kwargs = dict(
        ssh_address_or_host=(_str("SSH_HOST", "192.168.64.2"), _int("SSH_PORT", 22)),
        ssh_username=_str("SSH_USERNAME"),
        remote_bind_address=(_str("DB_HOST", "localhost"), _int("DB_PORT", 5432)),
        local_bind_address=("127.0.0.1", 0),
    )

    pkey = _str("SSH_PKEY")
    if pkey:
        tunnel_kwargs["ssh_pkey"] = pkey
        tunnel_kwargs["ssh_private_key_password"] = _str("SSH_PKEY_PASSWORD")
    else:
        tunnel_kwargs["ssh_password"] = _str("SSH_PASSWORD")

    tunnel = sshtunnel.SSHTunnelForwarder(**tunnel_kwargs)
    tunnel.start()

    conn = psycopg2.connect(
        database=db_name,
        user=_str("DB_USERNAME"),
        password=_str("DB_PASSWORD"),
        host="127.0.0.1",
        port=tunnel.local_bind_port,
        connect_timeout=_int("DB_CONNECT_TIMEOUT", 10),
        application_name=_str("DB_APP_NAME", "python-client"),
        keepalives=1,
        keepalives_idle=_int("DB_KEEPALIVES_IDLE", 30),
        keepalives_interval=_int("DB_KEEPALIVES_INTERVAL", 10),
        keepalives_count=_int("DB_KEEPALIVES_COUNT", 5),
    )
    return conn, tunnel


def _connect_direct(db_name: str):
    conn = psycopg2.connect(
        database=db_name,
        user=_str("DB_USERNAME"),
        password=_str("DB_PASSWORD"),
        host=_str("DB_HOST", "localhost"),
        port=_int("DB_PORT", 5432),
        connect_timeout=_int("DB_CONNECT_TIMEOUT", 10),
        application_name=_str("DB_APP_NAME", "python-client"),
        keepalives=1,
        keepalives_idle=_int("DB_KEEPALIVES_IDLE", 30),
        keepalives_interval=_int("DB_KEEPALIVES_INTERVAL", 10),
        keepalives_count=_int("DB_KEEPALIVES_COUNT", 5),
    )
    return conn


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
