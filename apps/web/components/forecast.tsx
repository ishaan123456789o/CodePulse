"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, Telescope } from "lucide-react";
import {
  api,
  Forecast,
  ForecastPage,
  ForecastStatus,
  ForecastValidation,
} from "@/lib/api";
import { date, number, signed } from "@/lib/utils";
import { Empty, ErrorState, Loading } from "./states";
import { Button } from "./ui/button";

function ForecastLabel({ forecast }: { forecast: Forecast }) {
  return (
    <span className={`pill ${forecast.predicted_breakout ? "accent" : ""}`}>
      {forecast.stale
        ? "Outdated forecast"
        : forecast.predicted_breakout
          ? "Potential breakout"
          : "Below breakout threshold"}
    </span>
  );
}

export function RepositoryForecast({ id }: { id: string }) {
  const query = useQuery({
    queryKey: ["forecast", "repository", id],
    queryFn: () => api<ForecastStatus>(`/repositories/${id}/forecast`),
  });
  const forecast = query.data?.forecast;
  return (
    <section className="panel score-panel">
      <div className="panel-heading">
        <h2>CodePulse Forecast</h2>
        <span className="pill">7 DAYS · EXPERIMENTAL</span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : forecast ? (
        <>
          <ForecastLabel forecast={forecast} />
          <p className="forecast-projection">
            {signed(forecast.projected_growth)}{" "}
            <small>projected net stars</small>
          </p>
          <p className="muted text-xs">
            From {date(forecast.as_of)} through {date(forecast.target_at)}.{" "}
            {forecast.stale && "This forecast is no longer current."}
          </p>
          <ul className="forecast-explanation">
            {forecast.explanation.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {forecast.evaluation_status === "evaluated" && (
            <p>
              Observed outcome: {signed(forecast.realized_growth)} net stars
              (seven-day equivalent).
            </p>
          )}
          {forecast.evaluation_status === "unavailable" && (
            <p>Outcome unavailable: no observation near the target date.</p>
          )}
        </>
      ) : (
        <p className="muted">{query.data.reason}</p>
      )}
      <Link href="/forecast" className="back-link">
        Explore forecasts and model evaluation →
      </Link>
    </section>
  );
}

