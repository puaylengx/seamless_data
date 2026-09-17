"""
Reconciliation check ระหว่าง "สิ่งที่ pipeline เตรียมไว้เขียน" กับ "สิ่งที่อยู่ในปลายทางจริง" (G4)

ใช้ร่วมกันทั้ง publication และ track_evaluation:
  1. summarize()            — สรุป DataFrame ที่ prepare แล้ว: rows / rows ต่อปี / distinct key ต่อปี
  2. fetch_summary_sql()    — สรุปแบบเดียวกันจากปลายทาง (MSSQL หรือ BigQuery) ผ่าน executor ที่ loader ส่งมา
  3. compare()              — expected (prepared) vs actual (ปลายทาง)  → log WARNING เมื่อไม่ตรง
  4. compare_destinations() — MSSQL vs BigQuery ต่อกันเอง → ตรวจว่าสอง DB ยัง sync กัน

เจตนา: **ตรวจแล้วบอก** ไม่ใช่ตัดสิน — ปลายทางไหนเป็น source of truth ยังรอ PD-4
จึง log เป็น WARNING และคืน ReconcileResult ให้ผู้เรียกตัดสินเอง ไม่ raise
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

# executor: รับ SQL string → คืน rows (tuple) — loader เป็นคนผูกกับ connection จริง
SqlExecutor = Callable[[str], Iterable[Sequence]]


@dataclass(frozen=True)
class Summary:
    label: str
    rows: int
    per_year: dict[int, int]            # year → จำนวนแถว
    distinct_per_year: dict[int, int]   # year → จำนวน key ที่ไม่ซ้ำ (ตาม key_cols)

    @property
    def years(self) -> list[int]:
        return sorted(self.per_year)


@dataclass
class ReconcileResult:
    label: str
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


# ── 1. สรุปจาก DataFrame ─────────────────────────────────────────────────────

def summarize(df: pd.DataFrame, year_col: str, key_cols: Sequence[str], label: str) -> Summary:
    """สรุป DataFrame ที่ prepare แล้ว (ค่าที่กำลังจะเขียน) — แถวที่ปีเป็น null จะถูกนับรวมใน rows แต่ไม่อยู่ใน per_year"""
    years = pd.to_numeric(df[year_col], errors="coerce")
    valid = years.notna()
    per_year = years[valid].astype(int).value_counts().sort_index()
    keys = [c for c in key_cols if c in df.columns]
    distinct = (
        df.loc[valid, keys].assign(_y=years[valid].astype(int))
        .drop_duplicates()
        .groupby("_y").size()
    )
    return Summary(
        label=label,
        rows=int(len(df)),
        per_year={int(y): int(n) for y, n in per_year.items()},
        distinct_per_year={int(y): int(n) for y, n in distinct.items()},
    )


# ── 2. สรุปจากปลายทาง ────────────────────────────────────────────────────────

def _in_list(years: Sequence[int]) -> str:
    return ", ".join(str(int(y)) for y in years)


def fetch_summary_sql(
    execute: SqlExecutor,
    table_fqn: str,
    year_col: str,
    key_cols: Sequence[str],
    years: Sequence[int],
    label: str,
) -> Summary:
    """
    สรุปแถวในปลายทางเฉพาะปีที่ pipeline เขียน (years) — ใช้ SQL มาตรฐานที่รันได้ทั้ง MSSQL และ BigQuery
    table_fqn ต้อง quote มาแล้วตามปลายทาง (เช่น [dbo].[publications] หรือ `proj.ds.publications`)
    """
    if not years:
        return Summary(label, 0, {}, {})
    ys = _in_list(years)
    rows_sql = (
        f"SELECT {year_col} AS y, COUNT(*) AS n FROM {table_fqn} "
        f"WHERE {year_col} IN ({ys}) GROUP BY {year_col}"
    )
    key_list = ", ".join(key_cols)
    distinct_sql = (
        f"SELECT y, COUNT(*) AS d FROM ("
        f"SELECT DISTINCT {year_col} AS y, {key_list} FROM {table_fqn} WHERE {year_col} IN ({ys})"
        f") s GROUP BY y"
    )
    per_year = {int(y): int(n) for y, n in execute(rows_sql)}
    distinct = {int(y): int(d) for y, d in execute(distinct_sql)}
    return Summary(label=label, rows=sum(per_year.values()), per_year=per_year, distinct_per_year=distinct)


# ── 3–4. เปรียบเทียบ ─────────────────────────────────────────────────────────

def compare(expected: Summary, actual: Summary) -> ReconcileResult:
    """
    prepared (expected) vs ปลายทาง (actual) ทีละปี:
      actual < expected → แถวหาย
      actual > expected → มีมากกว่าที่เพิ่งเขียน (เช่น MSSQL append รันซ้ำ → แถวซ้ำ)
      distinct ต่างกัน  → key ชุดไม่ตรง
    """
    result = ReconcileResult(label=f"{expected.label} → {actual.label}")
    for y in expected.years:
        e, a = expected.per_year[y], actual.per_year.get(y, 0)
        if a < e:
            result.issues.append(f"ปี {y}: ปลายทางมี {a} แถว น้อยกว่าที่เขียน {e} (หาย {e - a})")
        elif a > e:
            result.issues.append(
                f"ปี {y}: ปลายทางมี {a} แถว มากกว่าที่เขียน {e} (เกิน {a - e} — เป็นไปได้ว่า append รันซ้ำ/แถวซ้ำ)"
            )
        ed, ad = expected.distinct_per_year.get(y, 0), actual.distinct_per_year.get(y, 0)
        if ed != ad:
            result.issues.append(f"ปี {y}: distinct key ปลายทาง {ad} ≠ ที่เขียน {ed}")
    _log(result, expected, actual)
    return result


def compare_destinations(a: Summary, b: Summary) -> ReconcileResult:
    """MSSQL vs BigQuery — ต้องมีจำนวนแถวและ distinct key เท่ากันทุกปี ไม่งั้นสอง DB ไม่ sync"""
    result = ReconcileResult(label=f"{a.label} ⇄ {b.label}")
    for y in sorted(set(a.per_year) | set(b.per_year)):
        na, nb = a.per_year.get(y, 0), b.per_year.get(y, 0)
        if na != nb:
            result.issues.append(f"ปี {y}: {a.label} {na} แถว ≠ {b.label} {nb} แถว")
        da, db_ = a.distinct_per_year.get(y, 0), b.distinct_per_year.get(y, 0)
        if da != db_:
            result.issues.append(f"ปี {y}: distinct key {a.label} {da} ≠ {b.label} {db_}")
    _log(result, a, b)
    return result


def _log(result: ReconcileResult, left: Summary, right: Summary) -> None:
    if result.ok:
        logger.info(
            "✅ reconcile %s ตรงกัน — %d ปี, %s rows=%d / %s rows=%d",
            result.label, len(left.years), left.label, left.rows, right.label, right.rows,
        )
        return
    logger.warning("⚠️ reconcile %s ไม่ตรง %d จุด:", result.label, len(result.issues))
    for issue in result.issues:
        logger.warning("   - %s", issue)
