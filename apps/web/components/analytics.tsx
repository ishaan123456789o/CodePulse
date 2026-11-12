"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, Summary, Window } from "@/lib/api";
import { Kpis, MarketPanels, WindowSelect } from "./catalog";
import { RepoTable } from "./repo-table";
import { Empty, ErrorState, Loading } from "./states";
export function Analytics() {
  const [window, setWindow] = useState<Window>("7d");
  const query = useQuery({
    queryKey: ["summary", window],
    queryFn: () => api<Summary>(`/dashboard/summary?time_window=${window}`),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow accent">ECOSYSTEM SIGNALS</div>
          <h1>Follow the bigger picture</h1>
          <p>What’s gaining attention across the repositories in your index.</p>
        </div>
        <WindowSelect value={window} onChange={setWindow} />
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : (
        <>
          <Kpis data={query.data} />
          <MarketPanels data={query.data} />
          <section className="panel">
            <div className="panel-heading">
              <h2>Fastest growing</h2>
              <span className="eyebrow">OBSERVED STAR VELOCITY</span>
            </div>
            {query.data.fastest_growing.length ? (
              <RepoTable repos={query.data.fastest_growing} />
            ) : (
              <Empty
                title="Waiting for measured growth"
                description="Repositories will appear once their observation history covers this window."
              />
            )}
          </section>
          <section className="panel mt-6">
            <div className="panel-heading">
              <h2>Recently discovered</h2>
              <span className="eyebrow">LATEST ADDITIONS</span>
            </div>
            {query.data.recently_discovered.length ? (
              <RepoTable repos={query.data.recently_discovered} />
            ) : (
              <Empty />
            )}
          </section>
        </>
      )}
      <section className="panel methodology">
        <div className="eyebrow accent">TRANSPARENT BY DESIGN</div>
        <h2>What goes into momentum?</h2>
        <div className="method-grid">
          <div>
            <span>01</span>
            <h3>Measure actual change</h3>
            <p>
              Star velocity uses the exact time between observations. Relative
              growth accounts for the repository’s starting size. Two comparable
              windows are required to measure acceleration.
            </p>
          </div>
          <div>
            <span>02</span>
            <h3>Compare with context</h3>
            <p>
              Logarithmic scaling limits outliers. Peer percentiles require at
              least 10 other repositories of similar size and age. Missing
              factors remain unavailable; available weights are renormalized.
            </p>
          </div>
          <div>
            <span>03</span>
            <h3>Respect the unknowns</h3>
            <p>
              Missing boundaries, large observation gaps, and stale observations
              make growth unavailable. A metadata discovery heuristic is labeled
              separately. Neither score is a prediction.
            </p>
          </div>
        </div>
        <p className="muted text-xs">
          The index is a rotating sample of GitHub, not complete ecosystem
          coverage. Scores can change as the peer cohort and available
          measurements change.
        </p>
      </section>
    </>
  );
}
