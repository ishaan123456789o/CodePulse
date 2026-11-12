# Analytics policy (model 1.0.0)

## Observations and coverage

All times are UTC. Snapshots are unique by repository and UTC hour; immutable retries preserve the first snapshot in that hour. Cadence is scheduled separately, so priority changes do not duplicate an hour. Search metadata is not counted as an observation. A repository metadata response or authenticated 304 confirms an observation.

For each window, use the newest observation at or before the calculation time. Select the nearest observation **at or before** the target boundary. Require it within 6h for a 24h window, 24h for 7d, and 48h for 30d. Never use an observation after the target boundary to pretend full coverage. Rates use the actual elapsed interval, exposed as `coverage.elapsed_days`; a nominal 24h window may therefore span 24–30 observed hours.

Maximum interior gaps: 26h for 24h/7d and 48h for 30d. Maximum endpoint age: 6h for 24h, 26h for 7d/30d. Insufficient boundaries, interior gaps and stale endpoints make metrics null. Baseline age and observation freshness remain visible. Low-priority daily polling will often lack a fresh 24h metric; longer windows remain usable.

Acceleration compares this window’s stars/day with the preceding window’s stars/day. Both must satisfy coverage and their actual durations must have a ratio between 0.8 and 1.25. Negative star changes are valid; rates are never silently clamped in reported measurements.

## Measured features

- Absolute growth = end stars − start stars.
- Relative growth = star change / max(start stars, 10).
- Velocity = star change / actual elapsed days.
- Acceleration = recent velocity − preceding velocity (stars/day difference, not a second derivative).
- Fork growth = end forks − start forks.
- Consistency = fraction of observed elapsed time spent in intervals with positive star changes; at least three observations required.
- Peer percentile = empirical percentile of velocity, with half-weight ties, among at least ten **other** repositories in the same size and age group. Archived/disabled peers are excluded.
- Optional commit activity = fully enumerated default-branch commits over seven days, capped at two pages of 100; never a partial total.
- Optional contributor activity = change in unique GitHub-linked active authors in those complete seven-day commit enumerations. Unlinked authors make the count unavailable. Old optional metadata is retained for inspection, but snapshots include signals only if collected within six hours.

Size groups: below 100; 100–999; 1,000–9,999; 10,000+. Age groups: below 90d; 90–364d; 365d+. Peer cohorts depend on the tracked index, not all GitHub. Detail comparisons show up to five comparable repositories when at least ten candidates are available within the bounded lookup.

## Observed momentum score

Weights: velocity 25%, relative growth 25%, acceleration 15%, forks 10%, consistency 10%, peer percentile 10%, commit activity 2.5%, contributor activity 2.5%.

Positive values are scaled using `min(1, log1p(value) / log1p(reference))`. References are 100 stars/day, 1.0 relative growth, 50 acceleration, 50 forks, 50 commits, and 10 additional active authors. Negative inputs contribute zero to this opportunity-ranking score but remain visible as negative measured values. Consistency and percentile are already bounded.

Unavailable weights are removed and available weights are renormalized. Contributions sum to the displayed 0–100 score (within rounding). Confidence combines the fraction of available weight and the observation sample count, saturating at five observations. It describes measurement support, not prediction accuracy or a statistical confidence interval. Changing features or peers can change a score even without changed star counts.

Persisted score history includes version, window, calculation time, contributions, feature values, missing indicators, coverage and confidence. Calculations use an hourly UTC cutoff and are unique by repository/window/hour/version; repeated runs in the same hour preserve the first result. A later observation enters the following hour’s score. Watchlist score changes compare the two latest compatible score records.

## Early discovery heuristic

Repositories without sufficient measured history receive a separate heuristic: capped log-scaled stars (35 points), forks (20), push recency within 90d (25), and repository newness within 365d (20). Archived/disabled repositories receive zero. Confidence is fixed at 0.2. This estimates discovery interest from metadata; it does not measure historical growth and is not included in Trending or measured momentum distributions. A stale established repository can also fall back to this heuristic; coverage explains why measurements are unavailable.

## Explanations

Deterministic templates use the actual signed growth, rates, acceleration and peer percentile. Each contribution is inspectable. Future optional LLM providers must consume only computed metrics, reject unsupported numeric claims, cache by version and metrics hash, and fall back to the deterministic templates on any error. No model is currently called.
