"""Deterministic measurements and ranking; no IO or implicit clock reads."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite, log1p
from typing import Any, Literal

Window = Literal["24h", "7d", "30d"]
WINDOW_DAYS: dict[str, int] = {"24h": 1, "7d": 7, "30d": 30}
VERSION = "1.0.0"
WEIGHTS = {
    "star_velocity": 0.25,
    "relative_growth": 0.25,
    "star_acceleration": 0.15,
    "fork_growth": 0.10,
    "growth_consistency": 0.10,
    "peer_percentile": 0.10,
    "commit_activity": 0.025,
    "contributor_activity": 0.025,
}


def utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


@dataclass(frozen=True)
class Observation:
    observed_at: datetime
    stars: int
    forks: int
    contributors: int | None = None
    commits_7d: int | None = None


def compute_star_growth(start: Observation, end: Observation) -> int:
    return end.stars - start.stars


def compute_relative_growth(start: Observation, end: Observation) -> float:
    return compute_star_growth(start, end) / max(start.stars, 10)


def compute_star_velocity(start: Observation, end: Observation) -> float | None:
    days = (utc(end.observed_at) - utc(start.observed_at)).total_seconds() / 86400
    return compute_star_growth(start, end) / days if days > 0 else None


def compute_acceleration(recent: float | None, previous: float | None) -> float | None:
    return recent - previous if recent is not None and previous is not None else None


def compute_fork_growth(start: Observation, end: Observation) -> int:
    return end.forks - start.forks


def compute_growth_consistency(observations: list[Observation]) -> float | None:
    if len(observations) < 3:
        return None
    intervals = [
        (max(0, (utc(b.observed_at) - utc(a.observed_at)).total_seconds()), b.stars > a.stars)
        for a, b in zip(observations, observations[1:])
    ]
    total = sum(t for t, _ in intervals)
    return sum(t for t, positive in intervals if positive) / total if total else None


def compute_peer_percentile(value: float, peers: list[float], minimum: int = 10) -> float | None:
    peers = [p for p in peers if isfinite(p)]
    if len(peers) < minimum or not isfinite(value):
        return None
    return 100 * (sum(p < value for p in peers) + 0.5 * sum(p == value for p in peers)) / len(peers)


def peer_group(stars: int, age_days: float) -> tuple[int, int]:
    return (
        0 if stars < 100 else 1 if stars < 1000 else 2 if stars < 10000 else 3,
        0 if age_days < 90 else 1 if age_days < 365 else 2,
    )


def _boundary(
    points: list[Observation], end: Observation, days: int
) -> tuple[list[Observation], str | None]:
    target = utc(end.observed_at) - timedelta(days=days)
    tolerance = timedelta(hours={1: 6, 7: 24, 30: 48}[days])
    before = [p for p in points if utc(p.observed_at) <= target]
    if not before:
        return [], "History does not reach the requested boundary"
    start = before[-1]
    if target - utc(start.observed_at) > tolerance:
        return [], "No observation close enough to the window boundary"
    selected = [
        p for p in points if utc(start.observed_at) <= utc(p.observed_at) <= utc(end.observed_at)
    ]
    max_gap = timedelta(hours=26 if days < 30 else 48)
    if any(
        utc(b.observed_at) - utc(a.observed_at) > max_gap for a, b in zip(selected, selected[1:])
    ):
        return [], "Observation gaps exceed the coverage policy"
    return selected, None


def measure(observations: list[Observation], window: Window, now: datetime) -> dict[str, Any]:
    points = sorted(
        {utc(p.observed_at): p for p in observations if utc(p.observed_at) <= utc(now)}.values(),
        key=lambda p: utc(p.observed_at),
    )
    features = {
        key: None
        for key in [
            "star_growth",
            "relative_growth",
            "star_velocity",
            "star_acceleration",
            "fork_growth",
            "growth_consistency",
            "peer_percentile",
            "commit_activity",
            "contributor_activity",
        ]
    }
    coverage: dict[str, Any] = {
        "sufficient": False,
        "observation_count": len(points),
        "history_days": 0,
        "elapsed_days": None,
        "freshness_hours": None,
        "reason": "No observations yet",
        "start_at": None,
        "end_at": None,
    }
    if not points:
        return {"features": features, "coverage": coverage}
    end = points[-1]
    coverage.update(
        history_days=(utc(end.observed_at) - utc(points[0].observed_at)).total_seconds() / 86400,
        freshness_hours=(utc(now) - utc(end.observed_at)).total_seconds() / 3600,
        end_at=utc(end.observed_at).isoformat(),
    )
    freshness_limit = 6 if window == "24h" else 26
    if coverage["freshness_hours"] > freshness_limit:
        coverage["reason"] = "Latest observation is stale for this window"
        return {"features": features, "coverage": coverage}
    selected, reason = _boundary(points, end, WINDOW_DAYS[window])
    if reason:
        coverage["reason"] = reason
        return {"features": features, "coverage": coverage}
    start = selected[0]
    elapsed = (utc(end.observed_at) - utc(start.observed_at)).total_seconds() / 86400
    previous, _ = _boundary(points, start, WINDOW_DAYS[window])
    previous_velocity = None
    if previous:
        previous_days = (
            utc(start.observed_at) - utc(previous[0].observed_at)
        ).total_seconds() / 86400
        if 0.8 <= previous_days / elapsed <= 1.25:
            previous_velocity = compute_star_velocity(previous[0], start)
    features.update(
        star_growth=compute_star_growth(start, end),
        relative_growth=compute_relative_growth(start, end),
        star_velocity=compute_star_velocity(start, end),
        star_acceleration=compute_acceleration(
            compute_star_velocity(start, end), previous_velocity
        ),
        fork_growth=compute_fork_growth(start, end),
        growth_consistency=compute_growth_consistency(selected),
        commit_activity=end.commits_7d,
        contributor_activity=None
        if end.contributors is None or start.contributors is None
        else end.contributors - start.contributors,
    )
    coverage.update(
        sufficient=True,
        elapsed_days=elapsed,
        reason=None,
        start_at=utc(start.observed_at).isoformat(),
        window_observation_count=len(selected),
    )
    return {"features": features, "coverage": coverage}


def _log_scale(value: float, reference: float) -> float:
    return min(1, log1p(max(0, value)) / log1p(reference))


def generate_score_explanation(features: dict[str, float | None], score_type: str) -> list[str]:
    if score_type == "early_discovery":
        return [
            "Historical coverage is insufficient for measured momentum. This is a heuristic based on current repository metadata."
        ]
    out = [
        f"Gained {features['star_growth']:+,.0f} stars across the observed window ({features['star_velocity']:+,.1f} stars/day)."
    ]
    if features.get("star_acceleration") is not None:
        acceleration = features["star_acceleration"]
        if acceleration > 0:
            out.append(
                f"Star growth accelerated by {acceleration:,.1f} stars/day compared with the preceding window."
            )
        elif acceleration < 0:
            out.append(
                f"Star growth slowed by {abs(acceleration):,.1f} stars/day compared with the preceding window."
            )
    percentile = features.get("peer_percentile")
    if percentile is not None:
        out.append(
            f"Star velocity is at the {percentile:.0f}th percentile among projects of similar size and age."
        )
    return out


def compute_momentum_score(
    measurements: dict[str, Any], weights: dict[str, float] | None = None
) -> dict[str, Any] | None:
    if not measurements["coverage"]["sufficient"]:
        return None
    features, weights = measurements["features"], weights or WEIGHTS
    scales = {
        "star_velocity": 100,
        "relative_growth": 1,
        "star_acceleration": 50,
        "fork_growth": 50,
        "commit_activity": 50,
        "contributor_activity": 10,
    }
    normalized = {
        key: (
            None
            if features.get(key) is None
            else min(1, max(0, features[key] / 100))
            if key == "peer_percentile"
            else min(1, max(0, features[key]))
            if key == "growth_consistency"
            else _log_scale(features[key], scales[key])
        )
        for key in weights
    }
    available_weight = sum(weights[k] for k, v in normalized.items() if v is not None)
    contributions = {
        k: None if v is None else round(100 * weights[k] * v / available_weight, 4)
        for k, v in normalized.items()
    }
    score = round(min(100, max(0, sum(v or 0 for v in contributions.values()))), 2)
    count = measurements["coverage"]["window_observation_count"]
    confidence = round(min(1, available_weight * min(1, count / 5)), 2)
    return {
        "score": score,
        "score_type": "observed_momentum",
        "scoring_version": VERSION,
        "confidence": confidence,
        "coverage": measurements["coverage"],
        "feature_breakdown": {
            "values": features,
            "normalized": normalized,
            "contributions": contributions,
            "missing": [k for k, v in features.items() if v is None],
            "weights": weights,
        },
        "explanation": generate_score_explanation(features, "observed_momentum"),
    }


def compute_early_discovery_score(
    *,
    stars: int,
    forks: int,
    age_days: float,
    days_since_push: float | None,
    archived: bool,
    coverage: dict[str, Any],
) -> dict[str, Any]:
    # This is a metadata heuristic; stars/age is not reported as observed growth.
    factors = {
        "interest": 35 * _log_scale(stars, 1000),
        "fork_interest": 20 * _log_scale(forks, 100),
        "recency": 25 * max(0, 1 - (days_since_push if days_since_push is not None else 90) / 90),
        "newness": 20 * max(0, 1 - max(0, age_days) / 365),
    }
    if archived:
        factors = {k: 0.0 for k in factors}
    return {
        "score": round(sum(factors.values()), 2),
        "score_type": "early_discovery",
        "scoring_version": VERSION,
        "confidence": 0.2,
        "coverage": coverage,
        "feature_breakdown": {
            "values": {
                "stars": stars,
                "forks": forks,
                "age_days": age_days,
                "days_since_push": days_since_push,
            },
            "contributions": factors,
            "missing": ["observed_growth"],
        },
        "explanation": generate_score_explanation({}, "early_discovery"),
    }
