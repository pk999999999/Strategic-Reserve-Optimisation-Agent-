import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Radar } from "lucide-react";
import {
  getRiskScores,
  getTargetSignals,
  refreshSignals,
  ApiError,
} from "../api";
import {
  MapPanel,
  StatusBadge,
  Panel,
  LoadingIndicator,
  ErrorMessage,
  type CorridorPolyline,
} from "../components";
import { formatDateTime, bandColor } from "../lib";
import type { RiskScore, Signal } from "../types";

const CORRIDOR_GEOMETRY: Record<string, [number, number][]> = {
  "Strait of Hormuz": [
    [26.9667, 56.5333],
    [26.7333, 56.4667],
    [26.5665, 56.2497],
    [26.3, 56.1],
    [25.9667, 56.9],
  ],
  "Red Sea": [
    [12.5833, 43.3333],
    [15.5, 41.8],
    [19.5, 38.5],
    [24.5, 35.5],
    [27.9, 33.7],
    [29.9668, 32.5498],
  ],
  "Cape of Good Hope": [
    [4.5, 6.5],
    [-6.0, 11.0],
    [-20.0, 14.0],
    [-34.3587, 18.4736],
    [-33.0, 27.0],
    [-20.0, 40.0],
    [-6.0, 52.0],
  ],
};

function rankByScore(scores: RiskScore[]): RiskScore[] {
  return [...scores].sort((a, b) => b.score - a.score);
}

function toCorridorPolylines(scores: RiskScore[]): CorridorPolyline[] {
  return scores
    .filter((s) => s.target_type === "corridor" && CORRIDOR_GEOMETRY[s.target])
    .map((s) => ({
      id: s.target,
      name: s.target,
      positions: CORRIDOR_GEOMETRY[s.target],
      band: s.band,
    }));
}

interface DetailState {
  target: string;
  loading: boolean;
  signals: Signal[];
  error: string | null;
}

export function RiskRadarView() {
  const [scores, setScores] = useState<RiskScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [detail, setDetail] = useState<DetailState | null>(null);

const loadScores = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getRiskScores();
      setScores(res.risk_scores);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load risk scores.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadScores();
  }, [loadScores]);

const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      await refreshSignals();
      await loadScores();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to refresh signals.";
      setError(message);
    } finally {
      setRefreshing(false);
    }
  }, [loadScores]);

const handleSelectTarget = useCallback(async (target: string) => {
    setDetail({ target, loading: true, signals: [], error: null });
    try {
      const res = await getTargetSignals(target);
      setDetail({ target, loading: false, signals: res.signals, error: null });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load contributing signals.";
      setDetail({ target, loading: false, signals: [], error: message });
    }
  }, []);

  const ranked = useMemo(() => rankByScore(scores), [scores]);
  const corridors = useMemo(() => toCorridorPolylines(scores), [scores]);

  const refreshButton = (
    <button
      type="button"
      onClick={() => void handleRefresh()}
      disabled={refreshing || loading}
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <RefreshCw
        className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
        aria-hidden
      />
      {refreshing ? "Refreshingâ€¦" : "Refresh"}
    </button>
  );

  return (
    <Panel
      title="Live Risk Radar"
      subtitle="Corridor & supplier-country risk by band"
      icon={Radar}
      accent="rose"
      motionDelay={0.05}
      actions={refreshButton}
      ariaLabel="Live Risk Radar"
      bodyClassName="space-y-4"
    >
      {loading ? (
        <LoadingIndicator label="Scoring corridorsâ€¦" fullHeight />
      ) : error ? (
        <ErrorMessage module="risk" message={error} onRetry={() => void loadScores()} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-5">
          {/* Map with band-colored corridor polylines (R4.1). */}
          <div className="lg:col-span-3">
            <MapPanel corridors={corridors} height={400} />
          </div>

          {/* Ranked list of corridors + countries, highest-to-lowest (R4.2). */}
          <div className="lg:col-span-2">
            {ranked.length === 0 ? (
              <p className="text-sm text-slate-500">No risk scores available.</p>
            ) : (
              <ul
                className="divide-y divide-slate-100"
                aria-label="Ranked risk targets"
              >
                {ranked.map((s) => {
                  const isActive = detail?.target === s.target;
                  return (
                    <li key={`${s.target_type}:${s.target}`}>
                      <button
                        type="button"
                        onClick={() => void handleSelectTarget(s.target)}
                        aria-pressed={isActive}
                        style={{ borderLeftColor: bandColor(s.band) }}
                        className={`flex w-full items-center justify-between gap-3 border-l-2 py-2.5 pl-3 pr-1 text-left transition hover:bg-slate-50 ${
                          isActive ? "bg-slate-50" : ""
                        }`}
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-slate-900">
                            {s.target}
                          </span>
                          <span className="text-[10px] uppercase tracking-wide text-slate-500">
                            {s.target_type}
                          </span>
                          {/* Slim score bar colored by band. */}
                          <span className="mt-1.5 block h-1 w-full overflow-hidden rounded-full bg-slate-100">
                            <span
                              className="block h-full rounded-full"
                              style={{
                                width: `${Math.max(0, Math.min(100, s.score))}%`,
                                backgroundColor: bandColor(s.band),
                              }}
                            />
                          </span>
                        </span>
                        <StatusBadge band={s.band} score={s.score} size="sm" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Detail drawer: contributing signals with source + timestamp (R4.3). */}
      {detail && (
        <div className="border-t border-slate-100 pt-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-900">
              Contributing signals â€” {detail.target}
            </h3>
            <button
              type="button"
              onClick={() => setDetail(null)}
              className="rounded-md px-2 py-0.5 text-xs text-slate-600 transition hover:bg-slate-50"
            >
              Close
            </button>
          </div>

          {detail.loading ? (
            <LoadingIndicator label="Loading contributing signalsâ€¦" />
          ) : detail.error ? (
            <ErrorMessage
              module="risk"
              message={detail.error}
              onRetry={() => void handleSelectTarget(detail.target)}
            />
          ) : detail.signals.length === 0 ? (
            <p className="text-sm text-slate-500">
              No contributing signals for this target.
            </p>
          ) : (
            <ul
              className="divide-y divide-slate-100"
              aria-label="Contributing signals"
            >
              {detail.signals.map((sig) => (
                <li key={sig.id} className="py-2.5">
                  <p className="text-sm text-slate-700">{sig.text_summary}</p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span className="font-medium text-slate-600">{sig.source}</span>
                    <span aria-hidden>â€¢</span>
                    <time dateTime={sig.timestamp}>{formatDateTime(sig.timestamp)}</time>
                    <span aria-hidden>â€¢</span>
                    <span className="font-mono">severity {sig.raw_severity}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Panel>
  );
}

export default RiskRadarView;
