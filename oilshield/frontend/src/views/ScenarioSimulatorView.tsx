import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FlaskConical, Play, Save, FolderOpen } from "lucide-react";
import {
  getScenarios,
  runScenario,
  saveScenario,
  getSavedScenario,
  ApiError,
} from "../api";
import { Panel, LoadingIndicator, ErrorMessage } from "../components";
import type { ImpactResult, Scenario, ScenarioAssumption } from "../types";

type Overrides = Record<string, number>;

interface MetricLine {
  key: keyof ImpactPointMetrics;
  label: string;
  color: string;
}

interface ImpactPointMetrics {
  refinery_run_rate_pct: number;
  fuel_price_index: number;
  spr_days_of_cover: number;
  gdp_index: number;
}

const METRIC_LINES: MetricLine[] = [
  { key: "refinery_run_rate_pct", label: "Refinery run rate (%)", color: "#0D9488" },
  { key: "fuel_price_index", label: "Fuel price index", color: "#F43F5E" },
  { key: "spr_days_of_cover", label: "SPR days of cover", color: "#10B981" },
  { key: "gdp_index", label: "GDP index", color: "#8B5CF6" },
];

function stepForRange(min: number, max: number): number {
  const span = Math.abs(max - min);
  if (span === 0) return 1;
  if (span >= 100) return 1;
  if (span >= 10) return 0.5;
  if (span >= 1) return 0.1;
  return 0.01;
}

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function initialOverrides(scenario: Scenario): Overrides {
  const out: Overrides = {};
  for (const a of scenario.assumptions) {
    out[a.key] = a.value;
  }
  return out;
}

function adjustableOverrides(
  scenario: Scenario | null,
  overrides: Overrides,
): Overrides {
  if (!scenario) return {};
  const out: Overrides = {};
  for (const a of scenario.assumptions) {
    if (a.adjustable && a.key in overrides) {
      out[a.key] = overrides[a.key];
    }
  }
  return out;
}

export function ScenarioSimulatorView() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string>("");
  const [overrides, setOverrides] = useState<Overrides>({});

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [impact, setImpact] = useState<ImpactResult | null>(null);
  const [assumptionsUsed, setAssumptionsUsed] = useState<ScenarioAssumption[]>([]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  const [loadId, setLoadId] = useState("");
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [savedLoadError, setSavedLoadError] = useState<string | null>(null);

  const selected = useMemo(
    () => scenarios.find((s) => s.id === selectedId) ?? null,
    [scenarios, selectedId],
  );

const loadScenarios = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await getScenarios();
      setScenarios(res.scenarios);
      if (res.scenarios.length > 0) {
        const first = res.scenarios[0];
        setSelectedId(first.id);
        setOverrides(initialOverrides(first));
      }
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load scenarios.";
      setLoadError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadScenarios();
  }, [loadScenarios]);

const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      setImpact(null);
      setAssumptionsUsed([]);
      setRunError(null);
      setSavedId(null);
      setSaveError(null);
      const scenario = scenarios.find((s) => s.id === id);
      if (scenario) setOverrides(initialOverrides(scenario));
    },
    [scenarios],
  );

const handleAssumptionChange = useCallback(
    (assumption: ScenarioAssumption, raw: number) => {
      const next = clamp(raw, assumption.min_value, assumption.max_value);
      setOverrides((prev) => ({ ...prev, [assumption.key]: next }));
    },
    [],
  );

const handleRun = useCallback(async () => {
    if (!selectedId) return;
    setRunning(true);
    setRunError(null);
    try {
      const payload = adjustableOverrides(selected, overrides);
      const res = await runScenario(selectedId, payload);
      setImpact(res.impact);
      setAssumptionsUsed(res.assumptions_used);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to run scenario.";
      setRunError(message);
    } finally {
      setRunning(false);
    }
  }, [selectedId, overrides, selected]);

