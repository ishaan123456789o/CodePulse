"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  GitFork,
  Github,
  Info,
  Star,
} from "lucide-react";
import { api, Coverage, Repository, Snapshot, Window } from "@/lib/api";
import { date, number, signed } from "@/lib/utils";
import { Button } from "./ui/button";
import { Loading, ErrorState } from "./states";
import { RepositoryForecast } from "./forecast";
import { HistoryChart } from "./charts";
import { RepoTable, ScoreBadge, WatchButton } from "./repo-table";
export function Detail({ id }: { id: string }) {
  const [window, setWindow] = useState<Window | "all">("7d");
  const scoreWindow = window === "all" ? "30d" : window;
  const repo = useQuery({
    queryKey: ["repository", id, scoreWindow],
    queryFn: () =>
      api<Repository>(`/repositories/${id}?time_window=${scoreWindow}`),
  });
  const history = useQuery({
    queryKey: ["history", id, window],
    queryFn: () =>
      api<{ observations: Snapshot[] }>(
        `/repositories/${id}/history?time_window=${window}`,
      ),
  });
  const metrics = useQuery({
    queryKey: ["metrics", id, scoreWindow],
    queryFn: () =>
      api<{
        features: Record<string, number | null>;
        coverage: Coverage;
        peers: Repository[];
      }>(`/repositories/${id}/metrics?time_window=${scoreWindow}`),
  });
  if (repo.isPending) return <Loading />;
  if (repo.isError)
    return <ErrorState error={repo.error} retry={() => repo.refetch()} />;
  const r = repo.data,
    m = metrics.data;
  return (
    <>
      <Link href="/discover" className="back-link">
        <ArrowLeft size={14} /> Back to discovery
      </Link>
      <div className="page-heading detail-heading">
        <div>
          <div className="eyebrow accent">REPOSITORY INTELLIGENCE</div>
          <h1>
            <span className="muted">{r.owner} / </span>
            {r.name}
          </h1>
          <p>{r.description || "No description provided."}</p>
          <div className="topics">
            <span className="pill">{r.category}</span>
            {r.topics.slice(0, 8).map((t) => (
              <span className="topic" key={t}>
                {t}
              </span>
            ))}
            {r.archived && <span className="pill">Archived</span>}
            {r.disabled && <span className="pill">Unavailable</span>}
          </div>
        </div>
        <div className="heading-actions">
          <Button asChild variant="outline">
            <a href={r.url} target="_blank" rel="noreferrer">
              <Github size={15} /> GitHub <ArrowUpRight size={13} />
            </a>
          </Button>
          <WatchButton repo={r} labeled />
        </div>
      </div>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">
            Stars
            <Star size={16} />
          </div>
          <strong>{number(r.stars)}</strong>
          <span>Latest GitHub metadata</span>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">
            Forks
            <GitFork size={16} />
          </div>
          <strong>{number(r.forks)}</strong>
          <span>Latest GitHub metadata</span>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">
            Star velocity<span>{scoreWindow}</span>
          </div>
          <strong>{signed(m?.features.star_velocity, 1)}</strong>
          <span>Stars / day · observed timestamps</span>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">
            Relative growth<span>{scoreWindow}</span>
          </div>
          <strong>
            {m?.features.relative_growth == null
              ? "—"
              : signed(m.features.relative_growth * 100, 1) + "%"}
          </strong>
          <span>Growth relative to starting stars</span>
        </div>
      </div>
      <div className="section-intro">
        <div>
          <h2>Repository trajectory</h2>
          <span className="pill">
            {window === "all" ? "All available history" : window}
          </span>
        </div>
        <div className="segmented">
          {(["24h", "7d", "30d", "all"] as const).map((w) => (
            <button
              key={w}
              aria-pressed={window === w}
              onClick={() => setWindow(w)}
            >
              {w === "all" ? "All history" : w}
            </button>
          ))}
        </div>
      </div>
      {m && !m.coverage.sufficient && (
        <div className="info-note">
          <Info size={17} />
          <span>
            <strong>Building a trustworthy baseline.</strong>{" "}
            {m.coverage.reason}. {m.coverage.history_days.toFixed(1)} days of
            observed history. No growth is inferred for missing periods.
          </span>
        </div>
      )}
      {metrics.isError && (
        <ErrorState error={metrics.error} retry={() => metrics.refetch()} />
      )}
      <div className="detail-grid">
        <div className="chart-stack">
          {(["stars", "forks"] as const).map((metric) => (
            <section className="panel" key={metric}>
              <div className="panel-heading">
                <h2>{metric === "stars" ? "Star history" : "Fork history"}</h2>
                <span className="eyebrow">ACTUAL OBSERVATIONS</span>
              </div>
              {history.isPending ? (
                <Loading />
              ) : history.isError ? (
                <ErrorState
                  error={history.error}
                  retry={() => history.refetch()}
                />
              ) : (
                <HistoryChart
                  points={history.data.observations}
                  metric={metric}
                />
              )}
            </section>
          ))}
        </div>
        <aside className="detail-side">
          <RepositoryForecast id={id} />
          <section className="panel score-panel">
            <div className="panel-heading">
              <h2>Behind the score</h2>
              <span className="pill">{scoreWindow}</span>
            </div>
            <ScoreBadge score={r.score} />
            {r.score && (
              <>
                <p className="muted text-xs">
                  Confidence {(r.score.confidence * 100).toFixed(0)}% · model{" "}
                  {r.score.scoring_version}
                  {r.score.stale && " · Recalculation overdue"}
                </p>
                <div className="contributions">
                  {Object.entries(r.score.feature_breakdown.contributions).map(
                    ([name, contribution]) => (
                      <div key={name}>
                        <div>
                          <span>{name.replaceAll("_", " ")}</span>
                          <span>
                            {contribution == null
                              ? "Unavailable"
                              : `${contribution.toFixed(1)} pts`}
                          </span>
                        </div>
                        <div className="track">
                          <i
                            style={{
                              width: `${Math.min(100, contribution || 0)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
                <ul className="explanations">
                  {r.score.explanation.map((e) => (
                    <li key={e}>
                      <CheckCircle2 size={14} />
                      <span>{e}</span>
                    </li>
                  ))}
                </ul>
                <small className="muted">
                  Calculated {date(r.score.calculated_at)}
                </small>
              </>
            )}
          </section>
          <section className="panel metadata">
            <h2>Repository facts</h2>
            <dl>
              {[
                ["Language", r.language || "Unspecified"],
                ["License", r.license || "Not provided"],
                ["Open issues + PRs", number(r.open_issues)],
                [
                  "Acceleration",
                  m?.features.star_acceleration == null
                    ? "Insufficient history"
                    : `${signed(m.features.star_acceleration, 1)} stars/day`,
                ],
                ["Active authors · 7 days", number(r.contributors)],
                ["Commits · 7 days", number(r.commits_7d)],
                ["Activity collected", date(r.activity_fetched_at)],
                ["Default branch", r.default_branch],
                ["Created", date(r.created_at_github)],
                ["Discovered", date(r.discovered_at)],
                ["Last observation", date(m?.coverage.end_at)],
                ["Metadata fetched", date(r.last_fetched_at)],
                ["Last push", date(r.pushed_at)],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <p className="muted text-xs">
              <Clock3 size={12} className="inline" /> Optional activity may be
              unavailable under the API budget.
            </p>
          </section>
        </aside>
      </div>
      {m && m.peers.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Similar repositories</h2>
            <span className="eyebrow">COMPARABLE SIZE AND AGE</span>
          </div>
          <RepoTable repos={m.peers} />
        </section>
      )}
    </>
  );
}
