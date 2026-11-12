"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowDownUp,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Compass,
  Database,
  Radio,
  Search,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, Page, Summary, Window } from "@/lib/api";
import { number } from "@/lib/utils";
import { Button } from "./ui/button";
import { Empty, ErrorState, Loading } from "./states";
import { RepoTable } from "./repo-table";
import { Distribution } from "./charts";
export function WindowSelect({
  value,
  onChange,
}: {
  value: Window;
  onChange: (value: Window) => void;
}) {
  return (
    <div className="segmented" aria-label="Time window">
      {(["24h", "7d", "30d"] as const).map((w) => (
        <button key={w} aria-pressed={value === w} onClick={() => onChange(w)}>
          {w === "24h" ? "24 hours" : w === "7d" ? "7 days" : "30 days"}
        </button>
      ))}
    </div>
  );
}
export function Kpis({ data }: { data: Summary }) {
  const cards = [
    {
      label: "Repositories tracked",
      value: data.repositories_tracked,
      icon: Database,
      hint: "In your discovery index",
    },
    {
      label: "Emerging repositories",
      value: data.emerging_repositories,
      icon: Compass,
      hint: "Active · under 10k stars",
    },
    {
      label: "High momentum",
      value: data.high_momentum_repositories,
      icon: TrendingUp,
      hint: "Observed score ≥ 65",
    },
    {
      label: "Discovered today",
      value: data.new_discoveries_today,
      icon: Radio,
      hint: "Since midnight UTC",
    },
  ];
  return (
    <div className="kpi-grid">
      {cards.map(({ label, value, icon: Icon, hint }) => (
        <div className="kpi-card" key={label}>
          <div className="kpi-label">
            {label}
            <Icon size={16} />
          </div>
          <strong>{number(value)}</strong>
          <span>
            <span className="tiny-dot" />
            {hint}
          </span>
        </div>
      ))}
    </div>
  );
}
export function MarketPanels({ data }: { data: Summary }) {
  const total = data.repositories_tracked;
  return (
    <div className="market-grid">
      <section className="panel">
        <div className="panel-heading">
          <h2>Momentum distribution</h2>
          <span className="eyebrow">OBSERVED ONLY</span>
        </div>
        {data.momentum_distribution.some((d) => d.count) ? (
          <Distribution data={data.momentum_distribution} />
        ) : (
          <div className="chart-empty">
            The signal is still forming
            <small>
              Measured scores appear after sufficient history is collected.
            </small>
          </div>
        )}
        <div className="panel-foot">
          <span className="tiny-dot" /> Repository count by momentum score
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Across the ecosystem</h2>
          <span className="eyebrow">CATEGORIES</span>
        </div>
        {data.categories.length ? (
          <div className="category-list">
            {data.categories.slice(0, 6).map((c) => (
              <div className="category-row" key={c.name}>
                <div>
                  <span>{c.name}</span>
                  <span>{number(c.count)}</span>
                </div>
                <div className="track">
                  <i
                    style={{
                      width: `${(c.count / Math.max(1, total)) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="chart-empty">
            An open field of possibilities
            <small>
              Category coverage appears as repositories are discovered.
            </small>
          </div>
        )}
      </section>
    </div>
  );
}
const headings = {
  overview: [
    "The open-source pulse",
    "Find the projects gaining traction. Understand the signals behind them.",
  ],
  trending: [
    "Trending repositories",
    "Measured growth, ranked by momentum. Every signal backed by observations.",
  ],
  discover: [
    "Discover what’s next",
    "Explore the CodePulse index. Find emerging tools before everyone else.",
  ],
  watchlist: [
    "Your watchlist",
    "Keep promising projects close. Follow their momentum over time.",
  ],
};
export function Catalog({ mode }: { mode: keyof typeof headings }) {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") || ""),
    [search, setSearch] = useState(q),
    [window, setWindow] = useState<Window>("24h"),
    [category, setCategory] = useState(""),
    [language, setLanguage] = useState(""),
    [sort, setSort] = useState(mode === "discover" ? "newest" : "momentum"),
    [min, setMin] = useState(""),
    [max, setMax] = useState(""),
    [minScore, setMinScore] = useState(""),
    [scoreType, setScoreType] = useState(""),
    [emerging, setEmerging] = useState(false),
    [newOnly, setNewOnly] = useState(false),
    [page, setPage] = useState(1);
  useEffect(() => {
    setQ(searchParams.get("q") || "");
    setSearch(searchParams.get("q") || "");
    setPage(1);
  }, [searchParams]);
  useEffect(() => {
    const id = setTimeout(() => {
      setSearch(q);
      setPage(1);
    }, 250);
    return () => clearTimeout(id);
  }, [q]);
  const params = new URLSearchParams({
    q: search,
    time_window: window,
    sort,
    page: String(page),
    page_size: "15",
  });
  if (category) params.set("category", category);
  if (language) params.set("language", language);
  if (min) params.set("min_stars", min);
  if (max) params.set("max_stars", max);
  if (minScore) params.set("min_score", minScore);
  if (scoreType) params.set("score_type", scoreType);
  if (emerging) params.set("emerging", "true");
  if (newOnly) params.set("new_only", "true");
  const endpoint =
    mode === "watchlist"
      ? "watchlist"
      : mode === "trending"
        ? "trending"
        : mode === "discover"
          ? "discover"
          : "repositories";
  const repos = useQuery({
    queryKey: [
      mode === "watchlist" ? "watchlist" : "repositories",
      endpoint,
      params.toString(),
    ],
    queryFn: () => api<Page>(`/${endpoint}?${params}`),
  });
  const summary = useQuery({
    queryKey: ["summary", window],
    queryFn: () => api<Summary>(`/dashboard/summary?time_window=${window}`),
    enabled: mode === "overview",
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<string[]>("/categories"),
  });
  const languages = useQuery({
    queryKey: ["languages"],
    queryFn: () => api<string[]>("/languages"),
  });
  const resetPage =
    <T,>(setter: (v: T) => void) =>
    (v: T) => {
      setter(v);
      setPage(1);
    };
  return (
    <>
      <div className="breadcrumb">
        <Activity size={13} /> Workspace <ChevronRight size={12} />
        <span>
          {mode === "overview"
            ? "Overview"
            : mode.charAt(0).toUpperCase() + mode.slice(1)}
        </span>
      </div>
      <div className="page-heading">
        <div>
          <div className="eyebrow accent">OPEN-SOURCE INTELLIGENCE</div>
          <h1>{headings[mode][0]}</h1>
          <p>{headings[mode][1]}</p>
        </div>
        <WindowSelect value={window} onChange={resetPage(setWindow)} />
      </div>
      {mode === "overview" &&
        (summary.isPending ? (
          <div className="kpi-grid">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-32" />
            ))}
          </div>
        ) : summary.isError ? (
          <ErrorState error={summary.error} retry={() => summary.refetch()} />
        ) : (
          <Kpis data={summary.data} />
        ))}
      {mode === "overview" && (
        <div className="section-intro">
          <div>
            <span className="live-icon">
              <Activity size={16} />
            </span>
            <h2>On the radar</h2>
            <span className="pill">
              {repos.data?.total ?? "—"} repositories
            </span>
          </div>
          <Link href="/trending">
            View measured trends <ArrowUpRight size={14} />
          </Link>
        </div>
      )}
      {mode === "watchlist" && (
        <div className="info-note">
          <Bookmark size={15} />
          <span>
            Saved to this browser’s anonymous workspace. Clearing browser
            storage creates a new workspace. This is not an authenticated
            account.
          </span>
        </div>
      )}
      <section className="panel catalog-panel">
        <div className="filter-row">
          <div className="filter-search">
            <Search size={15} />
            <input
              aria-label="Search stored repositories"
              placeholder="Filter repositories…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <select
            aria-label="Category"
            value={category}
            onChange={(e) => resetPage(setCategory)(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.data?.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            aria-label="Language"
            value={language}
            onChange={(e) => resetPage(setLanguage)(e.target.value)}
          >
            <option value="">All languages</option>
            {languages.data?.map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
          <div className="sort-select">
            <ArrowDownUp size={13} />
            <select
              aria-label="Sort repositories"
              value={sort}
              onChange={(e) => resetPage(setSort)(e.target.value)}
            >
              <option value="momentum">Score</option>
              <option value="growth">Star velocity</option>
              <option value="stars">Total stars</option>
              <option value="newest">Recently discovered</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>
        <div className="filter-secondary">
          <SlidersHorizontal size={13} />
          <label>
            Stars{" "}
            <input
              aria-label="Minimum stars"
              type="number"
              min="0"
              placeholder="Min"
              value={min}
              onChange={(e) => resetPage(setMin)(e.target.value)}
            />{" "}
            <span>–</span>{" "}
            <input
              aria-label="Maximum stars"
              type="number"
              min="0"
              placeholder="Max"
              value={max}
              onChange={(e) => resetPage(setMax)(e.target.value)}
            />
          </label>
          <label>
            Score ≥{" "}
            <input
              aria-label="Minimum score"
              type="number"
              min="0"
              max="100"
              placeholder="0"
              value={minScore}
              onChange={(e) => resetPage(setMinScore)(e.target.value)}
            />
          </label>
          {mode !== "trending" && (
            <select
              aria-label="Score type"
              value={scoreType}
              onChange={(e) => resetPage(setScoreType)(e.target.value)}
            >
              <option value="">All score types</option>
              <option value="observed_momentum">Observed momentum</option>
              <option value="early_discovery">Discovery heuristic</option>
            </select>
          )}
          <label className="check-filter">
            <input
              type="checkbox"
              checked={emerging}
              onChange={(e) => resetPage(setEmerging)(e.target.checked)}
            />{" "}
            Emerging
          </label>
          <label className="check-filter">
            <input
              type="checkbox"
              checked={newOnly}
              onChange={(e) => resetPage(setNewOnly)(e.target.checked)}
            />{" "}
            New this week
          </label>
        </div>
        {repos.isPending ? (
          <Loading />
        ) : repos.isError ? (
          <ErrorState error={repos.error} retry={() => repos.refetch()} />
        ) : repos.data.items.length ? (
          <RepoTable
            repos={repos.data.items}
            watchlist={mode === "watchlist"}
          />
        ) : (
          <Empty
            title={
              mode === "watchlist"
                ? "A space for your next big find"
                : mode === "trending"
                  ? "Momentum needs a little history"
                  : "Your next discovery starts here"
            }
            description={
              mode === "watchlist"
                ? "Save repositories from Discover to follow them here. Saved projects must also match your active filters."
                : mode === "trending"
                  ? "This feed contains measured momentum only. Browse Discover while the collector builds real history, or adjust your filters."
                  : "No repositories match your filters yet. Connect GitHub in your environment and run discovery to begin."
            }
            settings={mode !== "watchlist"}
          />
        )}
        <div className="pagination">
          <span>
            {repos.data
              ? `${repos.data.total.toLocaleString()} repositories · page ${page} of ${Math.max(1, Math.ceil(repos.data.total / 15))}`
              : "Loading index…"}
          </span>
          <div>
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft size={15} /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!repos.data || page * 15 >= repos.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight size={15} />
            </Button>
          </div>
        </div>
      </section>
      {mode === "overview" && summary.data && (
        <>
          <MarketPanels data={summary.data} />
          <div className="method-note">
            <Clock3 size={17} />
            <div>
              <strong>A signal is only as good as its history.</strong>
              <p>
                CodePulse measures growth from timestamped GitHub observations.
                New discoveries receive a separate heuristic until there’s
                enough history.
              </p>
            </div>
            <Link href="/analytics">
              How scores work <ArrowRight size={14} />
            </Link>
          </div>
        </>
      )}
    </>
  );
}
