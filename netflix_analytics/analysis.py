"""Analysis functions. Each takes the cleaned frame and returns a small table.

Every function works on a filtered frame too, so the dashboard and the
notebook share exactly the same logic.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from .cleaning import RATING_GROUP_ORDER, UNKNOWN


def last_complete_year(df: pd.DataFrame) -> int:
    """Last calendar year that is fully covered by the `date_added` column."""
    latest = df["date_added"].max()
    return int(latest.year if (latest.month, latest.day) == (12, 31) else latest.year - 1)


def _cutoff(df: pd.DataFrame, last_year: int | None) -> int:
    """Use an explicit cut-off year (e.g. from the unfiltered data) or derive it."""
    return last_year if last_year is not None else last_complete_year(df)


def titles_added_per_year(df: pd.DataFrame, last_year: int | None = None) -> pd.DataFrame:
    """Titles added per year, split by type (partial final year excluded)."""
    sub = df[df["year_added"].notna() & (df["year_added"] <= _cutoff(df, last_year))]
    out = sub.groupby(["year_added", "type"]).size().unstack(fill_value=0)
    out.index = out.index.astype(int)
    out.columns.name = None
    return out


def country_counts(df: pd.DataFrame, top_n: int = 10) -> pd.Series:
    """Titles per primary country, excluding titles with no country listed."""
    known = df[df["primary_country"] != UNKNOWN]
    return known["primary_country"].value_counts().head(top_n)


def international_share_by_year(df: pd.DataFrame, min_titles: int = 50, last_year: int | None = None) -> pd.DataFrame:
    """Share of titles (with a known country) whose primary country is not the US."""
    known = df[(df["primary_country"] != UNKNOWN) & df["year_added"].notna()]
    known = known[known["year_added"] <= _cutoff(df, last_year)]
    by_year = known.groupby("year_added").agg(titles=("is_us", "size"), us=("is_us", "sum"))
    by_year = by_year[by_year["titles"] >= min_titles]
    by_year["non_us_share"] = 1 - by_year["us"] / by_year["titles"]
    by_year.index = by_year.index.astype(int)
    return by_year[["titles", "non_us_share"]]


def freshness_by_year(df: pd.DataFrame, min_titles: int = 50, last_year: int | None = None) -> pd.DataFrame:
    """How recent is content when it arrives? Share released within 1 year of being added."""
    sub = df[df["years_to_add"].notna() & (df["year_added"] <= _cutoff(df, last_year))].copy()
    sub["is_new"] = sub["years_to_add"] <= 1
    out = sub.groupby("year_added").agg(
        titles=("is_new", "size"),
        new_share=("is_new", "mean"),
        median_age=("years_to_add", "median"),
    )
    out = out[out["titles"] >= min_titles]
    out.index = out.index.astype(int)
    return out


def rating_mix_by_year(df: pd.DataFrame, min_titles: int = 50, last_year: int | None = None) -> pd.DataFrame:
    """Share of each age-rating group among titles added each year."""
    sub = df[df["year_added"].notna() & (df["year_added"] <= _cutoff(df, last_year))]
    counts = sub.groupby(["year_added", "rating_group"]).size().unstack(fill_value=0)
    counts = counts[counts.sum(axis=1) >= min_titles]
    shares = counts.div(counts.sum(axis=1), axis=0)
    shares = shares.reindex(columns=[c for c in RATING_GROUP_ORDER if c in shares.columns])
    shares.index = shares.index.astype(int)
    return shares


def genre_counts(df: pd.DataFrame, top_n: int = 10) -> pd.Series:
    """Number of titles carrying each genre tag (a title can have several)."""
    return df["genres"].explode().dropna().value_counts().head(top_n)


# These tags describe where a title is from, not what it is about, so they are
# left out of genre comparisons between countries.
GEOGRAPHY_TAGS = {
    "International Movies",
    "International TV Shows",
    "British TV Shows",
    "Korean TV Shows",
    "Spanish-Language TV Shows",
}


def country_genre_lift(
    df: pd.DataFrame, top_countries: int = 8, top_genres: int = 12
) -> pd.DataFrame:
    """Specialisation index: how much more (or less) a country leans on a genre.

    lift = share of the country's titles with the genre / share of all titles
    with the genre. 1.0 = in line with the catalogue, 2.0 = twice as likely.
    """
    known = df[df["primary_country"] != UNKNOWN]
    countries = known["primary_country"].value_counts().head(top_countries).index
    all_genres = known["genres"].explode().value_counts()
    genres = all_genres[~all_genres.index.isin(GEOGRAPHY_TAGS)].head(top_genres).index

    exploded = known[["primary_country", "genres"]].explode("genres").reset_index(drop=True)
    exploded = exploded[exploded["genres"].isin(genres)]
    per_country = pd.crosstab(exploded["primary_country"], exploded["genres"])
    country_totals = known["primary_country"].value_counts()
    country_share = per_country.div(country_totals.reindex(per_country.index), axis=0)

    overall = exploded["genres"].value_counts() / len(known)
    lift = country_share.div(overall.reindex(country_share.columns), axis=1)
    return lift.reindex(index=countries, columns=genres).fillna(0.0)


def signature_genre(df: pd.DataFrame, country: str, min_titles: int = 30) -> dict[str, float | str]:
    """The genre a country over-indexes on most (genres with fewer than `min_titles` ignored)."""
    known = df[df["primary_country"] != UNKNOWN]
    mine = known[known["primary_country"] == country]
    overall = known["genres"].explode().value_counts()
    own = mine["genres"].explode().value_counts()
    own = own[(own >= min_titles) & ~own.index.isin(GEOGRAPHY_TAGS)]
    share_own = own / len(mine)
    share_all = overall.reindex(own.index) / len(known)
    lift = (share_own / share_all).sort_values(ascending=False)
    genre = lift.index[0]
    return {
        "genre": genre,
        "lift": float(lift.iloc[0]),
        "country_share": float(share_own[genre]),
        "overall_share": float(share_all[genre]),
    }


def runtime_by_release_year(
    df: pd.DataFrame, start: int = 2000, min_titles: int = 30, last_year: int | None = None
) -> pd.DataFrame:
    """Median movie runtime by release year."""
    movies = df[df["runtime_min"].notna() & df["release_year"].between(start, _cutoff(df, last_year))]
    out = movies.groupby("release_year")["runtime_min"].agg(median="median", titles="size")
    return out[out["titles"] >= min_titles]


def seasons_by_release_period(df: pd.DataFrame) -> pd.DataFrame:
    """Share of one-season shows and average seasons, by release period."""
    tv = df[df["seasons"].notna()].copy()
    bins = [1899, 2010, 2015, 2018, 2030]
    labels = ["2010 or earlier", "2011-2015", "2016-2018", "2019-2021"]
    tv["period"] = pd.cut(tv["release_year"], bins=bins, labels=labels)
    return tv.groupby("period", observed=True).agg(
        shows=("seasons", "size"),
        one_season_share=("seasons", lambda s: (s == 1).mean()),
        avg_seasons=("seasons", "mean"),
    )


def top_directors(df: pd.DataFrame, top_n: int = 10) -> pd.Series:
    """Directors with the most titles."""
    return df["directors"].explode().dropna().value_counts().head(top_n)


def director_concentration(df: pd.DataFrame) -> dict[str, float]:
    """How concentrated is directing talent? (long-tail check)"""
    credits = df["directors"].explode().dropna()
    counts = credits.value_counts()
    return {
        "unique_directors": int(len(counts)),
        "titles_with_director": int(df["directors"].map(bool).sum()),
        "top_10_share_of_credits": float(counts.head(10).sum() / counts.sum()),
        "directors_with_one_title_share": float((counts == 1).mean()),
    }


def monthly_additions(df: pd.DataFrame, first_year: int = 2017, last_year: int | None = None) -> pd.Series:
    """Average titles added per calendar month across complete years."""
    last = _cutoff(df, last_year)
    sub = df[df["year_added"].between(first_year, last)]
    per_month = sub.groupby("month_added").size() / (last - first_year + 1)
    per_month.index = per_month.index.astype(int)
    return per_month


# ---- simple statistical checks -------------------------------------------------

def non_us_shift_test(df: pd.DataFrame, early=(2013, 2015), late=(2017, 2019)) -> dict[str, float]:
    """Chi-square test: did the non-US share of additions change between two periods?"""
    known = df[(df["primary_country"] != UNKNOWN) & df["year_added"].notna()]
    a = known[known["year_added"].between(*early)]
    b = known[known["year_added"].between(*late)]
    table = [
        [int((~a["is_us"]).sum()), int(a["is_us"].sum())],
        [int((~b["is_us"]).sum()), int(b["is_us"].sum())],
    ]
    p_value = stats.chi2_contingency(table)[1]
    return {
        "early_share": table[0][0] / sum(table[0]),
        "late_share": table[1][0] / sum(table[1]),
        "p_value": float(p_value),
    }


def runtime_trend_test(df: pd.DataFrame, start: int = 2000) -> dict[str, float]:
    """Spearman correlation between movie release year and runtime."""
    movies = df[df["runtime_min"].notna() & df["release_year"].between(start, last_complete_year(df))]
    rho, p_value = stats.spearmanr(movies["release_year"], movies["runtime_min"])
    return {"rho": float(rho), "p_value": float(p_value), "movies": int(len(movies))}


def headline_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Numbers used in the README, report and dashboard KPI row."""
    known = df[df["primary_country"] != UNKNOWN]
    movies = df[df["type"] == "Movie"]
    return {
        "titles": len(df),
        "movie_share": float((df["type"] == "Movie").mean()),
        "us_share_known": float(known["is_us"].mean()) if len(known) else float("nan"),
        "median_runtime": float(movies["runtime_min"].median()) if len(movies) else float("nan"),
        "countries": int(known["primary_country"].nunique()),
        "genres": int(df["genres"].explode().nunique()),
    }
