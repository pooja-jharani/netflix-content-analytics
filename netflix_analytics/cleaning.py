"""Loading, cleaning and data-quality checks for the Netflix titles dataset.

Design rule: never invent data. Missing values are labelled "Unknown" or left
as NaN, not filled with the most common value (filling country with the mode,
for example, would inflate the United States count).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Age-rating buckets, ordered from youngest to oldest audience.
RATING_GROUPS = {
    "TV-Y": "Kids",
    "TV-Y7": "Kids",
    "TV-Y7-FV": "Kids",
    "TV-G": "Kids",
    "G": "Kids",
    "TV-PG": "Family & Teens",
    "PG": "Family & Teens",
    "PG-13": "Family & Teens",
    "TV-14": "Family & Teens",
    "TV-MA": "Adult",
    "R": "Adult",
    "NC-17": "Adult",
    "NR": "Unrated",
    "UR": "Unrated",
    "Not Rated": "Unrated",
}
RATING_GROUP_ORDER = ["Kids", "Family & Teens", "Adult", "Unrated"]

DATE_FORMAT = "%B %d, %Y"
UNKNOWN = "Unknown"


def _split(value: object, sep: str = ",") -> list[str]:
    """Split a comma separated cell into a clean list ([] when missing)."""
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read the raw CSV exactly as published."""
    return pd.read_csv(path)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return an analysis-ready copy of the raw titles table."""
    df = raw.copy()

    # Trim whitespace in every text column.
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype("string").str.strip()

    # A title can only appear once per (title, type, release year).
    df = df.drop_duplicates(subset=["title", "type", "release_year"]).reset_index(drop=True)

    df["date_added"] = pd.to_datetime(df["date_added"], format=DATE_FORMAT, errors="coerce")
    df["year_added"] = df["date_added"].dt.year.astype("Int64")
    df["month_added"] = df["date_added"].dt.month.astype("Int64")
    # Years between release and arrival on the platform (negative = added before release).
    df["years_to_add"] = df["year_added"] - df["release_year"]

    # Multi-value columns -> lists. Missing stays empty / "Unknown", never imputed.
    df["countries"] = df["country"].map(_split)
    df["primary_country"] = df["countries"].map(lambda c: c[0] if c else UNKNOWN)
    df["genres"] = df["listed_in"].map(_split)
    df["directors"] = df["director"].map(_split)
    df["is_us"] = df["primary_country"].eq("United States")

    df["rating"] = df["rating"].fillna("Not Rated")
    df["rating_group"] = df["rating"].map(RATING_GROUPS).fillna("Unrated")

    # Duration: minutes for movies, seasons for TV shows.
    parts = df["duration"].str.extract(r"(?P<n>\d+)\s*(?P<unit>min|Season)")
    number = pd.to_numeric(parts["n"])
    df["runtime_min"] = number.where(df["type"].eq("Movie"))
    df["seasons"] = number.where(df["type"].eq("TV Show"))

    return df


def data_quality_report(raw: pd.DataFrame) -> pd.DataFrame:
    """Missing-value table for the raw data (one row per column)."""
    report = pd.DataFrame(
        {
            "missing": raw.isna().sum(),
            "missing_pct": (raw.isna().mean() * 100).round(2),
        }
    )
    return report.sort_values("missing", ascending=False)


def quality_summary(raw: pd.DataFrame, df: pd.DataFrame) -> dict[str, int]:
    """Headline data-quality counts, used in the README and the dashboard."""
    return {
        "rows_raw": len(raw),
        "rows_clean": len(df),
        "duplicates_removed": len(raw) - len(df),
        "missing_country": int(raw["country"].isna().sum()),
        "missing_director": int(raw["director"].isna().sum()),
        "missing_cast": int(raw["cast"].isna().sum()),
        "missing_date_added": int(raw["date_added"].isna().sum()),
        "missing_rating": int(raw["rating"].isna().sum()),
        "added_before_release": int((df["years_to_add"] < 0).sum()),
        "unparsed_dates": int(df["date_added"].isna().sum() - raw["date_added"].isna().sum()),
    }
