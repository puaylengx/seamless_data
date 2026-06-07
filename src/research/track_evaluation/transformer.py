import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.transformer import (  # re-export shared functions
    get_rank,
    get_parse_database_data,
    get_clean_publication_month,
    get_clean_publication_day,
    get_clean_publication_name_month,
    get_clean_year,
    get_format_effective_date,
)

import pandas as pd


def build_track_template(df_data: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame()
    df["Product Code"] = df_data["Product Code"]
    df["RC Meeting"] = df_data["RC Meeting"]
    df["Publication_month"] = get_clean_publication_name_month(df_data)
    df["orderNum"] = get_clean_publication_month(df_data)
    df["Publication_year"] = get_clean_year(df_data)
    df["PublicationDate"] = get_format_effective_date(df_data)
    df["Firstname"] = df_data["Firstname"]
    df["Lastname"] = df_data["Lastname"]
    df["Rank"] = get_rank(df_data)
    df["Division"] = df_data["Division"]
    df["Description"] = df_data["Description"]
    df["Weight"] = df_data["Weight"]
    df["Quality"] = df_data["Quality"]
    df["Corresponding"] = df_data["Corresponding"]
    df["Contribution"] = df_data["Contribution"]
    df["SCORE"] = df_data["SCORE"]
    df["REWARD"] = df_data["REWARD"]
    df["Title"] = df_data["Title"]
    df["Source"] = df_data["Journal/Conference/Source"]
    return df
