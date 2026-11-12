import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
export function number(value: number | null | undefined) {
  return value == null
    ? "—"
    : new Intl.NumberFormat("en", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value);
}
export function signed(value: number | null | undefined, digits = 0) {
  return value == null
    ? "—"
    : `${value > 0 ? "+" : ""}${value.toLocaleString("en", { maximumFractionDigits: digits })}`;
}
export function date(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not observed yet";
}
export function freshness(value: string | null | undefined) {
  if (!value) return "Awaiting first observation";
  const h = Math.max(0, (Date.now() - new Date(value).getTime()) / 3600000);
  return h < 1
    ? "Observed less than an hour ago"
    : `Observed ${Math.floor(h)}h ago`;
}
