"""Shared colours so the static report and the dashboard look like one system.

Categorical pair (Movie / TV Show) was checked for colour-blind separation and
contrast against the chart surface. Ordered groups use a single-hue ramp, and
the lift heatmap uses a blue-grey-red diverging scale.
"""

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e6e5e1"

MOVIE = "#e34948"
TV = "#2a78d6"
NEUTRAL = "#52514e"      # whole-catalogue series (not a Movie/TV entity)
ACCENT = "#e50914"       # brand red, used for headers only

# Ordered rating groups, youngest -> oldest, light -> dark single hue.
RATING_COLORS = {
    "Kids": "#c5dbf5",
    "Family & Teens": "#86b2e8",
    "Adult": "#174b8f",
    "Unrated": "#b8b7b0",
}

DIVERGING = ["#2a78d6", "#f0efec", "#e34948"]  # under-indexed, par, over-indexed
