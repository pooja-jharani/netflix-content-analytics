import pandas as pd
import pytest

from netflix_analytics import clean, quality_summary


@pytest.fixture
def raw():
    return pd.DataFrame(
        {
            "show_id": ["s1", "s2", "s3", "s4", "s5"],
            "type": ["Movie", "TV Show", "Movie", "Movie", "Movie"],
            "title": ["A", "B", "C", "C", "D"],
            "director": ["X, Y", None, "Z", "Z", None],
            "cast": [None, "P", "Q", "Q", "R"],
            "country": ["United States, India", None, "India", "India", "France"],
            "date_added": ["January 5, 2019", " March 1, 2020", None, None, "July 9, 2016"],
            "release_year": [2018, 2020, 2015, 2015, 2017],
            "rating": ["TV-MA", "TV-Y", "PG-13", "PG-13", None],
            "duration": ["95 min", "2 Seasons", "120 min", "120 min", "88 min"],
            "listed_in": ["Dramas, Comedies", "Kids' TV", "Dramas", "Dramas", "Documentaries"],
            "description": ["d"] * 5,
        }
    )


def test_exact_duplicates_are_removed(raw):
    df = clean(raw)
    assert len(df) == 4
    assert quality_summary(raw, df)["duplicates_removed"] == 1


def test_missing_country_is_not_imputed(raw):
    df = clean(raw)
    row = df[df["title"] == "B"].iloc[0]
    assert row["primary_country"] == "Unknown"
    assert row["countries"] == []
    assert not row["is_us"]


def test_multi_value_columns_become_lists(raw):
    df = clean(raw)
    a = df[df["title"] == "A"].iloc[0]
    assert a["countries"] == ["United States", "India"]
    assert a["primary_country"] == "United States" and a["is_us"]
    assert a["genres"] == ["Dramas", "Comedies"]
    assert a["directors"] == ["X", "Y"]


def test_dates_are_parsed_and_whitespace_trimmed(raw):
    df = clean(raw)
    b = df[df["title"] == "B"].iloc[0]
    assert b["year_added"] == 2020 and b["month_added"] == 3
    assert pd.isna(df[df["title"] == "C"].iloc[0]["year_added"])


def test_duration_split_by_type(raw):
    df = clean(raw)
    a = df[df["title"] == "A"].iloc[0]
    b = df[df["title"] == "B"].iloc[0]
    assert a["runtime_min"] == 95 and pd.isna(a["seasons"])
    assert b["seasons"] == 2 and pd.isna(b["runtime_min"])


def test_rating_groups(raw):
    df = clean(raw).set_index("title")
    assert df.loc["A", "rating_group"] == "Adult"
    assert df.loc["B", "rating_group"] == "Kids"
    assert df.loc["C", "rating_group"] == "Family & Teens"
    assert df.loc["D", "rating"] == "Not Rated" and df.loc["D", "rating_group"] == "Unrated"


def test_years_to_add(raw):
    df = clean(raw).set_index("title")
    assert df.loc["A", "years_to_add"] == 1
    assert df.loc["D", "years_to_add"] == -1
