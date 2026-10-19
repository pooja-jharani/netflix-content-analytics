"""Interactive dashboard for the Netflix content analysis.

Run locally:  streamlit run streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from netflix_analytics import analysis as A
from netflix_analytics import clean, data_quality_report, load_raw, quality_summary
from netflix_analytics import theme as T
from netflix_analytics.cleaning import RATING_GROUP_ORDER, UNKNOWN

DATA_PATH = Path(__file__).parent / "data" / "netflix_titles.csv"

st.set_page_config(page_title="Netflix Content Analytics", page_icon="🎬", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 2rem; max-width: 1200px; }}
      h1 {{ color: {T.ACCENT}; margin-bottom: 0; }}
      [data-testid="stMetricValue"] {{ font-size: 1.7rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data():
    raw = load_raw(DATA_PATH)
    df = clean(raw)
    return raw, df


raw, full = load_data()
LAST_YEAR = A.last_complete_year(full)


def base_layout(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", y=1.1, x=0),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=T.GRID)
    fig.update_yaxes(gridcolor=T.GRID, zeroline=False)
    return fig


def not_enough_data():
    st.info("Not enough titles match the current filters to draw this chart. Try widening them.")


# ---------------------------------------------------------------- header
st.title("Netflix Content Analytics")
st.caption(
    f"{len(full):,} titles added up to {full['date_added'].max():%d %b %Y}. "
    "Counts describe what was in the catalogue, not what people watched."
)

# ---------------------------------------------------------------- filters (one row)
f1, f2, f3, f4, f5 = st.columns([1.9, 1.4, 1.4, 1.4, 1.6])
types = f1.multiselect("Type", ["Movie", "TV Show"], default=["Movie", "TV Show"])
min_year, max_year = int(full["year_added"].min()), int(full["year_added"].max())
years = f2.slider("Year added", min_year, max_year, (2014, max_year))
top_countries = full.loc[full["primary_country"] != UNKNOWN, "primary_country"].value_counts().index.tolist()
countries = f3.multiselect("Country", top_countries, placeholder="All countries")
ratings = f4.multiselect("Audience", RATING_GROUP_ORDER, placeholder="All audiences")
all_genres = sorted(full["genres"].explode().dropna().unique())
genres = f5.multiselect("Genre", all_genres, placeholder="All genres")

mask = full["type"].isin(types) & full["year_added"].between(*years)
if countries:
    mask &= full["primary_country"].isin(countries)
if ratings:
    mask &= full["rating_group"].isin(ratings)
if genres:
    chosen = set(genres)
    mask &= full["genres"].map(lambda g: bool(chosen.intersection(g)))
df = full[mask]

if df.empty:
    st.warning("No titles match these filters.")
    st.stop()

# ---------------------------------------------------------------- KPIs
m = A.headline_metrics(df)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Titles", f"{m['titles']:,}")
k2.metric("Movies", f"{m['movie_share']:.0%}")
k3.metric("US share (known country)", "n/a" if pd.isna(m["us_share_known"]) else f"{m['us_share_known']:.0%}")
k4.metric("Median movie runtime", "n/a" if pd.isna(m["median_runtime"]) else f"{m['median_runtime']:.0f} min")
k5.metric("Countries", f"{m['countries']:,}")

tab_growth, tab_geo, tab_genre, tab_aud, tab_talent, tab_data = st.tabs(
    ["Growth", "Geography", "Genres", "Audience & format", "Talent", "Data & method"]
)

# ---------------------------------------------------------------- growth
with tab_growth:
    added = A.titles_added_per_year(df, last_year=LAST_YEAR)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Titles added per year")
        if added.empty:
            not_enough_data()
        else:
            fig = go.Figure()
            for col, color in (("Movie", T.MOVIE), ("TV Show", T.TV)):
                if col in added:
                    fig.add_scatter(x=added.index, y=added[col], name=col, mode="lines+markers",
                                    line=dict(color=color, width=2.5), marker=dict(size=8, line=dict(color=T.SURFACE, width=2)),
                                    hovertemplate=f"{col}: %{{y:,}} titles<extra>%{{x}}</extra>")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(base_layout(fig), width="stretch")
            st.caption(f"Years after {LAST_YEAR} are excluded because the data ends {full['date_added'].max():%d %b %Y}.")
    with c2:
        st.subheader("Seasonality")
        monthly = A.monthly_additions(df, last_year=LAST_YEAR).reindex(range(1, 13))
        if monthly.isna().all():
            not_enough_data()
        else:
            names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            fig = go.Figure(go.Bar(x=names, y=monthly.values, marker_color=T.NEUTRAL,
                                   hovertemplate="%{x}: %{y:.0f} titles a month<extra></extra>"))
            fig.update_yaxes(title="Avg titles added / month")
            st.plotly_chart(base_layout(fig), width="stretch")
            st.caption("Average per month across 2017 to 2020 (within your filters).")

# ---------------------------------------------------------------- geography
with tab_geo:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top countries")
        counts = A.country_counts(df, 10)[::-1]
        if counts.empty:
            not_enough_data()
        else:
            fig = go.Figure(go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color=T.NEUTRAL,
                                   text=[f"{v:,}" for v in counts.values], textposition="outside",
                                   hovertemplate="%{y}: %{x:,} titles<extra></extra>"))
            fig.update_xaxes(showgrid=True, gridcolor=T.GRID, range=[0, float(counts.max()) * 1.18])
            st.plotly_chart(base_layout(fig, 400), width="stretch")
            unknown = int((df["primary_country"] == UNKNOWN).sum())
            st.caption(f"{unknown:,} titles with no country listed are excluded.")
    with c2:
        st.subheader("Non-US share of additions")
        intl = A.international_share_by_year(df, min_titles=15, last_year=LAST_YEAR)
        if len(intl) < 2:
            not_enough_data()
        else:
            fig = go.Figure(go.Scatter(x=intl.index, y=intl["non_us_share"] * 100, mode="lines+markers",
                                       line=dict(color=T.NEUTRAL, width=2.5), marker=dict(size=8, line=dict(color=T.SURFACE, width=2)),
                                       customdata=intl["titles"],
                                       hovertemplate="%{y:.0f}% non-US (%{customdata:,} titles)<extra>%{x}</extra>"))
            fig.update_yaxes(range=[0, 100], title="% of titles")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(base_layout(fig, 400), width="stretch")
            st.caption("Years with fewer than 15 titles in your filters are hidden.")

# ---------------------------------------------------------------- genres
with tab_genre:
    c1, c2 = st.columns([2, 3])
    with c1:
        st.subheader("Most common genre tags")
        gc = A.genre_counts(df, 10)[::-1]
        if gc.empty:
            not_enough_data()
        else:
            fig = go.Figure(go.Bar(x=gc.values, y=gc.index, orientation="h", marker_color=T.NEUTRAL,
                                   hovertemplate="%{y}: %{x:,} titles<extra></extra>"))
            fig.update_xaxes(showgrid=True, gridcolor=T.GRID)
            st.plotly_chart(base_layout(fig, 420), width="stretch")
            st.caption("A title can carry several tags, so bars add up to more than the title count.")
    with c2:
        st.subheader("Which countries lean on which genres?")
        lift = A.country_genre_lift(df, top_countries=8, top_genres=14)
        if lift.shape[0] < 2 or lift.shape[1] < 2:
            not_enough_data()
        else:
            fig = go.Figure(go.Heatmap(
                z=lift.values, x=lift.columns, y=lift.index, zmin=0, zmid=1, zmax=3,
                colorscale=[[0, T.DIVERGING[0]], [1 / 3, T.DIVERGING[1]], [1, T.DIVERGING[2]]],
                colorbar=dict(title="Index"), texttemplate="%{z:.1f}", textfont=dict(size=11),
                hovertemplate="%{y} / %{x}<br>%{z:.2f}x the catalogue average<extra></extra>"))
            fig.update_xaxes(tickangle=-40, showgrid=False)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(base_layout(fig, 420), width="stretch")
            st.caption("1.0 = same as the whole filtered catalogue; above 1 (red) = over-indexed, below 1 (blue) = under-indexed. "
                       "Geography tags such as 'International Movies' are excluded.")

# ---------------------------------------------------------------- audience & format
with tab_aud:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Audience mix of additions")
        mix = A.rating_mix_by_year(df, min_titles=15, last_year=LAST_YEAR) * 100
        if mix.empty:
            not_enough_data()
        else:
            fig = go.Figure()
            for col in mix.columns:
                fig.add_bar(x=mix.index, y=mix[col], name=col, marker_color=T.RATING_COLORS[col],
                            marker_line=dict(color=T.SURFACE, width=2),
                            hovertemplate=f"{col}: %{{y:.0f}}%<extra>%{{x}}</extra>")
            fig.update_layout(barmode="stack", legend=dict(traceorder="normal"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(title="% of titles added", range=[0, 100])
            st.plotly_chart(base_layout(fig), width="stretch")
            st.caption("Kids = TV-Y/Y7/G; Family & Teens = TV-PG/PG/PG-13/TV-14; Adult = TV-MA/R/NC-17.")
    with c2:
        st.subheader("Movie runtime by release year")
        rt = A.runtime_by_release_year(df, start=2008, min_titles=10, last_year=LAST_YEAR)
        if len(rt) < 2:
            not_enough_data()
        else:
            fig = go.Figure(go.Scatter(x=rt.index, y=rt["median"], mode="lines+markers",
                                       line=dict(color=T.MOVIE, width=2.5), marker=dict(size=8, line=dict(color=T.SURFACE, width=2)),
                                       customdata=rt["titles"],
                                       hovertemplate="%{y:.0f} min median (%{customdata:,} movies)<extra>%{x}</extra>"))
            fig.update_yaxes(title="Median minutes")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(base_layout(fig), width="stretch")
    st.subheader("How long do TV shows run?")
    tv = df[df["seasons"].notna()]
    if tv.empty:
        st.caption("No TV shows in the current filters.")
    else:
        dist = tv["seasons"].clip(upper=6).value_counts().sort_index()
        labels = [f"{int(i)}" if i < 6 else "6+" for i in dist.index]
        fig = go.Figure(go.Bar(x=labels, y=dist.values, marker_color=T.TV,
                               hovertemplate="%{x} season(s): %{y:,} shows<extra></extra>"))
        fig.update_xaxes(title="Seasons")
        fig.update_yaxes(title="Shows")
        st.plotly_chart(base_layout(fig, 300), width="stretch")
        st.caption(f"{(tv['seasons'] == 1).mean():.0%} of the TV shows in view have a single season.")

# ---------------------------------------------------------------- talent
with tab_talent:
    st.subheader("Directors with the most titles")
    td = A.top_directors(df, 10)[::-1]
    conc = A.director_concentration(df)
    if td.empty:
        not_enough_data()
    else:
        fig = go.Figure(go.Bar(x=td.values, y=td.index, orientation="h", marker_color=T.NEUTRAL,
                               hovertemplate="%{y}: %{x} titles<extra></extra>"))
        fig.update_xaxes(showgrid=True, gridcolor=T.GRID)
        st.plotly_chart(base_layout(fig, 400), width="stretch")
        t1, t2, t3 = st.columns(3)
        t1.metric("Directors", f"{conc['unique_directors']:,}")
        t2.metric("Directed only one title", f"{conc['directors_with_one_title_share']:.0%}")
        t3.metric("Top 10 share of credits", f"{conc['top_10_share_of_credits']:.1%}")
        st.caption("About 31% of titles have no director listed, so these figures cover titles with a director only.")

# ---------------------------------------------------------------- data & method
with tab_data:
    st.subheader("Filtered titles")
    view = df[["title", "type", "primary_country", "release_year", "year_added", "rating", "duration"]].copy()
    view["genres"] = df["genres"].map(", ".join)
    st.dataframe(view, width="stretch", hide_index=True, height=320)
    st.download_button("Download filtered data (CSV)", view.to_csv(index=False).encode("utf-8"),
                       file_name="netflix_filtered.csv", mime="text/csv")

    st.subheader("Data quality")
    q = quality_summary(raw, full)
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Duplicates removed", q["duplicates_removed"])
    q2.metric("Missing country", f"{q['missing_country']:,}")
    q3.metric("Missing director", f"{q['missing_director']:,}")
    q4.metric("Added before release year", q["added_before_release"])
    st.dataframe(data_quality_report(raw), width="stretch")

    st.subheader("Method and limitations")
    st.markdown(
        """
- Missing values are labelled **Unknown**, never filled with the most common value.
- Only the **first listed country** is used for each title, so co-productions count once.
- The data is a **snapshot**: titles removed from the catalogue before it was taken are absent (survivorship bias).
- There is **no viewership data**: "top" means "most titles", not "most watched".
- The genre index is the share of a country's titles in a genre divided by the share across the catalogue.
        """
    )
