"""Static report figures (matplotlib). The dashboard uses Plotly with the same colours."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from . import analysis as A
from . import theme as T

plt.rcParams.update(
    {
        "figure.facecolor": T.SURFACE,
        "axes.facecolor": T.SURFACE,
        "savefig.facecolor": T.SURFACE,
        "axes.edgecolor": T.GRID,
        "axes.labelcolor": T.TEXT_2,
        "xtick.color": T.TEXT_2,
        "ytick.color": T.TEXT_2,
        "text.color": T.TEXT,
        "font.size": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": T.GRID,
        "grid.linewidth": 0.8,
        "figure.dpi": 110,
        "savefig.dpi": 150,
    }
)


def _title(ax, headline: str, sub: str | None = None) -> None:
    ax.set_title(headline, loc="left", fontsize=13, fontweight="bold", color=T.TEXT, pad=22 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=T.TEXT_2, va="bottom")


def _save(fig, out_dir: Path, name: str) -> Path:
    path = Path(out_dir) / name
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def growth_by_type(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.titles_added_per_year(df)
    data = data[data.index >= 2014]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for col, color in (("Movie", T.MOVIE), ("TV Show", T.TV)):
        ax.plot(data.index, data[col], color=color, lw=2, marker="o", ms=5, mec=T.SURFACE, mew=1.5, label=col)
        ax.annotate(f"{col}\n{int(data[col].iloc[-1]):,}", (data.index[-1], data[col].iloc[-1]),
                    xytext=(8, 0), textcoords="offset points", color=T.TEXT, fontsize=9.5, va="center")
    ax.set_xlim(data.index.min() - 0.2, data.index.max() + 1.3)
    ax.set_xticks(data.index)
    ax.set_ylabel("Titles added")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left")
    _title(ax, "Additions took off in 2016 and peaked in 2019",
           f"Titles added per year, by type (2021 excluded: data ends {df['date_added'].max():%d %b %Y})")
    return _save(fig, out_dir, "01_growth_by_type.png")


def international_share(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.international_share_by_year(df)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(data.index, data["non_us_share"] * 100, color=T.NEUTRAL, lw=2, marker="o", ms=6, mec=T.SURFACE, mew=1.5)
    for year, row in data.iterrows():
        ax.annotate(f"{row['non_us_share'] * 100:.0f}%", (year, row["non_us_share"] * 100),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9.5)
    ax.set_ylim(0, 85)
    ax.set_xticks(data.index)
    ax.set_ylabel("Non-US share of titles (%)")
    first, last = data.iloc[0], data.iloc[-1]
    _title(ax, f"Non-US content rose from {first['non_us_share']:.0%} to {last['non_us_share']:.0%} of additions "
               f"({data.index[0]} to {data.index[-1]})",
           "Share of titles added each year whose primary country is not the United States (known country only)")
    return _save(fig, out_dir, "02_international_share.png")


def top_countries(df: pd.DataFrame, out_dir: Path) -> Path:
    counts = A.country_counts(df, 10)[::-1]
    unknown = int((df["primary_country"] == "Unknown").sum())
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(counts.index, counts.values, color=T.NEUTRAL, height=0.62)
    for y, v in enumerate(counts.values):
        ax.text(v + counts.max() * 0.01, y, f"{v:,}", va="center", fontsize=9.5)
    ax.set_xlim(0, counts.max() * 1.12)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Titles")
    _title(ax, "The US leads, but India and the UK are clear numbers two and three",
           f"Titles by primary country; {unknown} titles with no country listed are excluded")
    return _save(fig, out_dir, "03_top_countries.png")


def freshness(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.freshness_by_year(df)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(data.index, data["new_share"] * 100, color=T.NEUTRAL, lw=2, marker="o", ms=6, mec=T.SURFACE, mew=1.5)
    for year, row in data.iterrows():
        ax.annotate(f"{row['new_share'] * 100:.0f}%", (year, row["new_share"] * 100),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9.5)
    ax.set_ylim(0, 100)
    ax.set_xticks(data.index)
    ax.set_ylabel("Added within 1 year of release (%)")
    since = data.loc[2018:, "new_share"].mean()
    _title(ax, f"Fewer additions are brand-new releases: {data['new_share'].iloc[0]:.0%} in {data.index[0]}, "
               f"about {since:.0%} since 2018",
           "Share of titles added within one year of their release year")
    return _save(fig, out_dir, "04_freshness.png")


def rating_mix(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.rating_mix_by_year(df) * 100
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bottom = np.zeros(len(data))
    for col in data.columns:
        ax.bar(data.index.astype(str), data[col], bottom=bottom, color=T.RATING_COLORS[col],
               edgecolor=T.SURFACE, linewidth=2, width=0.7, label=col)
        for i, v in enumerate(data[col]):
            if v >= 6:
                dark = col == "Adult"
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                        color="#ffffff" if dark else T.TEXT)
        bottom += data[col].values
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Share of titles added (%)")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    _title(ax, f"Kids' content fell from {data['Kids'].iloc[0]:.0f}% to {data['Kids'].min():.0f}% of additions, "
               f"then recovered to {data['Kids'].iloc[-1]:.0f}%",
           "Age-rating mix of titles added each year")
    return _save(fig, out_dir, "05_rating_mix.png")


def country_genre_heatmap(df: pd.DataFrame, out_dir: Path) -> Path:
    full = A.country_genre_lift(df, top_countries=8, top_genres=25)
    signature = {g for _, row in full.iterrows() for g in row.nlargest(2).index}
    big = list(full.columns[:5])  # the five most common genres, for context
    keep = [g for g in full.columns if g in signature or g in big]
    lift = full[keep]
    cmap = LinearSegmentedColormap.from_list("div", T.DIVERGING)
    norm = TwoSlopeNorm(vmin=0, vcenter=1, vmax=max(3.0, float(np.nanpercentile(lift.values, 97))))
    fig, ax = plt.subplots(figsize=(11, 5.2))
    im = ax.imshow(lift.values, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(lift.shape[1]), lift.columns, rotation=40, ha="right")
    ax.set_yticks(range(lift.shape[0]), lift.index)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(lift.shape[0]):
        for j in range(lift.shape[1]):
            v = lift.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5,
                    color="#ffffff" if v >= 2.2 or v <= 0.25 else T.TEXT)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Index (1.0 = same as whole catalogue)", color=T.TEXT_2)
    cbar.outline.set_visible(False)
    _title(ax, "Every major country has a signature genre",
           "Genre index: share of a country's titles in a genre vs. the whole catalogue (red = over-indexed, blue = under-indexed)")
    return _save(fig, out_dir, "06_country_genre_index.png")


def runtime_trend(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.runtime_by_release_year(df, start=2008)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(data.index, data["median"], color=T.MOVIE, lw=2, marker="o", ms=6, mec=T.SURFACE, mew=1.5)
    for year in (data.index.min(), data.index.max()):
        ax.annotate(f"{data.loc[year, 'median']:.0f} min", (year, data.loc[year, "median"]),
                    xytext=(0, 10), textcoords="offset points", ha="center", fontsize=9.5)
    ax.set_xticks(data.index)
    ax.set_ylim(80, 115)
    ax.set_ylabel("Median runtime (minutes)")
    _title(ax, f"Movies are getting shorter: median runtime fell from {data['median'].iloc[0]:.0f} to "
               f"{data['median'].iloc[-1]:.0f} minutes",
           "Median movie runtime by release year (years with at least 30 movies)")
    return _save(fig, out_dir, "07_runtime_trend.png")


def seasonality(df: pd.DataFrame, out_dir: Path) -> Path:
    data = A.monthly_additions(df)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(months, data.reindex(range(1, 13)).values, color=T.NEUTRAL, width=0.62)
    for i, v in enumerate(data.reindex(range(1, 13)).values):
        ax.text(i, v + 3, f"{v:.0f}", ha="center", fontsize=9.5)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Average titles added per month")
    _title(ax, "Additions peak in October to December; February is the quietest month",
           "Average titles added per calendar month, 2017 to 2020")
    return _save(fig, out_dir, "08_seasonality.png")


ALL_FIGURES = [
    growth_by_type,
    international_share,
    top_countries,
    freshness,
    rating_mix,
    country_genre_heatmap,
    runtime_trend,
    seasonality,
]


def make_all(df: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    return [fn(df, out) for fn in ALL_FIGURES]
