import re
import calendar
import numpy as np
import pandas as pd

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
    # Fix: use cleaned month values (handles "2023-10" format) instead of raw Month column
    year_clean = pd.to_numeric(get_clean_year(df_data), errors="coerce")
    month = get_clean_publication_month(df_data)
    year_budget = np.where(month >= 10, year_clean + 1, year_clean)
    return pd.Series(year_budget, index=df_data.index).astype("Int64")


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
