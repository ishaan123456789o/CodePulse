"use client";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleAlert,
  Database,
  Github,
  RefreshCw,
  Server,
} from "lucide-react";
import { api, Status } from "@/lib/api";
import { date } from "@/lib/utils";
import { ErrorState, Loading } from "./states";
import { Button } from "./ui/button";
export function Settings() {
  const query = useQuery({
    queryKey: ["status"],
    queryFn: () => api<Status>("/system/status"),
    refetchInterval: 60000,
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow accent">WORKSPACE CONFIGURATION</div>
          <h1>System & connections</h1>
          <p>Collection health, API budgets, and how this workspace runs.</p>
        </div>
        <Button
          variant="outline"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw size={14} /> Refresh status
        </Button>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : (
        <>
          <div className="status-grid">
            {[
              {
                name: "GitHub ingestion",
                icon: Github,
                value: query.data.ingestion.replaceAll("_", " "),
                good: query.data.ingestion === "active",
              },
              {
                name: "Redis broker",
                icon: Database,
                value: query.data.redis,
                good: query.data.redis === "healthy",
              },
              {
                name: "Worker heartbeat",
                icon: Server,
                value: query.data.worker_healthy ? "healthy" : "not detected",
                good: query.data.worker_healthy,
              },
            ].map(({ name, icon: Icon, value, good }) => (
              <section key={name} className="panel connection-card">
                <Icon size={22} />
                <h2>{name}</h2>
                <span className={good ? "positive" : "warning"}>
                  {good ? (
                    <CheckCircle2 size={14} />
                  ) : (
                    <CircleAlert size={14} />
                  )}{" "}
                  {value}
                </span>
              </section>
            ))}
          </div>
          <div className="settings-grid">
            <section className="panel settings-panel">
              <h2>Connect GitHub</h2>
              <p>
                Set <code>GITHUB_TOKEN</code> in the server’s ignored{" "}
                <code>.env</code> file. A fine-grained token with public
                repository read access is sufficient for metadata and discovery.
                No write permissions or LLM key are required.
              </p>
              <pre>GITHUB_TOKEN=your_token_here</pre>
              <p>
                Restart the API, worker and Beat after changing configuration.
                Then start discovery with the operator command:
              </p>
              <pre>make discover{`\n`}make track</pre>
              <span className="info-note">
                Credentials stay on the server and are never sent to this
                browser.
              </span>
              <h3>Anonymous workspace</h3>
              <p>
                Your browser stores a random workspace ID. Watchlists persist in
                PostgreSQL. The ID is an identifier, not authentication: deploy
                behind access control before sharing a private workspace.
              </p>
            </section>
            <section className="panel settings-panel">
              <h2>Collection policy</h2>
              <dl className="settings-list">
                {Object.entries(query.data.cadences_hours).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k} priority</dt>
                    <dd>Every {v}h</dd>
                  </div>
                ))}
                {Object.entries(query.data.budgets).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k} request budget</dt>
                    <dd>{v} / run</dd>
                  </div>
                ))}
                <div>
                  <dt>Recent job failures</dt>
                  <dd>{query.data.recent_failures}</dd>
                </div>
                <div>
                  <dt>Last worker heartbeat</dt>
                  <dd>
                    {query.data.worker_last_seen
                      ? date(
                          new Date(
                            query.data.worker_last_seen * 1000,
                          ).toISOString(),
                        )
                      : "Not detected"}
                  </dd>
                </div>
              </dl>
              <h3>Rate-limit resources</h3>
              {Object.entries(query.data.quotas).length ? (
                Object.entries(query.data.quotas).map(([key, quota]) => (
                  <div className="quota" key={key}>
                    <strong>{key}</strong>
                    <span>
                      {quota.remaining} / {quota.limit} requests remaining
                    </span>
                    <small>
                      Resets {date(new Date(quota.reset * 1000).toISOString())}
                    </small>
                  </div>
                ))
              ) : (
                <p>
                  No rate-limit headers observed yet. Quotas are learned from
                  GitHub responses.
                </p>
              )}
              {query.data.cooldown_until && (
                <p className="warning">
                  Requests paused until{" "}
                  {date(
                    new Date(query.data.cooldown_until * 1000).toISOString(),
                  )}
                </p>
              )}
            </section>
          </div>
          <section className="panel settings-panel">
            <h2>Latest discovery run</h2>
            {query.data.last_discovery ? (
              <dl className="settings-list">
                <div>
                  <dt>Status</dt>
                  <dd>{query.data.last_discovery.status}</dd>
                </div>
                <div>
                  <dt>Started</dt>
                  <dd>{date(query.data.last_discovery.started_at)}</dd>
                </div>
                <div>
                  <dt>Repositories found</dt>
                  <dd>{query.data.last_discovery.repositories_found}</dd>
                </div>
                {query.data.last_discovery.error && (
                  <div>
                    <dt>Collector message</dt>
                    <dd>{query.data.last_discovery.error}</dd>
                  </div>
                )}
              </dl>
            ) : (
              <p>
                No discovery runs recorded. Scheduled discovery begins when the
                worker is running and a GitHub token is configured.
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}
