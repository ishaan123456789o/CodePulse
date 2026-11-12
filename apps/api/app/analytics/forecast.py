"""Experimental seven-day damped-trend baseline. Pure, point-in-time inputs only."""

from datetime import datetime
from math import ceil

from app.analytics.engine import Observation, measure, utc

VERSION = "trend-1.0.0"
HORIZON_DAYS = 7
MIN_HISTORY_DAYS = 14


def predict(observations: list[Observation], now: datetime) -> dict:
    points = sorted(
        {utc(p.observed_at): p for p in observations if utc(p.observed_at) <= utc(now)}.values(),
        key=lambda p: utc(p.observed_at),
    )
    unavailable = {"status": "insufficient_history", "prediction": None}
    recent = measure(points, "7d", now)
    coverage = recent["coverage"]
    if not coverage["sufficient"]:
        return {**unavailable, "reason": coverage["reason"]}
    if coverage["freshness_hours"] > 6:
        return {**unavailable, "reason": "Forecasts require an observation from the last six hours"}
    boundary = datetime.fromisoformat(coverage["start_at"])
    previous = measure(points, "7d", boundary)
    if not previous["coverage"]["sufficient"]:
        return {**unavailable, "reason": "At least 14 days of continuous observations are required"}
    elapsed = coverage["elapsed_days"]
    previous_elapsed = previous["coverage"]["elapsed_days"]
    if not 0.8 <= previous_elapsed / elapsed <= 1.25:
        return {**unavailable, "reason": "The two observed weeks are not comparable"}

    recent_rate = recent["features"]["star_velocity"]
    previous_rate = previous["features"]["star_velocity"]
    # Carry half the change in weekly rates forward, capped to resist a sudden spike.
    trend = max(-abs(recent_rate), min(abs(recent_rate), recent_rate - previous_rate))
    projected = max(-points[-1].stars, HORIZON_DAYS * (recent_rate + 0.5 * trend))
    baseline = (
        HORIZON_DAYS
        * (recent["features"]["star_growth"] + previous["features"]["star_growth"])
        / (elapsed + previous_elapsed)
    )
    threshold = ceil(max(20, points[-1].stars * 0.02, 1.5 * max(0, baseline)))
    return {
        "status": "ready",
        "reason": None,
        "prediction": {
            "as_of": utc(points[-1].observed_at),
            "stars_at_origin": points[-1].stars,
            "projected_growth": round(projected, 2),
            "baseline_growth": round(HORIZON_DAYS * recent_rate, 2),
            "breakout_threshold": threshold,
            "breakout_ratio": round(projected / threshold, 4),
            "predicted_breakout": round(projected, 2) >= threshold,
            "features": {
                "recent_stars_per_day": recent_rate,
                "previous_stars_per_day": previous_rate,
                "historical_weekly_average": baseline,
                "damped_trend_per_day": 0.5 * trend,
                "history_days": elapsed + previous_elapsed,
            },
            "explanation": [
                f"Recent star growth: {recent_rate:+.1f}/day; preceding week: {previous_rate:+.1f}/day.",
                "The model projects the recent rate plus half the change in rate, with a cap on the trend.",
                f"Unusually strong growth means at least {threshold:,} net new stars over seven days.",
                "Experimental statistical baseline; no calibrated probability or validated accuracy yet.",
            ],
        },
    }
