import logging
import re
import calendar
import numpy as np
import pandas as pd

from helpers.fiscal import fiscal_year

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2  # header row 1, data starts at row 2

_VALID_RANKS = [
    "Lecturer", "Assoc.Prof.", "Support Staff", "Asst.Prof.",
    "Prof.", "Asst.Lect.", "Academic Advisor",
]

_FLAG_COLUMNS = [
    "WoS_with_JIF-P90", "WoS_with_JIF",
    "WoS_SC", "WoS_SS", "WoS_AH", "WoS_ES",
    "Scopus_SJR-10", "Scopus_Q1", "Scopus_Q2", "Scopus_Q3", "Scopus_Q4", "Scopus_No_Q",
    "SENSE_ABC", "ERIC", "MathSciNet", "Pubmed", "JSTOR", "Project_Muse",
    "Other_Inter.Databases", "TCI_Group1", "TCI_Group2", "National_Journal",
]

_DB_INDICATORS = (
    "WoS", "Scopus", "TCI", "ERIC", "MathSciNet",
    "Pubmed", "JSTOR", "Project_Muse", "Other_Inter.Databases", "National",
)

_DB_INT_COLUMNS = [
    "WoS_with_JIF-P90", "WoS_with_JIF", "WoS_SC", "WoS_SS", "WoS_AH", "WoS_ES",
    "Scopus_SJR-10", "Scopus_Q1", "Scopus_Q2", "Scopus_Q3", "Scopus_Q4", "Scopus_No_Q",
    "ERIC", "MathSciNet", "Pubmed", "JSTOR", "Project_Muse", "Other_Inter.Databases",
]

_SPECIAL_INTERNATIONAL = {
    "Being used as public policy",
    "Featured role International venue",
    "Group/International",
}

_CLASSIFICATION_COL = 'Other Classification ("A"-Excellent, International-Very Good, National-Good)'


def get_rank(df_data: pd.DataFrame) -> pd.Series:
    def _check(row):
        rank = str(row["Rank"]).strip()
        if rank not in _VALID_RANKS:
            if rank in ("Asst.Prof", "Asst. Prof."):
                return "Asst.Prof."
            if rank in ("Assoc.Prof", "Assoc. Prof."):
                return "Assoc.Prof."
        return rank

    return df_data.apply(_check, axis=1)


def get_group_rank(df_data: pd.DataFrame) -> pd.Series:
    def _map(row):
        rank = str(row["Rank"]).strip()
        if rank in ("Academic Advisor", "Support Staff"):
            return rank
        return "Lecturer"

    return df_data.apply(_map, axis=1)


