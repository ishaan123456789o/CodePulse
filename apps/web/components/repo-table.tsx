"use client";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Check, ChevronRight, GitFork, Star } from "lucide-react";
import { api, Repository, Score } from "@/lib/api";
import { number, signed } from "@/lib/utils";
import { Button } from "./ui/button";
import { Sparkline } from "./charts";
export function WatchButton({
  repo,
  labeled = false,
}: {
  repo: Repository;
  labeled?: boolean;
}) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      api(repo.watchlisted ? `/watchlist/${repo.id}` : "/watchlist", {
        method: repo.watchlisted ? "DELETE" : "POST",
        ...(repo.watchlisted
          ? {}
          : { body: JSON.stringify({ repository_id: repo.id }) }),
      }),
    onSuccess: () =>
      client.invalidateQueries({
        predicate: (q) =>
          ["repositories", "repository", "watchlist"].includes(
            String(q.queryKey[0]),
          ),
      }),
  });
  return (
    <div className="watch-action">
      <Button
        variant={repo.watchlisted ? "default" : "outline"}
        size={labeled ? "default" : "icon"}
        aria-label={`${repo.watchlisted ? "Remove" : "Add"} ${repo.full_name} ${repo.watchlisted ? "from" : "to"} watchlist`}
        aria-pressed={repo.watchlisted}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {repo.watchlisted ? <Check size={15} /> : <Bookmark size={15} />}{" "}
        {labeled && (repo.watchlisted ? "Watching" : "Add to watchlist")}
      </Button>
      {mutation.isError && (
        <span role="alert" className="mutation-error">
          {mutation.error.message}
        </span>
      )}
    </div>
  );
}
export function ScoreBadge({ score }: { score: Score | null }) {
  return score ? (
    <div
      className={`score-cell ${score.score_type === "early_discovery" ? "early" : ""}`}
    >
      <span className="score-number">
        {score.score.toFixed(0)}
        <span>/100</span>
      </span>
      <span className="score-label">
        {score.stale
          ? "Stale score"
          : score.score_type === "early_discovery"
            ? "Discovery heuristic"
            : "Observed momentum"}
      </span>
    </div>
  ) : (
    <span className="muted text-xs">Awaiting score</span>
  );
}
export function RepoTable({
  repos,
  watchlist = false,
}: {
  repos: Repository[];
  watchlist?: boolean;
}) {
  return (
    <div
      className="table-scroll"
      role="region"
      aria-label="Repository results"
      tabIndex={0}
    >
      <table className="repo-table">
        <thead>
          <tr>
            <th>Repository</th>
            <th>Category / language</th>
            <th>Stars</th>
            <th>Growth</th>
            <th>Score</th>
            <th>{watchlist ? "Score change" : "Recent observations"}</th>
            <th>
              <span className="sr-only">Watchlist action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {repos.map((repo) => {
            const values = repo.score?.feature_breakdown.values;
            const observed =
              repo.score?.score_type === "observed_momentum" &&
              !repo.score.stale;
            return (
              <tr key={repo.id}>
                <td className="repo-name-cell">
                  <Link href={`/repos/${repo.id}`} className="repo-name">
                    <span className="repo-avatar">
                      {repo.owner.slice(0, 2).toUpperCase()}
                    </span>
                    <span>
                      <span className="repo-owner">{repo.owner} / </span>
                      {repo.name}
                    </span>
                    <ChevronRight size={14} />
                  </Link>
                  <p className="repo-description">
                    {repo.description || "No description provided."}
                  </p>
                </td>
                <td>
                  <span className="category-label">{repo.category}</span>
                  <span className="language">
                    <i />
                    {repo.language || "Unspecified"}
                  </span>
                </td>
                <td>
                  <span className="metric-inline">
                    <Star size={13} />
                    {number(repo.stars)}
                  </span>
                  <small className="forks">
                    <GitFork size={11} />
                    {number(repo.forks)}
                  </small>
                </td>
                <td>
                  <span
                    className={
                      observed && (values?.star_growth ?? 0) > 0
                        ? "positive"
                        : "muted"
                    }
                  >
                    {observed ? signed(values?.star_growth) : "—"}
                  </span>
                  <small className="muted block">
                    {observed
                      ? `${signed((values?.relative_growth ?? 0) * 100, 1)}% observed`
                      : "Building history"}
                  </small>
                </td>
                <td>
                  <ScoreBadge score={repo.score} />
                </td>
                <td>
                  {watchlist ? (
                    <span>
                      {signed(repo.score_change, 1)}
                      <small className="muted block">
                        points · last calculation
                      </small>
                    </span>
                  ) : (
                    <Sparkline points={repo.sparkline} />
                  )}
                </td>
                <td>
                  <WatchButton repo={repo} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
