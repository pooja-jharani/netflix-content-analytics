"""Tests for the analysis layer, using both a tiny hand-made frame and the real dataset."""

from pathlib import Path

import pandas as pd
import pytest

from netflix_analytics import analysis as A
from netflix_analytics import clean, load_raw

DATA = Path(__file__).resolve().parents[1] / "data" / "netflix_titles.csv"


@pytest.fixture(scope="module")
def df():
    return clean(load_raw(DATA))


def test_last_complete_year_excludes_partial_year(df):
    # The data ends mid-January 2021, so 2021 must not count as a complete year.
    assert A.last_complete_year(df) == 2020


def test_last_complete_year_when_year_is_finished():
    frame = pd.DataFrame({"date_added": pd.to_datetime(["2019-06-01", "2020-12-31"])})
    assert A.last_complete_year(frame) == 2020


def test_yearly_additions_exclude_partial_year(df):
    added = A.titles_added_per_year(df)
    assert added.index.max() == 2020
    assert set(added.columns) == {"Movie", "TV Show"}


def test_country_counts_exclude_unknown(df):
    counts = A.country_counts(df, 10)
    assert "Unknown" not in counts.index
    assert counts.index[0] == "United States"
    assert counts.is_monotonic_decreasing


def test_us_count_is_not_inflated_by_imputation(df):
    # Raw data has 2,883 titles whose first listed country is the US.
    assert A.country_counts(df, 1).iloc[0] == 2883


def test_international_share_between_0_and_1(df):
    share = A.international_share_by_year(df)["non_us_share"]
    assert share.between(0, 1).all()
    assert share.iloc[-1] > share.iloc[0]


def test_rating_mix_rows_sum_to_one(df):
    mix = A.rating_mix_by_year(df)
    assert (mix.sum(axis=1).round(6) == 1).all()


def test_genre_lift_excludes_geography_tags(df):
    lift = A.country_genre_lift(df)
    assert not set(lift.columns) & A.GEOGRAPHY_TAGS
    assert (lift >= 0).all().all()


def test_lift_is_one_when_country_matches_catalogue():
    # Two countries with identical genre mix -> index of 1.0 everywhere.
    rows = []
    for country in ("A", "B"):
        for _ in range(10):
            rows.append({"primary_country": country, "genres": ["Dramas", "Comedies"]})
    frame = pd.DataFrame(rows)
    lift = A.country_genre_lift(frame, top_countries=2, top_genres=2)
    assert lift.round(6).eq(1.0).all().all()


def test_signature_genre_respects_minimum_titles():
    rows = [{"primary_country": "A", "genres": ["Big"]} for _ in range(40)]
    rows += [{"primary_country": "A", "genres": ["Tiny"]} for _ in range(2)]
    rows += [{"primary_country": "B", "genres": ["Big", "Tiny"]} for _ in range(40)]
    result = A.signature_genre(pd.DataFrame(rows), "A", min_titles=30)
    assert result["genre"] == "Big"


def test_runtime_trend_is_negative_and_significant(df):
    result = A.runtime_trend_test(df)
    assert result["rho"] < 0
    assert result["p_value"] < 0.001


def test_non_us_shift_is_significant(df):
    result = A.non_us_shift_test(df)
    assert result["late_share"] > result["early_share"]
    assert result["p_value"] < 0.001


def test_director_concentration_is_fragmented(df):
    stats = A.director_concentration(df)
    assert stats["top_10_share_of_credits"] < 0.05
    assert 0 < stats["directors_with_one_title_share"] < 1


def test_headline_metrics(df):
    metrics = A.headline_metrics(df)
    assert metrics["titles"] == len(df)
    assert 0.6 < metrics["movie_share"] < 0.8