const handleSave = useCallback(async () => {
    if (!selectedId) return;
    setSaving(true);
    setSaveError(null);
    setSavedId(null);
    try {
      const payload = adjustableOverrides(selected, overrides);
      const res = await saveScenario(selectedId, payload);
      setSavedId(res.id);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to save scenario.";
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  }, [selectedId, overrides, selected]);

const handleLoad = useCallback(async () => {
    const id = loadId.trim();
    if (!id) return;
    setLoadingSaved(true);
    setSavedLoadError(null);
    try {
      const res = await getSavedScenario(id);
      const scenario = res.scenario;
      setScenarios((prev) =>
        prev.some((s) => s.id === scenario.id) ? prev : [...prev, scenario],
      );
      setSelectedId(scenario.id);
      setOverrides(initialOverrides(scenario));
      setImpact(null);
      setAssumptionsUsed([]);
      setRunError(null);
      setSavedId(null);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load saved scenario.";
      setSavedLoadError(message);
    } finally {
      setLoadingSaved(false);
    }
  }, [loadId]);

  return (
    <Panel
      title="Disruption Scenario Simulator"
      subtitle="Tune assumptions and project the downstream impact"
      icon={FlaskConical}
      accent="teal"
      motionDelay={0.13}
      ariaLabel="Disruption Scenario Simulator"
      bodyClassName="space-y-4"
    >
      {loading ? (
        <LoadingIndicator label="Loading scenariosâ€¦" fullHeight />
      ) : loadError ? (
        <ErrorMessage
          module="scenario"
          message={loadError}
          onRetry={() => void loadScenarios()}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-5">
          {/* Left column: picker + assumptions + save/load controls. */}
          <div className="space-y-4 lg:col-span-2">
            {/* Scenario picker (R5.1). */}
            <div>
              <label
                htmlFor="scenario-picker"
                className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500"
              >
                Scenario
              </label>
              <select
                id="scenario-picker"
                value={selectedId}
                onChange={(e) => handleSelect(e.target.value)}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-accent/50"
              >
                {scenarios.length === 0 && <option value="">No scenarios</option>}
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              {selected && (
                <p className="mt-1 text-xs text-slate-500">
                  Corridor: <span className="text-slate-700">{selected.corridor}</span>
                </p>
              )}
            </div>

            {/* Assumptions panel (R5.2, R5.3, R5.4). */}
            {selected && (
              <div className="border-t border-slate-100 pt-4">
                <h3 className="mb-3 text-sm font-semibold text-slate-900">
                  Assumptions
                </h3>
                <ul className="flex flex-col gap-4" aria-label="Scenario assumptions">
                  {selected.assumptions.map((a) => {
                    const value = overrides[a.key] ?? a.value;
                    const step = stepForRange(a.min_value, a.max_value);
                    return (
                      <li key={a.key}>
                        <div className="flex items-center justify-between gap-3">
                          <label
                            htmlFor={`assumption-${a.key}`}
                            className="text-sm text-slate-700"
                          >
                            {a.label}
                            {a.unit && (
                              <span className="ml-1 text-xs text-slate-500">
                                ({a.unit})
                              </span>
                            )}
                          </label>
                          {a.adjustable ? (
                            <input
                              id={`assumption-${a.key}`}
                              type="number"
                              value={value}
                              min={a.min_value}
                              max={a.max_value}
                              step={step}
                              onChange={(e) =>
                                handleAssumptionChange(a, e.target.valueAsNumber)
                              }
                              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-right text-sm text-slate-900 outline-none focus:border-accent/50"
                            />
                          ) : (
                            <span
                              className="w-24 text-right text-sm text-slate-500"
                              aria-label={`${a.label} (read-only)`}
                            >
                              {a.value}
                            </span>
                          )}
                        </div>
                        {a.adjustable ? (
                          <>
                            <input
                              type="range"
                              value={value}
                              min={a.min_value}
                              max={a.max_value}
                              step={step}
                              onChange={(e) =>
                                handleAssumptionChange(a, e.target.valueAsNumber)
                              }
                              aria-label={`${a.label} slider`}
                              className="mt-2 w-full accent-accent"
                            />
                            <div className="mt-0.5 flex justify-between text-[10px] text-slate-500">
                              <span>{a.min_value}</span>
                              <span>{a.max_value}</span>
                            </div>
                          </>
                        ) : (
                          <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                            Fixed
                          </p>
                        )}
                      </li>
                    );
                  })}
                </ul>

                {/* Run action. */}
                <button
                  type="button"
                  onClick={() => void handleRun()}
                  disabled={running || !selectedId}
                  className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Play className="h-4 w-4" aria-hidden />
                  {running ? "Runningâ€¦" : "Run scenario"}
                </button>

                {/* Save / Load controls (R7.1, R7.2, R7.3). */}
                <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                  <div>
                    <button
                      type="button"
                      onClick={() => void handleSave()}
                      disabled={saving || !selectedId}
                      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" aria-hidden />
                      {saving ? "Savingâ€¦" : "Save scenario"}
                    </button>
                    {savedId && (
                      <p className="mt-1.5 text-xs text-slate-500">
                        Saved as{" "}
                        <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-accent">
                          {savedId}
                        </code>
                      </p>
                    )}
                    {saveError && (
                      <div className="mt-2">
                        <ErrorMessage module="scenario" message={saveError} />
                      </div>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="load-id"
                      className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500"
                    >
                      Load saved scenario
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        id="load-id"
                        type="text"
                        value={loadId}
                        onChange={(e) => setLoadId(e.target.value)}
                        placeholder="saved scenario id"
                        className="min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 outline-none focus:border-accent/50"
                      />
                      <button
                        type="button"
                        onClick={() => void handleLoad()}
                        disabled={loadingSaved || !loadId.trim()}
                        className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <FolderOpen className="h-3.5 w-3.5" aria-hidden />
                        {loadingSaved ? "Loadingâ€¦" : "Load"}
                      </button>
                    </div>
                    {savedLoadError && (
                      <div className="mt-2">
                        <ErrorMessage module="scenario" message={savedLoadError} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right column: run error / timeline / assumptions used. */}
          <div className="space-y-4 lg:col-span-3">
            {runError && (
              <ErrorMessage
                module="scenario"
                message={runError}
                onRetry={() => void handleRun()}
              />
            )}

            {running ? (
              <LoadingIndicator label="Projecting impactâ€¦" fullHeight />
            ) : impact ? (
              <>
                {/* Recharts timeline of projected values (R6.6). */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-slate-900">
                    Projected impact timeline
                  </h3>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={impact.timeline}
                        margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
                      >
                        <defs>
                          {METRIC_LINES.map((m) => (
                            <linearGradient
                              key={m.key}
                              id={`area-grad-${m.key}`}
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop offset="0%" stopColor={m.color} stopOpacity={0.35} />
                              <stop offset="95%" stopColor={m.color} stopOpacity={0} />
                            </linearGradient>
                          ))}
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis
                          dataKey="day"
                          stroke="#64748B"
                          tick={{ fontSize: 11, fill: "#64748B" }}
                          label={{
                            value: "Day",
                            position: "insideBottom",
                            offset: -2,
                            fill: "#64748B",
                            fontSize: 11,
                          }}
                        />
                        <YAxis stroke="#64748B" tick={{ fontSize: 11, fill: "#64748B" }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            border: "1px solid #E2E8F0",
                            borderRadius: 8,
                            fontSize: 12,
                          }}
                          labelStyle={{ color: "#0F172A" }}
                          labelFormatter={(d) => `Day ${d}`}
                        />
                        <Legend wrapperStyle={{ fontSize: 11, color: "#475569" }} />
                        {METRIC_LINES.map((m) => (
                          <Area
                            key={m.key}
                            type="monotone"
                            dataKey={m.key}
                            name={m.label}
                            stroke={m.color}
                            strokeWidth={2}
                            fill={`url(#area-grad-${m.key})`}
                            dot={false}
                            activeDot={{ r: 3 }}
                          />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Assumptions used, as returned by the backend (R6.2). */}
                <div className="border-t border-slate-100 pt-4">
                  <h3 className="mb-3 text-sm font-semibold text-slate-900">
                    Assumptions used
                  </h3>
                  {assumptionsUsed.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      No assumptions reported.
                    </p>
                  ) : (
                    <ul
                      className="grid gap-x-8 sm:grid-cols-2"
                      aria-label="Assumptions used"
                    >
                      {assumptionsUsed.map((a) => (
                        <li
                          key={a.key}
                          className="flex items-center justify-between gap-3 border-b border-slate-100 py-2"
                        >
                          <span className="min-w-0 truncate text-sm text-slate-600">
                            {a.label}
                          </span>
                          <span className="whitespace-nowrap font-mono text-sm text-slate-900">
                            {a.value}
                            {a.unit && (
                              <span className="ml-1 text-xs text-slate-500">
                                {a.unit}
                              </span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            ) : (
              <div className="flex h-full min-h-[200px] items-center justify-center p-6 text-center">
                <p className="text-sm text-slate-500">
                  Pick a scenario, adjust its assumptions, and run to project the
                  downstream impact.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}

export default ScenarioSimulatorView;
