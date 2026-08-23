import type {
  ImpactResult,
  PipelineResult,
  ProcurementOption,
  RiskScore,
  Scenario,
  ScenarioAssumption,
  Signal,
} from "../types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

interface ErrorEnvelope {
  error?: {
    module?: string;
    message?: string;
    code?: string;
  };
}

export class ApiError extends Error {
  readonly module: string;
  readonly status?: number;
  readonly code?: string;

  constructor(params: { module: string; message: string; status?: number; code?: string }) {
    super(params.message);
    this.name = "ApiError";
    this.module = params.module;
    this.status = params.status;
    this.code = params.code;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export interface NormalizedError {
  module: string;
  message: string;
}

function url(path: string): string {
  return `${API_BASE}${path}`;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const { method = "GET", body } = options;

  let response: Response;
  try {
    response = await fetch(url(path), {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError({
      module: "network",
      message: err instanceof Error ? err.message : "Network request failed",
    });
  }

  if (!response.ok) {
    throw await normalizeErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError({
      module: "network",
      message: "Failed to parse response body as JSON",
      status: response.status,
    });
  }
}

async function normalizeErrorResponse(response: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope | null = null;
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    envelope = null;
  }

  const err = envelope?.error;
  return new ApiError({
    module: err?.module ?? "api",
    message: err?.message ?? `Request failed with status ${response.status}`,
    status: response.status,
    code: err?.code,
  });
}

export interface RefreshSignalsResponse {
  signals: Signal[];
  data_source_modes: Record<string, string>;
}

export interface RiskScoresResponse {
  risk_scores: RiskScore[];
  data_source_modes: Record<string, string>;
}

export interface TargetSignalsResponse {
  target: string;
  signals: Signal[];
  data_source_modes: Record<string, string>;
}

export interface ScenariosResponse {
  scenarios: Scenario[];
}

export interface RunScenarioResponse {
  impact: ImpactResult;
  assumptions_used: ScenarioAssumption[];
}

export interface SaveScenarioResponse {
  id: string;
}

export interface SavedScenarioResponse {
  scenario: Scenario;
}

export interface RecommendResponse {
  recommendations: ProcurementOption[];
}

export type AssumptionOverrides = Record<string, number>;

export function refreshSignals(): Promise<RefreshSignalsResponse> {
  return request<RefreshSignalsResponse>("/signals/refresh", { method: "POST" });
}

export function getRiskScores(): Promise<RiskScoresResponse> {
  return request<RiskScoresResponse>("/risk/scores");
}

export function getTargetSignals(target: string): Promise<TargetSignalsResponse> {
  return request<TargetSignalsResponse>(`/risk/${encodeURIComponent(target)}/signals`);
}

export function getScenarios(): Promise<ScenariosResponse> {
  return request<ScenariosResponse>("/scenarios");
}

export function runScenario(
  id: string,
  assumptions?: AssumptionOverrides,
): Promise<RunScenarioResponse> {
  return request<RunScenarioResponse>(`/scenarios/${encodeURIComponent(id)}/run`, {
    method: "POST",
    body: { assumptions },
  });
}

export function saveScenario(
  id: string,
  assumptions?: AssumptionOverrides,
): Promise<SaveScenarioResponse> {
  return request<SaveScenarioResponse>("/scenarios/save", {
    method: "POST",
    body: { id, assumptions },
  });
}

export function getSavedScenario(id: string): Promise<SavedScenarioResponse> {
  return request<SavedScenarioResponse>(`/scenarios/saved/${encodeURIComponent(id)}`);
}

export function recommendProcurement(): Promise<RecommendResponse> {
  return request<RecommendResponse>("/procurement/recommend", { method: "POST" });
}

export function runPipeline(scenarioId?: string): Promise<PipelineResult> {
  return request<PipelineResult>("/pipeline/run", {
    method: "POST",
    body: { scenario_id: scenarioId },
  });
}
