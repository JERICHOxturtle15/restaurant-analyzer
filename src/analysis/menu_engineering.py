import pandas as pd
import numpy as np
from config.settings import (
    POPULARITY_THRESHOLD_PERCENTILE,
    CATEGORY_STAR, CATEGORY_PLOW_HORSE, CATEGORY_PUZZLE, CATEGORY_DOG,
)


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["profit_margin"] = (df["price"] - df["cost"]) / df["price"]
    df["gross_profit"] = df["price"] - df["cost"]
    df["monthly_revenue"] = df["price"] * df["monthly_orders"]
    df["monthly_profit"] = df["gross_profit"] * df["monthly_orders"]
    return df


def classify_boston_matrix(df: pd.DataFrame) -> pd.DataFrame:
    df = compute_metrics(df)

    pop_threshold = np.percentile(df["monthly_orders"], POPULARITY_THRESHOLD_PERCENTILE)
    margin_threshold = df["profit_margin"].median()

    def _classify(row):
        high_pop = row["monthly_orders"] >= pop_threshold
        high_margin = row["profit_margin"] >= margin_threshold
        if high_pop and high_margin:
            return CATEGORY_STAR
        if high_pop and not high_margin:
            return CATEGORY_PLOW_HORSE
        if not high_pop and high_margin:
            return CATEGORY_PUZZLE
        return CATEGORY_DOG

    df["matrix_category"] = df.apply(_classify, axis=1)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("matrix_category")
        .agg(
            dish_count=("dish_name", "count"),
            avg_margin=("profit_margin", "mean"),
            avg_orders=("monthly_orders", "mean"),
            total_monthly_profit=("monthly_profit", "sum"),
        )
        .round(3)
        .reset_index()
    )
    return summary
