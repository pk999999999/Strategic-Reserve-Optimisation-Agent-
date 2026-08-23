import { Radio, TrendingDown } from "lucide-react";
import type { ImpactPoint, RiskBand, Signal } from "../types";
import { formatDateTime } from "../lib";
import { StatusBadge } from "./StatusBadge";

export type TimelineItemKind = "signal" | "projection";

export interface TimelineItem {
  id: string;
  kind: TimelineItemKind;
  
  timestampMs: number;
  
  label: string;
  title: string;
  detail?: string;
  
  band?: RiskBand;
}

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function parseMs(iso: string): number | null {
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}

export interface BuildTimelineOptions {
  
  projectionStart?: Date | string;
}

export function buildTimeline(
  signals: Signal[],
  projectionPoints: ImpactPoint[],
  options: BuildTimelineOptions = {},
): TimelineItem[] {
  const signalItems: TimelineItem[] = signals.map((s, i) => {
    const ms = parseMs(s.timestamp);
    return {
      id: `signal-${s.id ?? i}`,
      kind: "signal" as const,
      timestampMs: ms ?? 0,
      label: formatDateTime(s.timestamp),
      title: s.target ? `${s.target}` : "Signal",
      detail: s.text_summary,
    };
  });

  let anchorMs: number;
  if (options.projectionStart !== undefined) {
    const provided =
      options.projectionStart instanceof Date
        ? options.projectionStart.getTime()
        : parseMs(options.projectionStart);
    anchorMs = provided ?? Date.now();
  } else if (signalItems.length > 0) {
    anchorMs = Math.max(...signalItems.map((s) => s.timestampMs));
  } else {
    anchorMs = Date.now();
  }

  const projectionItems: TimelineItem[] = projectionPoints.map((p, i) => {
    const ms = anchorMs + p.day * MS_PER_DAY;
    return {
      id: `projection-day-${p.day}-${i}`,
      kind: "projection" as const,
      timestampMs: ms,
      label: `Day ${p.day}`,
      title: `Projected impact â€” day ${p.day}`,
      detail: `Run rate ${p.refinery_run_rate_pct.toFixed(1)}% Â· Price idx ${p.fuel_price_index.toFixed(
        1,
      )} Â· SPR ${p.spr_days_of_cover.toFixed(1)}d`,
    };
  });

  return [...signalItems, ...projectionItems].sort((a, b) => a.timestampMs - b.timestampMs);
}

export interface TimelineProps {
  
  signals?: Signal[];
  
  projectionPoints?: ImpactPoint[];
  
  projectionStart?: Date | string;
  
  items?: TimelineItem[];
  
  emptyLabel?: string;
  className?: string;
}

const KIND_ICON = {
  signal: Radio,
  projection: TrendingDown,
} as const;

export function Timeline({
  signals = [],
  projectionPoints = [],
  projectionStart,
  items,
  emptyLabel = "No timeline events yet.",
  className,
}: TimelineProps) {
  const resolved = items ?? buildTimeline(signals, projectionPoints, { projectionStart });

  if (resolved.length === 0) {
    return <p className={`text-xs text-slate-500 ${className ?? ""}`}>{emptyLabel}</p>;
  }

  return (
    <ol className={`relative space-y-4 border-l border-slate-200 pl-5 ${className ?? ""}`}>
      {resolved.map((item) => {
        const Icon = KIND_ICON[item.kind];
        return (
          <li key={item.id} className="relative">
            <span
              aria-hidden
              className="absolute -left-[27px] flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-accent"
            >
              <Icon className="h-3 w-3" />
            </span>
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-slate-800">{item.title}</p>
              <div className="flex items-center gap-2">
                {item.band && <StatusBadge band={item.band} size="sm" />}
                <time className="whitespace-nowrap font-mono text-[11px] text-slate-500">
                  {item.label}
                </time>
              </div>
            </div>
            {item.detail && <p className="mt-0.5 text-xs text-slate-500">{item.detail}</p>}
          </li>
        );
      })}
    </ol>
  );
}

export default Timeline;
