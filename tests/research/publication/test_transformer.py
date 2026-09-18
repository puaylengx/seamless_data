"""ทดสอบ transformation ของ publication — parse database/SDG, rank, ปี/เดือน, effective_date (G1)

ทุกฟังก์ชันเป็น pure pandas ไม่ต่อ DB — ใช้ synthetic data เท่านั้น
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.transformer import (
    TEMPLATE_COLUMN_ORDER,
    _CLASSIFICATION_COL,
    _parse_database_entry,
    build_publication_template,
    coerce_and_clean,
    get_clean_budget_year,
    get_clean_publication_month,
    get_clean_year,
    get_extract_sdg_values,
    get_format_effective_date,
    get_group_rank,
    get_national_international,
    get_parse_database_data,
    get_rank,
)

DB_COL = "Database (WoS, Scopus, TCI)"


def _on(result: dict) -> dict:
    """คืนเฉพาะ flag ที่เป็น 1 (+ Field) เพื่อให้ assertion อ่านง่าย"""
    return {k: v for k, v in result.items() if v not in (0, "")}


# ── _parse_database_entry ─────────────────────────────────────────────────────

def test_parse_wos_scopus_tci_with_field():
    r = _parse_database_entry("Scopus SJR-Q1, WoS (SC) JIF-P95, TCI Group 1, Field: Physics, Chemistry")
    assert _on(r) == {
        "WoS_with_JIF-P90": 1, "WoS_with_JIF": 1, "WoS_SC": 1,
        "Scopus_Q1": 1, "TCI_Group1": 1, "Field": "Physics, Chemistry",
    }
    print("✅ parse WoS/Scopus/TCI + Field หลาย token")


def test_parse_jif_below_p90_sets_only_with_jif():
    r = _parse_database_entry("WoS (SS) JIF-P60")
    assert r["WoS_with_JIF"] == 1 and r["WoS_with_JIF-P90"] == 0 and r["WoS_SS"] == 1


def test_parse_scimago_top10_percent_and_national_journal():
    r = _parse_database_entry("Scopus SJR-Q3, Scimago 12/200, National Journal")
    assert _on(r) == {"Scopus_SJR-10": 1, "Scopus_Q3": 1, "National_Journal": 1}


def test_parse_scimago_outside_top10_not_flagged():
    r = _parse_database_entry("Scopus SJR-Q2, Scimago 50/200")
    assert r["Scopus_SJR-10"] == 0 and r["Scopus_Q2"] == 1


def test_parse_tci_group_spacing_and_case_insensitive():
    assert _parse_database_entry("tci group2")["TCI_Group2"] == 1
    assert _parse_database_entry("TCI Group 1")["TCI_Group1"] == 1


def test_parse_other_databases():
    r = _parse_database_entry("ERIC, MathSciNet, Pubmed, JSTOR, ProjectMuse, SENSE A, Other_Inter.Databases")
    assert _on(r) == {
        "ERIC": 1, "MathSciNet": 1, "Pubmed": 1, "JSTOR": 1,
        "Project_Muse": 1, "SENSE_ABC": 1, "Other_Inter.Databases": 1,
    }


def test_parse_null_gives_all_zero_and_empty_field():
    r = _parse_database_entry(None)
    assert r["Field"] == "" and sum(v for k, v in r.items() if k != "Field") == 0
    print("✅ null → ทุก flag 0")


def test_get_parse_database_data_appends_flag_columns_and_keeps_index():
    df = pd.DataFrame({DB_COL: ["Scopus SJR-Q1", None]}, index=[10, 20])
    out = get_parse_database_data(df)
    assert out.index.tolist() == [10, 20]
    assert out.loc[10, "Scopus_Q1"] == 1 and out.loc[20, "Scopus_Q1"] == 0
    assert "Field" in out.columns


# ── SDG ───────────────────────────────────────────────────────────────────────

def test_sdg_parses_ints_subgoals_and_ignores_out_of_range():
    r = get_extract_sdg_values("3, 7.2, 18, abc, 17")
    assert {k for k, v in r.items() if v} == {"sdg3", "sdg7", "sdg17"}
    print("✅ SDG: 7.2 → sdg7, 18/abc ข้าม")


def test_sdg_null_and_numeric_input():
    assert sum(get_extract_sdg_values(None).values()) == 0
    assert get_extract_sdg_values(4)["sdg4"] == 1        # Excel อาจส่งมาเป็นตัวเลข
    assert get_extract_sdg_values(4.0)["sdg4"] == 1      # "4.0".split(".")[0] → 4


# ── rank / group_rank ─────────────────────────────────────────────────────────

def test_rank_normalizes_known_variants_only():
    df = pd.DataFrame({"Rank": ["Asst.Prof", "Assoc. Prof.", " Prof. ", "Lecturer", "Dr."]})
    assert get_rank(df).tolist() == ["Asst.Prof.", "Assoc.Prof.", "Prof.", "Lecturer", "Dr."]
    print("✅ rank variants → canonical; ค่าที่ไม่รู้จักผ่านตามเดิม")


def test_group_rank_only_advisor_and_support_staff_kept():
    df = pd.DataFrame({"Rank": ["Academic Advisor", "Support Staff", "Prof.", "Asst.Prof."]})
    assert get_group_rank(df).tolist() == ["Academic Advisor", "Support Staff", "Lecturer", "Lecturer"]


# ── year / month / budget year ────────────────────────────────────────────────

def _dates(**cols) -> pd.DataFrame:
    base = {"Year": ["2024"], "Month": ["3"], "Online Date": [None], "Publication Date": [None]}
    base.update(cols)
    return pd.DataFrame(base)


def test_clean_year_handles_whitespace_and_null():
    df = _dates(Year=[" 2023 ", None, "2024"], Month=["1", "1", "1"],
                **{"Online Date": [None] * 3, "Publication Date": [None] * 3})
    out = get_clean_year(df)
    assert str(out.dtype) == "Int64"
    assert out.isna().tolist() == [False, True, False]
    assert out.dropna().tolist() == [2023, 2024]


def test_clean_publication_month_formats_and_fallback_to_date():
    df = _dates(Year=["2024"] * 3, Month=["2023-10", "5", None],
                **{"Online Date": [None, None, "2024-03-15"], "Publication Date": [None] * 3})
    assert get_clean_publication_month(df).tolist() == [10, 5, 3]
    print("✅ month: 'YYYY-MM' → MM, '5' → 5, ว่าง → เดือนจาก Online Date")


def test_clean_publication_month_uses_publication_date_when_online_missing():
    df = _dates(Month=[None], **{"Online Date": [None], "Publication Date": ["2024-11-02"]})
    assert get_clean_publication_month(df).tolist() == [11]


def test_budget_year_rolls_over_from_october():
    # ปีงบเริ่ม ต.ค. → เดือน 10–12 นับเป็นปีงบถัดไป (นิยามเดียวกับ finance add_fiscal_month)
    df = _dates(Year=["2024"] * 3, Month=["9", "10", "2024-12"],
                **{"Online Date": [None] * 3, "Publication Date": [None] * 3})
    assert get_clean_budget_year(df).tolist() == [2024, 2025, 2025]
    print("✅ budget year: ก.ย. = ปีเดิม, ต.ค.–ธ.ค. = ปี+1")


def test_budget_year_na_when_year_missing():
    df = _dates(Year=[None], Month=["10"])
    assert get_clean_budget_year(df).isna().all()


# ── effective_date ────────────────────────────────────────────────────────────

def test_format_effective_date_month_name_becomes_month_end():
    df = _dates(**{"Online Date": ["March 2024", "Feb 2023"], "Publication Date": [None, None]}, Year=["x", "x"], Month=["1", "1"])
    assert get_format_effective_date(df).tolist() == ["2024-03-31", "2023-02-28"]
    print("✅ 'March 2024' → วันสิ้นเดือน")


def test_format_effective_date_prefers_online_date_then_publication_date():
    df = _dates(**{"Online Date": [None, "2024-01-05 00:00:00"], "Publication Date": ["2023-12-01", "2020-01-01"]}, Year=["x", "x"], Month=["1", "1"])
    assert get_format_effective_date(df).tolist() == ["2023-12-01", "2024-01-05"]


def test_format_effective_date_passes_garbage_through_for_validator():
    df = _dates(**{"Online Date": ["garbage"], "Publication Date": [None]})
    assert get_format_effective_date(df).tolist() == ["garbage"]


# ── national / international ──────────────────────────────────────────────────

def test_national_international_rules():
    df = pd.DataFrame({
        _CLASSIFICATION_COL: [None, None, "Being used as public policy", "National-Good"],
        DB_COL: ["Scopus SJR-Q1", "TCI Group 2", "TCI Group 1", "Scopus SJR-Q1"],
    })
    assert get_national_international(df).tolist() == ["International", "National", "International", "National-Good"]
    print("✅ classification ว่าง → ดูจาก DB flag; special → International; อื่นผ่านตามเดิม")


# ── coerce_and_clean (G11) ────────────────────────────────────────────────────

def test_coerce_fills_bad_month_from_effective_date_only_when_parseable():
    df = pd.DataFrame({
        "publication_month": [13, None, 5, 0],
        "effective_date": ["2024-03-31", "2023-11-02", "2024-01-01", "garbage"],
    })
    out = coerce_and_clean(df)
    assert out["publication_month"].tolist()[:3] == [3, 11, 5]
    assert out["publication_month"].iloc[3] == 0              # เดือนผิด + วันที่ parse ไม่ได้ → คงค่าเดิม ให้ validator จับ (เหมือนเดิม)
    assert out["effective_date"].tolist() == df["effective_date"].tolist()   # ไม่ coerce effective_date
    print("✅ coerce_and_clean: เติม month จาก effective_date เฉพาะที่ parse ได้")


def test_coerce_does_not_mutate_and_skips_when_columns_missing():
    df = pd.DataFrame({"publication_month": [13], "effective_date": ["2024-03-31"]})
    snap = df.copy(deep=True)
    coerce_and_clean(df)
    pd.testing.assert_frame_equal(df, snap)
    assert coerce_and_clean(pd.DataFrame({"title": ["t"]})).equals(pd.DataFrame({"title": ["t"]}))


# ── build_publication_template (G11: ย้ายจาก main) ───────────────────────────

def _raw_row(**o):
    d = {
        "Description": "Journal", "Division": "Science", "Product Code": "P-1", "Firstname": "A",
        "Lastname": "B", "Title": "T", "Journal/Conference/Source": "J", "Rank": "Asst.Prof",
        "Year": "2024", "Month": "2024-11", "Online Date": None, "Publication Date": "2024-11-15",
        DB_COL: "Scopus SJR-Q1, TCI Group 1, Field: Physics", "SDGs Goal": "3, 7",
        _CLASSIFICATION_COL: None, "Volume": "12", "Issue": None, "Pages": "1-10",
    }
    d.update(o)
    return pd.DataFrame([d])


def test_build_template_columns_and_values():
    from src.research.publication.loader import _RENAME_MAP
    out = build_publication_template(_raw_row(), rename_map=_RENAME_MAP)
    assert list(out.columns) == TEMPLATE_COLUMN_ORDER
    r = out.iloc[0]
    assert (r["rank"], r["group_rank"]) == ("Asst.Prof.", "Lecturer")
    assert (r["scopus_q1"], r["tci_group1"], r["field"]) == (1, 1, "Physics")
    assert (r["publication_month"], r["publication_year"], r["publication_budget_year"]) == (11, 2024, 2025)
    assert r["effective_date"] == "2024-11-15" and r["national_international"] == "International"
    assert (r["sdg3"], r["sdg7"], r["sdg1"]) == (1, 1, 0)
    assert (r["volume"], r["pages"]) == ("12", "1-10") and pd.isna(r["issue"])
    print("✅ build_publication_template: ลำดับ column + ค่าครบเหมือน main เดิม")


def test_build_template_optional_columns_absent_become_none():
    from src.research.publication.loader import _RENAME_MAP
    raw = _raw_row().drop(columns=["Volume", "Issue", "Pages"])
    out = build_publication_template(raw, rename_map=_RENAME_MAP)
    assert out["volume"].isna().all() and "pages" in out.columns


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\n🎉 ทุก test ผ่าน")
