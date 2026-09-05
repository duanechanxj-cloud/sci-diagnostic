from pathlib import Path
import pandas as pd

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def ensure_parent(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def read_csv_flexible(path_or_buffer):
    return pd.read_csv(path_or_buffer, dtype=str).fillna("")

def write_csv_utf8(df, path):
    path = ensure_parent(path)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path