export function ForecastDashboard() {
  const [page, setPage] = useState(1);
  const [breakoutsOnly, setBreakoutsOnly] = useState(false);
  const query = useQuery({
    queryKey: ["forecast", page, breakoutsOnly],
    queryFn: () =>
      api<ForecastPage>(
        `/forecast?page=${page}&page_size=20&breakouts_only=${breakoutsOnly}`,
      ),
  });
  const validation = useQuery({
    queryKey: ["forecast-validation"],
    queryFn: () => api<ForecastValidation>("/forecast/validation"),
  });
  const v = validation.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow accent">LOOKING SEVEN DAYS AHEAD</div>
          <h1>CodePulse Forecast</h1>
          <p>
            Which repositories could see unusually strong star growth next week?
          </p>
        </div>
        <span className="pill">
          <Telescope size={14} /> EXPERIMENTAL
        </span>
      </div>
      <div className="info-note">
        <Info size={18} />
        <span>
          <strong>A projection, with a testable track record.</strong> This
          statistical baseline extends recent growth and dampens changes in its
          rate. It has no calibrated probability. Live predictive performance is
          not yet established.
        </span>
      </div>
      {query.data?.demo && (
        <p className="demo-banner">
          Forecasts shown here use synthetic demo observations.
        </p>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Seven-day outlook</h2>
          <label className="check-filter">
            <input
              type="checkbox"
              checked={breakoutsOnly}
              onChange={(e) => {
                setBreakoutsOnly(e.target.checked);
                setPage(1);
              }}
            />{" "}
            Potential breakouts only
          </label>
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorState error={query.error} retry={() => query.refetch()} />
        ) : query.data.items.length ? (
          <>
            <div
              className="table-scroll"
              role="region"
              aria-label="Forecast results"
              tabIndex={0}
            >
              <table className="repo-table forecast-table">
                <thead>
                  <tr>
                    <th>Repository</th>
                    <th>Projected net stars · 7d</th>
                    <th>Breakout threshold</th>
                    <th>Projection / threshold</th>
                    <th>Outlook</th>
                    <th>Target date</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((f) => (
                    <tr key={f.id}>
                      <td>
                        <Link
                          className="repo-name"
                          href={`/repos/${f.repository_id}`}
                        >
                          {f.full_name}
                        </Link>
                        <div className="muted">
                          {f.language || "Unspecified"}
                        </div>
                      </td>
                      <td className="forecast-value">
                        {signed(f.projected_growth)}
                      </td>
                      <td>{number(f.breakout_threshold)} stars</td>
                      <td>{f.breakout_ratio.toFixed(2)}×</td>
                      <td>
                        <ForecastLabel forecast={f} />
                      </td>
                      <td>{date(f.target_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <Empty
            title={
              breakoutsOnly
                ? "No potential breakouts in the current forecast"
                : "Building a forecast history"
            }
            description={
              breakoutsOnly
                ? "No current projection reaches its repository’s breakout threshold. You can view all forecasts instead."
                : "Forecasts need at least 14 days of continuous observations, a recent snapshot, and a forecast worker run. Missing history is never replaced with invented data."
            }
            settings={!breakoutsOnly}
          />
        )}
        {query.data && query.data.total > 0 && (
          <div className="pagination">
            <span>
              {query.data.total} current forecasts · ranked by projection /
              threshold, not probability
            </span>
            <div>
              <Button
                variant="outline"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span>Page {page}</span>
              <Button
                variant="outline"
                disabled={page * 20 >= query.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>
      <section className="panel methodology">
        <div className="eyebrow accent">MEASURE THE PREDICTIONS TOO</div>
        <h2>Model evaluation</h2>
        <p>
          Saved predictions are compared with observations after seven days.
          Metrics below cover forecasts issued in the last 90 days. Daily
          forecasts overlap, so these are descriptive results, not independent
          trials.
        </p>
        {validation.isPending ? (
          <Loading />
        ) : validation.isError ? (
          <ErrorState
            error={validation.error}
            retry={() => validation.refetch()}
          />
        ) : (
          v && (
            <>
              {v.demo && (
                <p className="accent">
                  Synthetic evaluation only — not evidence of real-world
                  accuracy.
                </p>
              )}
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Evaluated forecasts</div>
                  <strong>{number(v.evaluated)}</strong>
                  <span>
                    {v.pending} pending · {v.unavailable} missing outcomes
                  </span>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Breakout precision</div>
                  <strong>
                    {v.precision == null
                      ? "—"
                      : `${(v.precision * 100).toFixed(0)}%`}
                  </strong>
                  <span>
                    Of {v.predicted_breakouts} evaluated breakout predictions
                  </span>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Forecast error</div>
                  <strong>
                    {v.mean_absolute_error == null
                      ? "—"
                      : v.mean_absolute_error.toFixed(1)}
                  </strong>
                  <span>Mean absolute error · net stars</span>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Continue-last-week error</div>
                  <strong>
                    {v.baseline_mean_absolute_error == null
                      ? "—"
                      : v.baseline_mean_absolute_error.toFixed(1)}
                  </strong>
                  <span>Comparison baseline · lower error is better</span>
                </div>
              </div>
              {!v.evaluated && (
                <p className="muted">
                  No evaluated outcomes yet. Accuracy is unknown until forecasts
                  mature and matching observations are collected.
                </p>
              )}
            </>
          )
        )}
        <div className="method-grid">
          <div>
            <span>01</span>
            <h3>Define unusual growth</h3>
            <p>
              At least 20 net stars, 2% of stars at forecast time, and 1.5× the
              weekly average across the preceding two observed weeks. Each
              repository must clear all three.
            </p>
          </div>
          <div>
            <span>02</span>
            <h3>Project with restraint</h3>
            <p>
              Use two comparable weeks of measured star growth. Carry half their
              change in daily rate forward, capped at half the magnitude of the
              recent rate. This is an explainable baseline, not a trained
              machine-learning model.
            </p>
          </div>
          <div>
            <span>03</span>
            <h3>Keep an honest record</h3>
            <p>
              One saved forecast per repository per UTC day. Target dates are
              seven days after the source observation. Outcomes within six hours
              after the target are normalized to seven days; missing outcomes
              stay unavailable.
            </p>
          </div>
        </div>
        <p className="muted text-xs">
          Forecasts older than 30 hours from their source observation are
          excluded. External events and sudden publicity are not modeled.{" "}
          {query.data?.model_version}
        </p>
      </section>
    </>
  );
}