def _parse_database_entry(db_str: str) -> dict:
    result = {col: 0 for col in _FLAG_COLUMNS}
    result["Field"] = ""

    if pd.isnull(db_str):
        return result

    if "Field:" in db_str:
        field_start = db_str.find("Field:")
        before_field = db_str[:field_start].rstrip(", ")
        field_sub = db_str[field_start + len("Field:"):].strip()

        tokens = [t.strip() for t in field_sub.split(",")]
        field_tokens, remainder_tokens = [], []
        for token in tokens:
            if any(token.startswith(ind) for ind in _DB_INDICATORS):
                remainder_tokens.append(token)
            else:
                if not remainder_tokens:
                    field_tokens.append(token)
                else:
                    remainder_tokens.append(token)

        result["Field"] = ", ".join(field_tokens)
        db_str = before_field + (", " + ", ".join(remainder_tokens) if remainder_tokens else "")

    for part in db_str.split(","):
        part = part.strip()

        if "WoS" in part:
            if "(SC)" in part:
                result["WoS_SC"] = 1
            if "(SS)" in part:
                result["WoS_SS"] = 1
            if "(AH)" in part:
                result["WoS_AH"] = 1
            if "(ES)" in part:
                result["WoS_ES"] = 1
            m = re.search(r"JIF-?P?([\d\.]+)", part)
            if m:
                try:
                    jif = float(m.group(1))
                    result["WoS_with_JIF"] = 1
                    if jif >= 90:
                        result["WoS_with_JIF-P90"] = 1
                except ValueError:
                    pass

        if "Scopus" in part:
            if "SJR-10" in part:
                result["Scopus_SJR-10"] = 1
            if "SJR-Q1" in part:
                result["Scopus_Q1"] = 1
            if "SJR-Q2" in part:
                result["Scopus_Q2"] = 1
            if "SJR-Q3" in part:
                result["Scopus_Q3"] = 1
            if "SJR-Q4" in part:
                result["Scopus_Q4"] = 1
            if "No_Q" in part:
                result["Scopus_No_Q"] = 1

        if "Scimago" in part:
            m2 = re.search(r"Scimago\s*?(\d+)\s*/\s*(\d+)", part)
            if m2:
                rank_val = int(m2.group(1))
                total = int(m2.group(2))
                if rank_val <= total * 0.1:
                    result["Scopus_SJR-10"] = 1

        # case-insensitive, handles both "Group1" and "Group 1"
        if "tci" in part.lower():
            p = part.lower().replace(" ", "")
            if "group1" in p:
                result["TCI_Group1"] = 1
            if "group2" in p:
                result["TCI_Group2"] = 1

        if "SENSE" in part:
            result["SENSE_ABC"] = 1
        if "ERIC" in part:
            result["ERIC"] = 1
        if "MathSciNet" in part:
            result["MathSciNet"] = 1
        if "Pubmed" in part:
            result["Pubmed"] = 1
        if "JSTOR" in part:
            result["JSTOR"] = 1
        if "ProjectMuse" in part:
            result["Project_Muse"] = 1
        if "Other_Inter.Databases" in part:
            result["Other_Inter.Databases"] = 1
        if "National" in part and "Journal" in part:
            result["National_Journal"] = 1

    return result


def get_parse_database_data(df_data: pd.DataFrame) -> pd.DataFrame:
    new_columns = _FLAG_COLUMNS + ["Field"]
    parsed = df_data["Database (WoS, Scopus, TCI)"].apply(_parse_database_entry)
    parsed_df = pd.DataFrame(parsed.tolist(), index=df_data.index)
    df_clean = df_data.drop(columns=new_columns, errors="ignore")
    return pd.concat([df_clean, parsed_df], axis=1)


def get_clean_publication_month(df_data: pd.DataFrame) -> pd.Series:
    effective_dates = df_data["Online Date"].combine_first(df_data["Publication Date"])

    def _extract(val, fallback):
        if pd.notna(val) and str(val).strip():
            s = str(val)
            if "-" in s:
                try:
                    return int(s.split("-")[1])
                except (ValueError, IndexError):
                    pass
            try:
                return int(s)
            except ValueError:
                pass
        try:
            return pd.to_datetime(fallback).month
        except Exception:
            return np.nan

    return df_data.apply(
        lambda row: _extract(row["Month"], effective_dates.loc[row.name]),
        axis=1,
    )


def get_clean_publication_day(df_data: pd.DataFrame) -> pd.Series:
    effective_dates = df_data["Online Date"].combine_first(df_data["Publication Date"])

    def _extract_day(val):
        try:
            return pd.to_datetime(val).day
        except Exception:
            return np.nan

    return effective_dates.apply(_extract_day)


def get_clean_publication_name_month(df_data: pd.DataFrame) -> pd.Series:
    effective_dates = df_data["Online Date"].combine_first(df_data["Publication Date"])

    def _extract_name(val, fallback):
        if pd.notna(val) and str(val).strip():
            s = str(val)
            if "-" in s:
                try:
                    return calendar.month_name[int(s.split("-")[1])]
                except (ValueError, IndexError):
                    return np.nan
            try:
                return calendar.month_name[int(s)]
            except (ValueError, IndexError):
                return np.nan
        try:
            dt = pd.to_datetime(fallback, errors="coerce")
            if pd.isna(dt):
                return np.nan
            return dt.strftime("%B")
        except Exception:
            return np.nan

    return df_data.apply(
        lambda row: _extract_name(row["Month"], effective_dates.loc[row.name]),
        axis=1,
    )


