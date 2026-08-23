import type { RiskBand } from "../types";

export const BAND_HEX: Record<RiskBand, string> = {
  low: "#10B981", // emerald-500
  elevated: "#F59E0B", // amber-500 (darkened for contrast on white)
  high: "#F43F5E", // rose-500
};

export function bandColor(band: RiskBand): string {
  return BAND_HEX[band];
}

export const BAND_BADGE_CLASSES: Record<RiskBand, string> = {
  low: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  elevated: "bg-amber-50 text-amber-700 border border-amber-200",
  high: "bg-rose-50 text-rose-700 border border-rose-200",
};

export function bandBadgeClasses(band: RiskBand): string {
  return BAND_BADGE_CLASSES[band];
}

export function bandLabel(band: RiskBand): string {
  return band.charAt(0).toUpperCase() + band.slice(1);
}

export function formatLatencyMs(ms: number): string {
  if (!Number.isFinite(ms)) return "â€”";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function formatPercent(value: number, fractionDigits = 1): string {
  if (!Number.isFinite(value)) return "â€”";
  return `${value.toFixed(fractionDigits)}%`;
}

export function formatFraction(value: number, fractionDigits = 0): string {
  if (!Number.isFinite(value)) return "â€”";
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

const USD_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatUsd(value: number): string {
  if (!Number.isFinite(value)) return "â€”";
  return USD_FORMATTER.format(value);
}

const DATETIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return DATETIME_FORMATTER.format(date);
}

export function formatScore(score: number): string {
  if (!Number.isFinite(score)) return "â€”";
  return String(Math.round(score));
}
