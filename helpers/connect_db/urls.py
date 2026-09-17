"""
SQLAlchemy connection URL จาก .env — ประกอบด้วย sqlalchemy.URL.create() ไม่ใช่ f-string (G16)

ทำไม: f-string + quote() ทำให้ password โผล่เป็น plain text ใน traceback / repr(engine) / log
และ escape ผิดได้ถ้ามี @ : / % ในรหัสผ่าน — URL.create() เก็บ password เป็น field แยก,
str(url) / repr(engine) แสดง *** เสมอ, และ driver ได้ค่าถูกต้องไม่ว่ารหัสผ่านมีอักขระอะไร

ใช้ร่วมกันทั้ง 3 โหมดของโปรเจกต์:
  - mssql_url()               → research (publication / track_evaluation)
  - postgres_url(mode="ssh")  → ผ่าน SSH tunnel: host 127.0.0.1 + local_bind_port ของ tunnel
  - postgres_url(mode="direct") → DB_HOST/DB_PORT ตรง
(helpers/connect_db/connection.py ที่ใช้ psycopg2.connect(**kwargs) ไม่มี URL string อยู่แล้ว จึงไม่กระทบ)
"""
from __future__ import annotations

import os

from sqlalchemy import URL


def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v and v.strip() else default


def _int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v and v.strip() else default


def mssql_url(
    *,
    driver: str = "ODBC Driver 17 for SQL Server",
    database_env: str = "RESEARCH_DATABASE",
) -> URL:
    """MSSQL research DB: LOCAL_HOST / LOCAL_USERNAME / LOCAL_PASSWORD / RESEARCH_DATABASE"""
    return URL.create(
        "mssql+pyodbc",
        username=_env("LOCAL_USERNAME"),
        password=_env("LOCAL_PASSWORD"),
        host=_env("LOCAL_HOST"),
        database=_env(database_env),
        query={"driver": driver},
    )


def postgres_url(database: str, *, mode: str | None = None, local_port: int | None = None) -> URL:
    """
    PostgreSQL ผ่าน SQLAlchemy (ใช้โดย loader ที่ใช้ pandas.to_sql เช่น zeal_data)

    mode "ssh"   : host=127.0.0.1, port=local_port (local_bind_port ของ SSHTunnelForwarder) — ต้องส่ง local_port
    mode "direct": host=DB_HOST, port=DB_PORT
    mode None    : อ่านจาก DB_CONNECTION_MODE (default "ssh")
    """
    mode = (mode or _env("DB_CONNECTION_MODE", "ssh") or "ssh").lower()
    if mode == "ssh":
        if local_port is None:
            raise ValueError("postgres_url(mode='ssh') ต้องส่ง local_port ของ SSH tunnel")
        host, port = "127.0.0.1", int(local_port)
    elif mode == "direct":
        host, port = _env("DB_HOST", "localhost"), _int("DB_PORT", 5432)
    else:
        raise ValueError(f"DB_CONNECTION_MODE ต้องเป็น 'ssh' หรือ 'direct' ได้รับ: '{mode}'")
    return URL.create(
        "postgresql+psycopg2",
        username=_env("DB_USERNAME"),
        password=_env("DB_PASSWORD"),
        host=host,
        port=port,
        database=database,
    )
