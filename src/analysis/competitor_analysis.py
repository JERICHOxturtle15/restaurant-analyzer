import pandas as pd
import numpy as np


def compare_pricing(my_menu_df: pd.DataFrame, competitor_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare average price per category between my menu and competitors.

    Returns a DataFrame with columns:
      category | my_avg_price | <RestaurantA> | <RestaurantB> | ... | competitor_avg | price_gap | gap_pct
    """
    my_avg = (
        my_menu_df.groupby("category")["price"]
        .mean()
        .reset_index()
        .rename(columns={"price": "my_avg_price"})
    )

    comp_avg = (
        competitor_df.groupby(["restaurant_name", "category"])["price"]
        .mean()
        .reset_index()
    )
    comp_pivot = comp_avg.pivot(index="category", columns="restaurant_name", values="price").reset_index()
    comp_pivot.columns.name = None

    result = my_avg.merge(comp_pivot, on="category", how="outer")

    restaurant_cols = [c for c in result.columns if c not in ("category", "my_avg_price")]
    result["competitor_avg"] = result[restaurant_cols].mean(axis=1)
    result["price_gap"] = result["my_avg_price"] - result["competitor_avg"]
    result["gap_pct"] = (result["price_gap"] / result["competitor_avg"] * 100).round(1)

    return result.round(2).fillna("-")


def score_positioning(competitor_df: pd.DataFrame) -> dict:
    """
    Summarize each competitor's average price, rating, and order volume.

    Returns:
      {
        "by_restaurant": [{"restaurant_name": ..., "avg_price": ..., ...}],
        "market_avg_price": float,
        "market_avg_rating": float,
        "market_total_orders": int,
      }
    """
    by_restaurant = (
        competitor_df.groupby("restaurant_name")
        .agg(
            avg_price=("price", "mean"),
            avg_rating=("rating", "mean"),
            total_monthly_orders=("monthly_orders", "sum"),
            dish_count=("dish_name", "count"),
        )
        .round(2)
        .reset_index()
        .to_dict("records")
    )

    return {
        "by_restaurant": by_restaurant,
        "market_avg_price": round(float(competitor_df["price"].mean()), 2),
        "market_avg_rating": round(float(competitor_df["rating"].mean()), 2),
        "market_total_orders": int(competitor_df["monthly_orders"].sum()),
    }


def run_competitor_analysis(
    my_menu_df: pd.DataFrame,
    competitor_df: pd.DataFrame,
    output_path,
) -> tuple[pd.DataFrame, dict]:
    """Full competitor analysis pipeline. Saves pricing report CSV."""
    df_pricing = compare_pricing(my_menu_df, competitor_df)
    positioning = score_positioning(competitor_df)

    import pathlib
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_pricing.to_csv(output_path, index=False, encoding="utf-8-sig")

    return df_pricing, positioning
