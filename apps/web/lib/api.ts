export type Window = "24h" | "7d" | "30d";
export type Score = {
  score: number;
  score_type: "observed_momentum" | "early_discovery";
  scoring_version: string;
  time_window: Window;
  calculated_at: string;
  confidence: number;
  stale: boolean;
  coverage: Coverage;
  feature_breakdown: {
    values: Record<string, number | null>;
    contributions: Record<string, number | null>;
    missing: string[];
  };
  explanation: string[];
};
export type Coverage = {
  sufficient: boolean;
  observation_count: number;
  history_days: number;
  elapsed_days: number | null;
  freshness_hours: number | null;
  reason: string | null;
  start_at: string | null;
  end_at: string | null;
  peer_count?: number;
};
export type Snapshot = {
  observed_at: string;
  stars: number;
  forks: number;
  open_issues: number;
  contributors: number | null;
  commits_7d: number | null;
  collection_source: string;
};
export type Repository = {
  id: number;
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  url: string;
  description: string | null;
  language: string | null;
  topics: string[];
  category: string;
  stars: number;
  forks: number;
  open_issues: number;
  license: string | null;
  default_branch: string;
  size: number | null;
  archived: boolean;
  disabled: boolean;
  contributors: number | null;
  commits_7d: number | null;
  activity_fetched_at: string | null;
  created_at_github: string;
  pushed_at: string | null;
  updated_at_github: string | null;
  discovered_at: string;
  last_fetched_at: string | null;
  tracking_priority: string;
  score: Score | null;
  score_change: number | null;
  sparkline: Snapshot[];
  watchlisted: boolean;
};
export type Page = {
  items: Repository[];
  total: number;
  page: number;
  page_size: number;
  demo: boolean;
};
export type Summary = {
  repositories_tracked: number;
  emerging_repositories: number;
  high_momentum_repositories: number;
  new_discoveries_today: number;
  last_observation_at: string | null;
  categories: { name: string; count: number }[];
  momentum_distribution: { range: string; count: number }[];
  fastest_growing: Repository[];
  recently_discovered: Repository[];
  demo: boolean;
};
export type Status = {
  ingestion: string;
  github_configured: boolean;
  demo: boolean;
  redis: string;
  worker_last_seen: number | null;
  worker_healthy: boolean;
  cooldown_until: number | null;
  quotas: Record<
    string,
    { remaining: number; limit: number; reset: number; observed_at: number }
  >;
  tasks: Record<string, { status: string; at: number; count?: number }>;
  last_discovery: {
    status: string;
    started_at: string;
    completed_at: string | null;
    repositories_found: number;
    error: string | null;
  } | null;
  recent_failures: number;
  cadences_hours: Record<string, number>;
  budgets: Record<string, number>;
};
let memoryWorkspace: string | undefined;
export function workspaceId(): string {
  if (typeof window === "undefined") return "";
  try {
    const saved = localStorage.getItem("codepulse-workspace");
    if (saved && /^[0-9a-f-]{36}$/i.test(saved)) return saved;
    const id = crypto.randomUUID();
    localStorage.setItem("codepulse-workspace", id);
    return id;
  } catch {
    return (memoryWorkspace ??= crypto.randomUUID());
  }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Workspace-Id": workspaceId(),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status}). Check the API connection and filters.`,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export type Forecast = {
  id: number;
  repository_id: number;
  full_name: string;
  language: string | null;
  model_version: string;
  issued_at: string;
  as_of: string;
  target_at: string;
  stars_at_origin: number;
  projected_growth: number;
  baseline_growth: number;
  breakout_threshold: number;
  breakout_ratio: number;
  predicted_breakout: boolean;
  features: Record<string, number>;
  explanation: string[];
  stale: boolean;
  demo: boolean;
  evaluation_status: "pending" | "evaluated" | "unavailable";
  realized_growth: number | null;
  actual_breakout: boolean | null;
  outcome_at: string | null;
};
export type ForecastPage = {
  items: Forecast[];
  total: number;
  page: number;
  page_size: number;
  demo: boolean;
  model_version: string;
};
export type ForecastStatus = {
  status: "ready" | "insufficient_history" | "stale" | "inactive";
  reason: string | null;
  forecast: Forecast | null;
  demo: boolean;
};
export type ForecastValidation = {
  model_version: string;
  demo: boolean;
  evaluated: number;
  pending: number;
  unavailable: number;
  predicted_breakouts: number;
  actual_breakouts: number;
  precision: number | null;
  recall: number | null;
  mean_absolute_error: number | null;
  baseline_mean_absolute_error: number | null;
};
