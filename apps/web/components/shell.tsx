"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Bookmark,
  Compass,
  Github,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  TrendingUp,
  Telescope,
  X,
} from "lucide-react";
import { useState } from "react";
import { api, Status, Summary } from "@/lib/api";
import { freshness } from "@/lib/utils";
import { Button } from "./ui/button";
const links = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/trending", label: "Trending", icon: TrendingUp },
  { href: "/forecast", label: "Forecast", icon: Telescope },
  { href: "/discover", label: "Discover", icon: Compass },
  { href: "/watchlist", label: "Watchlist", icon: Bookmark },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname(),
    router = useRouter();
  const [open, setOpen] = useState(false),
    [search, setSearch] = useState("");
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => api<Status>("/system/status"),
    refetchInterval: 60000,
  });
  const summary = useQuery({
    queryKey: ["summary", "24h"],
    queryFn: () => api<Summary>("/dashboard/summary?time_window=24h"),
  });
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      {open && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        className={`sidebar ${open ? "open" : ""}`}
        aria-label="Main navigation"
      >
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">
            <Activity size={22} />
          </span>
          codepulse<span className="version">BETA</span>
        </Link>
        <div className="workspace">
          <span className="workspace-avatar">P</span>
          <div>
            Personal workspace<small>Open-source intelligence</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav>
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={path === href ? "page" : undefined}
              className={`nav-link ${path === href ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              <Icon size={17} />
              {label}
              {href === "/trending" && (
                <span className="nav-live">
                  {status.data?.ingestion === "active" ? "LIVE" : "INDEX"}
                </span>
              )}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="collector-card">
            <span
              className={`status-dot ${status.data?.ingestion === "active" ? "good" : ""}`}
            />
            <strong>
              {status.data?.demo
                ? "Demo environment"
                : status.data?.ingestion === "active"
                  ? "Collector connected"
                  : "Collector status"}
            </strong>
            <p>
              {status.data?.github_configured
                ? "Real observations. Transparent scores."
                : "Connect GitHub to start discovering emerging projects."}
            </p>
            <Link href="/settings">
              View configuration <ArrowUpRight size={13} />
            </Link>
          </div>
          <a
            className="source-link"
            href="https://github.com/ishaan123456789o/CodePulse"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={16} /> View source <ArrowUpRight size={14} />
          </a>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <Button
            variant="ghost"
            size="icon"
            className="mobile-menu"
            aria-expanded={open}
            aria-label={open ? "Close navigation" : "Open navigation"}
            onClick={() => setOpen(!open)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </Button>
          <form
            className="global-search"
            onSubmit={(e) => {
              e.preventDefault();
              router.push(`/discover?q=${encodeURIComponent(search)}`);
            }}
          >
            <Search size={16} />
            <input
              aria-label="Search CodePulse index"
              placeholder="Search the CodePulse index…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <kbd>↵</kbd>
          </form>
          <div className="topbar-status">
            <span className="last-updated">
              {freshness(summary.data?.last_observation_at)}
            </span>
            <Link href="/settings" className="status-pill">
              <span
                className={`status-dot ${status.data?.ingestion === "active" ? "good" : ""}`}
              />
              {status.isError
                ? "API offline"
                : status.data
                  ? `GitHub · ${status.data.ingestion.replaceAll("_", " ")}`
                  : "Connecting"}
            </Link>
          </div>
        </header>
        {status.data?.demo && (
          <div className="demo-banner">
            DEMO MODE — all repositories and metrics in this environment are
            synthetic fixtures, not live GitHub data.
          </div>
        )}
        <main id="main" className="main-content">
          {children}
        </main>
        <footer className="footer">
          <span>
            CodePulse <span className="muted">/</span> Open-source signals, in
            focus.
          </span>
          <span>Measured momentum. Experimental forecasts.</span>
        </footer>
      </div>
    </div>
  );
}