def get_clean_year(df_data: pd.DataFrame) -> pd.Series:
    cleaned = df_data["Year"].astype(str).str.replace(r"\D", "", regex=True).replace("", pd.NA)
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def get_clean_budget_year(df_data: pd.DataFrame) -> pd.Series:
    """ปีงบของผลงาน — นิยามเดียวกับ finance ผ่าน helpers/fiscal.py (ใช้ month ที่ clean แล้ว รองรับ "2023-10")"""
    year_clean = get_clean_year(df_data)
    month = get_clean_publication_month(df_data)
    return fiscal_year(year_clean, month)


def get_format_effective_date(df_data: pd.DataFrame) -> pd.Series:
    def _format(val):
        if isinstance(val, str):
            m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", val.strip())
            if m:
                month_name = m.group(1).lower()
                year = int(m.group(2))
                month_map = {n.lower(): i for i, n in enumerate(calendar.month_name) if n}
                abbr_map = {n.lower(): i for i, n in enumerate(calendar.month_abbr) if n}
                month_num = month_map.get(month_name) or abbr_map.get(month_name)
                if not month_num:
                    return val
                last_day = calendar.monthrange(year, month_num)[1]
                return f"{year:04d}-{month_num:02d}-{last_day:02d}"
        try:
            return pd.to_datetime(val).strftime("%Y-%m-%d")
        except Exception:
            return val

    effective_dates = df_data["Online Date"].combine_first(df_data["Publication Date"])
    return effective_dates.apply(_format)


def get_national_international(df_data: pd.DataFrame) -> pd.Series:
    classification = df_data[_CLASSIFICATION_COL]
    database_data = get_parse_database_data(df_data)

    results = []
    for idx, cls in classification.items():
        if cls in _SPECIAL_INTERNATIONAL:
            results.append("International")
        elif pd.isna(cls):
            row_db = database_data.loc[idx, _DB_INT_COLUMNS]
            results.append("International" if (row_db == 1).any() else "National")
        else:
            results.append(cls)

    return pd.Series(results, index=df_data.index)


def get_extract_sdg_values(db_str) -> dict:
    sdg_cols = [f"sdg{i}" for i in range(1, 18)]
    result = {col: 0 for col in sdg_cols}

    if pd.isnull(db_str):
        return result

    if not isinstance(db_str, str):
        db_str = str(db_str)

    for part in db_str.split(","):
        part = part.strip()
        main_val = part.split(".")[0] if "." in part else part
        try:
            n = int(main_val)
        except ValueError:
            continue
        if 1 <= n <= 17:
            result[f"sdg{n}"] = 1

    return result


# ── template assembly (ย้ายมาจาก main.py — G11) ─────────────────────────────

_DB_KEYS = _FLAG_COLUMNS + ["Field"]

# ลำดับ column ของ draft template ที่ส่งให้ฝ่ายวิจัย review (ชื่อ snake_case ตาม DB ยกเว้น column ต้นทางที่คงไว้ให้ดู)
TEMPLATE_COLUMN_ORDER = [
    "rank", "group_rank", "description",
    "Database (WoS, Scopus, TCI)",
    "wos_with_jif_p90", "wos_with_jif", "wos_sc", "wos_ss", "wos_ah", "wos_es",
    "scopus_sjr_10", "scopus_q1", "scopus_q2", "scopus_q3", "scopus_q4", "scopus_no_q",
    "sense_abc", "eric", "math_sci_net", "pubmed", "jstor", "project_muse",
    "other_inter", "tci_group1", "tci_group2", "national_journal", "field",
    "division", "product_code", "firstname", "lastname", "title", "source",
    "volume", "issue", "pages",
    "publication_month", "publication_year", "publication_calendar_year",
    "publication_budget_year", "effective_date", "national_international",
] + [f"sdg{i}" for i in range(1, 18)]


def _process_database(raw_data: pd.DataFrame) -> pd.DataFrame:
    parsed_db = get_parse_database_data(raw_data.copy())
    df = pd.DataFrame()
    df["Database (WoS, Scopus, TCI)"] = raw_data["Database (WoS, Scopus, TCI)"]
    for k in _DB_KEYS:
        df[k] = parsed_db.get(k, None)
    return df


