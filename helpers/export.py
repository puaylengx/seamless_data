from pathlib import Path

import pandas as pd


def export_excel(df: pd.DataFrame, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)
    return f"Exported excel successfully: {path}"
