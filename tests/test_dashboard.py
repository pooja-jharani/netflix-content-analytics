"""Smoke tests: the dashboard renders without errors for many filter combinations."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")

# Widget order in the filter row: multiselect 0=Type, 1=Country, 2=Audience, 3=Genre; slider 0=Year added.
SCENARIOS = {
    "default": lambda a: None,
    "movies_only": lambda a: a.multiselect[0].set_value(["Movie"]),
    "tv_only": lambda a: a.multiselect[0].set_value(["TV Show"]),
    "india": lambda a: a.multiselect[1].set_value(["India"]),
    "japan_kids": lambda a: (a.multiselect[1].set_value(["Japan"]), a.multiselect[2].set_value(["Kids"])),
    "documentaries": lambda a: a.multiselect[3].set_value(["Documentaries"]),
    "two_years": lambda a: a.slider[0].set_value((2019, 2020)),
    "tiny_slice": lambda a: (
        a.multiselect[0].set_value(["Movie"]),
        a.multiselect[1].set_value(["South Korea"]),
        a.multiselect[2].set_value(["Kids"]),
        a.multiselect[3].set_value(["Anime Features"]),
    ),
    "empty_result": lambda a: (
        a.multiselect[0].set_value(["Movie"]),
        a.multiselect[1].set_value(["United States"]),
        a.multiselect[2].set_value(["Kids"]),
        a.multiselect[3].set_value(["Reality TV"]),
    ),
    "no_type_selected": lambda a: a.multiselect[0].set_value([]),
}


@pytest.mark.parametrize("name", SCENARIOS)
def test_dashboard_renders(name):
    at = AppTest.from_file(APP, default_timeout=120).run()
    SCENARIOS[name](at)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_default_view_shows_all_titles():
    at = AppTest.from_file(APP, default_timeout=120).run()
    titles = next(m for m in at.metric if m.label == "Titles")
    # Default year filter starts in 2014, so nearly the whole catalogue is in view.
    assert int(titles.value.replace(",", "")) > 7000


def test_empty_selection_shows_warning():
    at = AppTest.from_file(APP, default_timeout=120).run()
    SCENARIOS["no_type_selected"](at)
    at.run()
    assert any("No titles" in w.value for w in at.warning)