def _process_clean(raw_data: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame()
    df["rank"] = get_rank(raw_data)
    df["group_rank"] = get_group_rank(raw_data)
    df["publication_month"] = get_clean_publication_month(raw_data)
    df["publication_year"] = get_clean_year(raw_data)
    df["publication_calendar_year"] = get_clean_year(raw_data)
    df["publication_budget_year"] = get_clean_budget_year(raw_data)
    df["effective_date"] = get_format_effective_date(raw_data)
    df["national_international"] = get_national_international(raw_data)

    sdg_df = raw_data["SDGs Goal"].apply(
        lambda x: pd.Series(get_extract_sdg_values(x) if pd.notna(x) else {})
    )
    return pd.concat([df, sdg_df], axis=1)


def build_publication_template(raw_data: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    """
    ไฟล์ต้นทาง (extractor.read_raw) → draft template ให้ฝ่ายวิจัย review (behavior เดิมของ main.run_template)
    rename_map = loader._RENAME_MAP (ชื่อ flag เดิม → snake_case) — ส่งเข้ามาเพื่อไม่ให้ transformer import loader
    """
    db_data = _process_database(raw_data)
    clean_data = _process_clean(raw_data)

    template = pd.DataFrame({
        "description": raw_data["Description"],
        "division": raw_data["Division"],
        "product_code": raw_data["Product Code"],
        "firstname": raw_data["Firstname"],
        "lastname": raw_data["Lastname"],
        "title": raw_data["Title"],
        "source": raw_data["Journal/Conference/Source"],
        "volume": raw_data["Volume"] if "Volume" in raw_data.columns else None,
        "issue": raw_data["Issue"] if "Issue" in raw_data.columns else None,
        "pages": raw_data["Pages"] if "Pages" in raw_data.columns else None,
    })

    df_combined = pd.concat(
        [template.reset_index(drop=True), db_data.reset_index(drop=True), clean_data.reset_index(drop=True)],
        axis=1,
    ).rename(columns=rename_map)

    for col in TEMPLATE_COLUMN_ORDER:
        if col not in df_combined.columns:
            df_combined[col] = None
    return df_combined[TEMPLATE_COLUMN_ORDER]


# ── reviewed template → DB-ready (G11: mutation ย้ายมาจาก validator) ─────────

def coerce_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    template ที่ review แล้ว (ชื่อ column snake_case) → DataFrame ที่ validator ตรวจแบบ read-only ได้

    เดิม validate_publication ทำ 2 อย่างนี้ **ใน validator** (mutate df ที่รับเข้ามา):
      1. publication_month ที่ว่าง/นอก 1–12 → เติมจากเดือนของ effective_date (ถ้า parse ได้)
      2. effective_date ถูก coerce เป็น datetime *เฉพาะเมื่อ* มี month ผิด (side effect ไม่สม่ำเสมอ)
    ตอนนี้ (1) อยู่ที่นี่และทำทุกครั้ง; (2) ไม่ทำ — effective_date คงค่าเดิม (loader._prepare_df แปลงเป็น date เองอยู่แล้ว)
    คืน DataFrame ใหม่ ไม่แก้ตัวที่รับเข้ามา
    """
    df = df.copy()
    if "publication_month" in df.columns and "effective_date" in df.columns:
        month = pd.to_numeric(df["publication_month"], errors="coerce")
        bad = month.isna() | ~month.between(1, 12)
        if bad.any():
            eff = pd.to_datetime(df["effective_date"], errors="coerce")
            fillable = bad & eff.notna()
            rows = (df.index[bad] + _EXCEL_ROW_OFFSET).tolist()
            logger.info(
                "publication_month ไม่อยู่ใน 1–12 ที่ Excel rows: %s → เติมจาก effective_date ได้ %d/%d แถว",
                rows, int(fillable.sum()), int(bad.sum()),
            )
            month = month.astype("Float64")
            month[fillable] = eff[fillable].dt.month
            df["publication_month"] = month
    return df
