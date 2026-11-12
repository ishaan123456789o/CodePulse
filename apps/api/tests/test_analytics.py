from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.engine import (
    Observation,
    compute_acceleration,
    compute_early_discovery_score,
    compute_momentum_score,
    compute_peer_percentile,
    compute_relative_growth,
    compute_star_velocity,
    measure,
)

NOW = datetime(2026, 1, 31, tzinfo=timezone.utc)


def point(hours, stars, forks=2):
    return Observation(NOW + timedelta(hours=hours), stars, forks)


def test_no_invented_history():
    for history in [[], [point(0, 100)], [point(-12, 90), point(0, 100)]]:
        result = measure(history, "24h", NOW)
        assert result["features"]["star_velocity"] is None
        assert compute_momentum_score(result) is None


def test_actual_uneven_elapsed_time_and_negative_growth():
    result = measure([point(-25, 100), point(-5, 90), point(0, 80)], "24h", NOW)
    assert result["coverage"]["sufficient"]
    assert result["features"]["star_velocity"] == pytest.approx(-20 / (25 / 24))
    assert result["features"]["star_growth"] == -20
    assert compute_momentum_score(result)["score"] == 0


def test_boundary_policy_does_not_extrapolate():
    assert not measure([point(-23, 1), point(0, 10)], "24h", NOW)["coverage"]["sufficient"]
    assert not measure([point(-40, 1), point(-10, 5), point(0, 10)], "24h", NOW)["coverage"][
        "sufficient"
    ]


def test_stale_and_internal_gap():
    assert not measure([point(-48, 1), point(-24, 10)], "24h", NOW)["coverage"]["sufficient"]
    assert not measure([point(-168, 1), point(0, 10)], "7d", NOW)["coverage"]["sufficient"]


def test_acceleration_requires_two_windows():
    assert (
        measure([point(-24, 1), point(0, 10)], "24h", NOW)["features"]["star_acceleration"] is None
    )
    result = measure([point(-48, 100), point(-24, 110), point(-12, 125), point(0, 140)], "24h", NOW)
    assert result["features"]["star_acceleration"] == 20
    assert "accelerated" in " ".join(compute_momentum_score(result)["explanation"])


def test_zero_duplicate_and_peer_guards():
    assert compute_relative_growth(point(-24, 0), point(0, 10)) == 1
    assert compute_star_velocity(point(0, 0), point(0, 1)) is None
    assert compute_acceleration(1, None) is None
    assert compute_peer_percentile(10, [1, 2]) is None
    assert compute_peer_percentile(10, [10] * 10) == 50
    assert compute_peer_percentile(999999, list(range(10))) == 100


def test_determinism_bounds_and_explanations():
    history = [point(-48, 0), point(-24, 1), point(-12, 10000), point(0, 10000000)]
    a = compute_momentum_score(measure(history, "24h", NOW))
    assert a == compute_momentum_score(measure(history, "24h", NOW))
    assert 0 <= a["score"] <= 100
    assert sum(v or 0 for v in a["feature_breakdown"]["contributions"].values()) == pytest.approx(
        a["score"], abs=0.01
    )


def test_early_is_explicit_and_archived_is_zero():
    score = compute_early_discovery_score(
        stars=500, forks=20, age_days=5, days_since_push=None, archived=True, coverage={}
    )
    assert score["score_type"] == "early_discovery"
    assert score["score"] == 0
    assert "heuristic" in score["explanation"][0]
