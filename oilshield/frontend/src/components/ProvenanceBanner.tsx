import { Database, Wifi } from "lucide-react";
import type { DataSourceMode } from "../types";

export interface ProvenanceBannerProps {
  
  mode?: DataSourceMode;
  
  modes?: Record<string, string>;
  className?: string;
}

export function deriveOverallMode(modes: Record<string, string>): DataSourceMode {
  const values = Object.values(modes);
  if (values.length === 0) return "simulated";
  return values.every((m) => m === "live") ? "live" : "simulated";
}

export function ProvenanceBanner({ mode, modes, className }: ProvenanceBannerProps) {
  const overall: DataSourceMode = mode ?? (modes ? deriveOverallMode(modes) : "simulated");
  const isLive = overall === "live";
  const Icon = isLive ? Wifi : Database;

  const labelTone = isLive ? "text-emerald-300" : "text-amber-300";

  return (
    <div
      role="status"
      className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-white/10 bg-[#0F2A4A] px-4 py-2 text-xs text-slate-100 ${className ?? ""}`}
    >
      <span className={`flex items-center gap-2 font-semibold uppercase tracking-wide ${labelTone}`}>
        <Icon className="h-4 w-4" aria-hidden />
        {isLive ? "Live data" : "Simulated data"}
      </span>
      <span className="text-slate-300">
        {isLive
          ? "Showing signals from live feeds."
          : "Showing bundled simulated data â€” external feeds unavailable or disabled."}
      </span>
      {modes && Object.keys(modes).length > 0 && (
        <span className="ml-auto font-mono text-[10px] text-slate-400">
          {Object.entries(modes).map(([source, m], index) => (
            <span key={source}>
              {index > 0 && <span className="text-slate-600"> Â· </span>}
              <span className="text-slate-300">{source}</span>
              <span className="text-slate-500">: </span>
              <span className={m === "live" ? "text-emerald-300" : "text-amber-300"}>{m}</span>
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

export default ProvenanceBanner;
