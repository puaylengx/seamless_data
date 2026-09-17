"""ทดสอบ main.reconcile() ของ publication — orchestration ของ G4 โดย mock summary fetchers (ไม่ต่อ DB)"""
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

import src.research.publication.main as main_mod
from src.research.publication.loader import _REQUIRED_COLS, _STR_COLS
from src.research.reconcile import Summary


def _df(years):
    rows = []
    for i, y in enumerate(years):
        d = {c: 0 for c in _REQUIRED_COLS}
        d.update({c: "x" for c in _STR_COLS})
        d.update({"product_code": f"P{i}", "title": f"T{i}", "publication_month": 1,
                  "publication_year": y, "publication_calendar_year": y,
                  "publication_budget_year": y, "effective_date": f"{y}-01-31"})
        rows.append(d)
    return pd.DataFrame(rows)


def _fake(label, per_year):
    def fetch(years):
        fetch.years = years
        return Summary(label, sum(per_year.values()), per_year, per_year)
    return fetch


def test_reconcile_ok_when_both_destinations_match(monkeypatch, caplog):
    df = _df([2024, 2024, 2025])
    m = _fake("MSSQL", {2024: 2, 2025: 1})
    b = _fake("BigQuery", {2024: 2, 2025: 1})
    monkeypatch.setattr(main_mod, "mssql_summary", m)
    monkeypatch.setattr(main_mod, "bq_summary", b)
    with caplog.at_level(logging.INFO, logger="src.research.reconcile"):
        assert main_mod.reconcile(df, mssql=True, bq=True) is True
    assert m.years == [2024, 2025]          # ถามปลายทางเฉพาะปีที่เขียน
    assert "MSSQL ⇄ BigQuery" in caplog.text
    print("✅ reconcile: ทั้งสองปลายทางตรง + เทียบกันเอง")


def test_reconcile_flags_mssql_duplicates_but_does_not_raise(monkeypatch, caplog):
    df = _df([2024, 2024])
    monkeypatch.setattr(main_mod, "mssql_summary", _fake("MSSQL", {2024: 4}))   # append รันซ้ำ
    with caplog.at_level(logging.WARNING, logger="src.research.reconcile"):
        assert main_mod.reconcile(df, mssql=True, bq=False) is False
    assert "ซ้ำ" in caplog.text


def test_reconcile_only_queries_enabled_destinations(monkeypatch):
    df = _df([2024])
    calls = []
    monkeypatch.setattr(main_mod, "mssql_summary", lambda years: calls.append("mssql") or Summary("MSSQL", 1, {2024: 1}, {2024: 1}))
    monkeypatch.setattr(main_mod, "bq_summary", lambda years: calls.append("bq") or Summary("BigQuery", 1, {2024: 1}, {2024: 1}))
    assert main_mod.reconcile(df, mssql=False, bq=True) is True
    assert calls == ["bq"]


def test_reconcile_survives_fetch_failure_and_reports_not_ok(monkeypatch, caplog):
    df = _df([2024])

    def boom(years):
        raise ConnectionError("no route to host")
    monkeypatch.setattr(main_mod, "bq_summary", boom)
    with caplog.at_level(logging.ERROR, logger="src.research.publication.main"):
        assert main_mod.reconcile(df, mssql=False, bq=True) is False
    assert "อ่านสรุปจาก BigQuery ไม่สำเร็จ" in caplog.text
    print("✅ reconcile: ปลายทางถามไม่ได้ → log error, ไม่ล้ม, คืน False")
