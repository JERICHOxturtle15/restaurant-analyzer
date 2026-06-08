import pandas as pd
from pathlib import Path
from typing import Optional


def load_csv(filepath: str | Path) -> pd.DataFrame:
    return pd.read_csv(filepath, encoding="utf-8-sig")


def load_excel(filepath: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    return pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")


def validate_schema(df: pd.DataFrame, required_columns: list[str]) -> bool:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必要列: {missing}")
    return True


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Drop fully empty rows
    df.dropna(how="all", inplace=True)

    # Strip whitespace from string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Coerce numeric columns, fill missing with column median
    numeric_cols = ["price", "cost", "monthly_orders", "rating"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    # Remove rows where price or cost is zero / negative
    if "price" in df.columns:
        df = df[df["price"] > 0]
    if "cost" in df.columns:
        df = df[df["cost"] > 0]

    df.reset_index(drop=True, inplace=True)
    return df
