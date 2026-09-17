"""ทดสอบ src/research/reconcile — summary / fetch / compare (G4) — ไม่ต่อ DB, ใช้ fake executor"""
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.research.reconcile import (
    Summary,
    compare,
    compare_destinations,
    fetch_summary_sql,
    summarize,
)

KEYS = ["product_code", "title"]


def _df(rows):
    return pd.DataFrame(rows, columns=["product_code", "title", "publication_year"])


# ── summarize ─────────────────────────────────────────────────────────────────

def test_summarize_rows_per_year_and_distinct_keys():
    df = _df([
        ("P1", "a", 2024), ("P1", "a", 2024),   # ซ้ำ key เดียวกัน
        ("P2", "b", 2024), ("P3", "c", 2025),
    ])
    s = summarize(df, "publication_year", KEYS, "prepared")
    assert s.rows == 4
    assert s.per_year == {2024: 3, 2025: 1}
    assert s.distinct_per_year == {2024: 2, 2025: 1}
    assert s.years == [2024, 2025]
    print("✅ summarize: rows/ปี + distinct key/ปี")


def test_summarize_null_year_counted_in_rows_but_not_per_year():
    df = _df([("P1", "a", 2024), ("P2", "b", None), ("P3", "c", "2025")])
    s = summarize(df, "publication_year", KEYS, "x")
    assert s.rows == 3 and s.per_year == {2024: 1, 2025: 1}


def test_summarize_ignores_key_cols_missing_from_df():
    df = _df([("P1", "a", 2024)])
    s = summarize(df, "publication_year", ["product_code", "nope"], "x")
    assert s.distinct_per_year == {2024: 1}


# ── fetch_summary_sql ─────────────────────────────────────────────────────────

def test_fetch_summary_sql_builds_year_filtered_queries_and_parses_rows():
    seen = []

    def execute(sql):
        seen.append(sql)
        if "DISTINCT" in sql:
            return [(2024, 2), (2025, 1)]
        return [(2024, 3), (2025, 1)]

    s = fetch_summary_sql(execute, "[dbo].[publications]", "publication_year", KEYS, [2024, 2025], "MSSQL")
    assert s.label == "MSSQL" and s.rows == 4
    assert s.per_year == {2024: 3, 2025: 1} and s.distinct_per_year == {2024: 2, 2025: 1}
    assert len(seen) == 2
    assert "WHERE publication_year IN (2024, 2025)" in seen[0]
    assert "[dbo].[publications]" in seen[0]
    assert "SELECT DISTINCT publication_year AS y, product_code, title" in seen[1]
    print("✅ fetch_summary_sql: 2 query กรองปี, parse ผลได้")


def test_fetch_summary_sql_no_years_does_not_query():
    called = []
    s = fetch_summary_sql(lambda sql: called.append(sql) or [], "t", "y", KEYS, [], "x")
    assert called == [] and s.rows == 0


# ── compare ───────────────────────────────────────────────────────────────────

def _sum(label, per_year, distinct=None):
    return Summary(label, sum(per_year.values()), per_year, distinct or per_year)


def test_compare_ok_when_identical(caplog):
    e, a = _sum("prepared", {2024: 3}), _sum("MSSQL", {2024: 3})
    with caplog.at_level(logging.INFO, logger="src.research.reconcile"):
        r = compare(e, a)
    assert r.ok and r.issues == []
    assert "ตรงกัน" in caplog.text


def test_compare_detects_missing_rows():
    r = compare(_sum("prepared", {2024: 3}), _sum("BQ", {2024: 1}))
    assert not r.ok and any("หาย 2" in i for i in r.issues)


def test_compare_detects_real_duplicates_from_destination_itself(caplog):
    # MSSQL append รันซ้ำ → ปลายทาง 6 แถว แต่ distinct key 3 → ซ้ำ 3 แถว (ไม่ต้องอาศัยขนาด batch)
    e = _sum("prepared", {2024: 3}, {2024: 3})
    a = _sum("MSSQL", {2024: 6}, {2024: 3})
    with caplog.at_level(logging.WARNING, logger="src.research.reconcile"):
        r = compare(e, a)
    assert not r.ok
    assert any("ซ้ำ 3 แถว" in i for i in r.issues)
    print("✅ compare: จับแถวซ้ำจาก rows > distinct ของปลายทางเอง")


def test_compare_incremental_uploads_same_year_do_not_warn(caplog):
    # ทยอย upload ชุดที่ 2 ของปี 2024 (batch 2 แถว) ปลายทางสะสม 5 แถว 5 key → ไม่ใช่ปัญหา
    e = _sum("prepared", {2024: 2}, {2024: 2})
    a = _sum("MSSQL", {2024: 5}, {2024: 5})
    with caplog.at_level(logging.INFO, logger="src.research.reconcile"):
        r = compare(e, a)
    assert r.ok
    assert "สะสมจาก upload ก่อนหน้า" in caplog.text
    assert "⚠️" not in caplog.text
    print("✅ compare: append เพิ่มปีเดียวกันโดยตั้งใจ → INFO ไม่ WARNING")


def test_compare_detects_fewer_distinct_keys_than_batch():
    # ปลายทาง 3 แถวแต่ key ไม่ซ้ำแค่ 2 → ทั้ง "distinct น้อยกว่า batch" และ "ซ้ำ 1 แถว"
    r = compare(_sum("prepared", {2024: 3}, {2024: 3}), _sum("BQ", {2024: 3}, {2024: 2}))
    assert not r.ok
    assert any("distinct key ปลายทาง 2 น้อยกว่า" in i for i in r.issues)
    assert any("ซ้ำ 1 แถว" in i for i in r.issues)


def test_compare_missing_year_in_destination():
    r = compare(_sum("prepared", {2024: 1, 2025: 1}), _sum("BQ", {2024: 1}))
    assert not r.ok and any("ปี 2025" in i for i in r.issues)


# ── compare_destinations ──────────────────────────────────────────────────────

def test_compare_destinations_ok_and_mismatch():
    a = _sum("MSSQL", {2024: 3, 2025: 1})
    assert compare_destinations(a, _sum("BigQuery", {2024: 3, 2025: 1})).ok
    r = compare_destinations(a, _sum("BigQuery", {2024: 3, 2025: 2, 2026: 1}))
    assert not r.ok
    assert any("ปี 2025" in i for i in r.issues) and any("ปี 2026" in i for i in r.issues)
    print("✅ compare_destinations: MSSQL ⇄ BQ")
