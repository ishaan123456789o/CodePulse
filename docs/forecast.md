# CodePulse Forecast

CodePulse Forecast is an **experimental, explainable seven-day star-growth model**. Version `trend-1.0.0` is a statistical baseline with hand-selected parameters, not a trained machine-learning classifier. Live predictive accuracy, calibrated probabilities, and confidence intervals are not established. Momentum and early-discovery scores remain separate measurements/rankings.

## Target and model

The predicted quantity is **net new stars over seven days from the latest source observation**. Stars are a measurable attention proxy, not a measure of software quality, adoption, or investment value. The source observation must be no more than six hours old when a forecast is issued. The target date and source date are exposed in the API and repository card.

“Unusually strong growth” means meeting all three conditions:

- At least 20 net new stars.
- At least 2% of the source observation's star count.
- At least 1.5 times the weekly average growth across the preceding two observed weeks.

The threshold is rounded up to a whole star. The thresholds are initial product assumptions, not learned or empirically validated constants. Changing target semantics or model parameters requires a new model version.

Two comparable observed weeks are required. The existing coverage policy selects a boundary at or before each seven-day target, within 24 hours, rejects gaps greater than 26 hours, and uses actual elapsed time. Thus the lookback may be slightly longer than 14 days. The two windows' duration ratio must be between 0.8 and 1.25. Missing or stale data produces no prediction.

Let `r` be the most recent week's measured stars/day, and `p` the preceding week's rate:

```text
trend = clamp(r - p, -abs(r), abs(r))
projected_net_stars = max(-source_stars, 7 * (r + 0.5 * trend))
breakout_ratio = projected_net_stars / breakout_threshold
```

Negative net growth is preserved. The cap prevents the projected star count from becoming negative. The ranked list sorts by the breakout ratio with a repository-ID tie-breaker. A ratio of at least 1 indicates a potential breakout; it is **not a probability**. The comparison baseline projects `7 * r` (continue the recent rate).

## Storage and operation

Migration `0005_forecasts` adds `repository_forecasts`. There are no new dependencies, external model services, or API credentials.

```sh
# Apply migrations before restarting the API, worker and Beat.
make migrate
docker compose up -d --build api worker beat web
make forecast
```

Without Docker, run `uv run alembic upgrade head` and `uv run python -m app.workers.cli forecast` from `apps/api`, and restart the web/API/worker/Beat processes with the new code.

Beat runs the forecast job hourly. It saves at most one eligible forecast per repository per UTC day and model version. A first eligible run later in the day can still produce a forecast. Retries and subsequent observations do not rewrite its original projection, features, threshold, source timestamp, or issuance timestamp. Archived/disabled repositories are excluded. Current lists exclude source observations older than 30 hours; repository details retain the last forecast with an explicit stale flag.

Forecast generation reads repositories in batches of 100 and at most 17 days of observations per batch. It uses only snapshots observed **and inserted** no later than the run's start time. Mutable current repository star counts are not model inputs. Live forecasts only accept `github_rest` snapshots; demo forecasts only accept `synthetic_demo_fixture`. Demo rows are flagged and excluded from live results/evaluation. Demo fixtures never establish real predictive performance.

## Prospective evaluation

Each hourly job also evaluates up to 500 due forecasts, oldest first. It uses the first same-source observation at or after the stored target time, up to six hours late. Outcomes are normalized by actual elapsed time to seven-day equivalent growth; this approximation and the actual outcome timestamp are explicit. An observation outside that boundary does not count. After the six-hour allowance, missing outcomes are marked unavailable, not false predictions. Completed evaluations are not recomputed.

The validation API reports the following for forecasts issued during the last 90 days, separately by current model version and demo/live mode:

- Evaluated, pending, and unavailable counts.
- Predicted and actual breakout counts, precision, and recall.
- Mean absolute error in seven-day net stars for the model and continue-last-week baseline.

Undefined metrics are null, never zero. There is no automatic claim of readiness or accuracy after an arbitrary sample count. Daily forecasts have overlapping outcomes and are correlated; aggregate metrics are descriptive, not independent trials. Missing outcomes can bias results, which is why unavailable counts are shown.

## API and interface

- `GET /api/v1/forecast?page=1&page_size=20&breakouts_only=false`: current ranked forecasts, paginated (maximum page size 100).
- `GET /api/v1/repositories/{id}/forecast`: ready, stale, inactive, or insufficient-history status and latest forecast.
- `GET /api/v1/forecast/validation`: prospective evaluation summary.
- `/forecast`: outlook table, potential-breakout filter, methodology and evaluation.
- Repository detail: projection, target date, threshold explanation and outcome when available.

The new task appears in system status as `forecast`. There is no public endpoint that triggers forecasting.

## Next modeling stage

Collect real observations and prospective outcomes first. Before replacing this baseline with a learned model:

1. Assemble immutable point-in-time feature/label examples from genuine observations. Retain missing-outcome and selection information; never treat absent labels as negatives.
2. Use rolling chronological training/validation splits with a seven-day purge to keep label windows from crossing split boundaries. Audit repeated repository overlap and tune only inside training folds.
3. Compare against the current baseline, recent-rate continuation, and breakout prevalence. Report precision/recall, precision at a fixed review budget, errors, calibration if probabilities are produced, coverage and subgroup behavior.
4. Promote a version only after sufficient independent out-of-time evidence. Keep synthetic tests separate from performance evidence.

External publicity, topics, forks and developer activity are not modeled in v1. The tracked index is a sampled subset of GitHub; conclusions do not establish performance across all repositories.
