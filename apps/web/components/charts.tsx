"use client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Snapshot } from "@/lib/api";
const tooltip = {
  backgroundColor: "#171c20",
  border: "1px solid #30383e",
  borderRadius: 8,
  color: "#e4e9e7",
  fontSize: 12,
};
export function HistoryChart({
  points,
  metric = "stars",
}: {
  points: Snapshot[];
  metric?: "stars" | "forks";
}) {
  if (points.length < 2)
    return (
      <div className="chart-empty">
        {points.length === 1
          ? "Baseline recorded. The next observation will start the trend."
          : "No observations in this window yet."}
        <small>Charts appear only when real observations are available.</small>
      </div>
    );
  return (
    <div
      className="history-chart"
      role="img"
      aria-label={`${metric} observations over time`}
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <AreaChart
          data={points.map((p) => ({
            ...p,
            time: new Date(p.observed_at).getTime(),
          }))}
          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id={`fill-${metric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ad9a0" stopOpacity={0.18} />
              <stop offset="100%" stopColor="#4ad9a0" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="#252c30"
            strokeDasharray="3 4"
            vertical={false}
          />
          <XAxis
            dataKey="time"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v) =>
              new Date(v).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })
            }
            stroke="#728079"
            tickLine={false}
            axisLine={false}
            minTickGap={45}
            fontSize={11}
          />
          <YAxis
            domain={["auto", "auto"]}
            stroke="#728079"
            tickLine={false}
            axisLine={false}
            width={48}
            fontSize={11}
          />
          <Tooltip
            contentStyle={tooltip}
            labelFormatter={(v) => new Date(Number(v)).toLocaleString()}
          />
          <Area
            type="linear"
            dataKey={metric}
            stroke="#4ad9a0"
            strokeWidth={2}
            fill={`url(#fill-${metric})`}
            dot={points.length < 15}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
export function Sparkline({ points }: { points: Snapshot[] }) {
  if (points.length < 2)
    return <span className="muted text-xs">Collecting</span>;
  const values = points.map((p) => p.stars),
    min = Math.min(...values),
    max = Math.max(...values);
  const first = new Date(points[0].observed_at).getTime(),
    elapsed = new Date(points.at(-1)!.observed_at).getTime() - first;
  const coordinates = points
    .map(
      (p) =>
        `${((new Date(p.observed_at).getTime() - first) / Math.max(1, elapsed)) * 90 + 2},${28 - ((p.stars - min) / Math.max(1, max - min)) * 24}`,
    )
    .join(" ");
  return (
    <svg
      width="96"
      height="34"
      viewBox="0 0 96 34"
      role="img"
      aria-label={`Stars from ${values[0]} to ${values.at(-1)}`}
    >
      <polyline
        points={coordinates}
        fill="none"
        stroke={values.at(-1)! >= values[0] ? "#4ad9a0" : "#e39487"}
        strokeWidth="1.7"
      />
    </svg>
  );
}
export function Distribution({
  data,
}: {
  data: { range: string; count: number }[];
}) {
  return (
    <div
      className="distribution-chart"
      role="img"
      aria-label="Distribution of measured momentum scores"
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={data}>
          <CartesianGrid vertical={false} stroke="#252c30" />
          <XAxis
            dataKey="range"
            stroke="#728079"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            allowDecimals={false}
            stroke="#728079"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={24}
          />
          <Tooltip contentStyle={tooltip} cursor={{ fill: "#ffffff05" }} />
          <Bar
            isAnimationActive={false}
            dataKey="count"
            name="Repositories"
            fill="#43bb8d"
            radius={[3, 3, 0, 0]}
            maxBarSize={48}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
