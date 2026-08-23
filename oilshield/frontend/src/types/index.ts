
export type TargetType = "corridor" | "country";

export type RiskBand = "low" | "elevated" | "high";

export type DataSourceMode = "live" | "simulated";

export interface RawSignal {
  source: string;
  
  timestamp: string;
  text: string;
  
  raw_severity: number;
  
  hinted_target: string | null;
}

export interface Signal {
  id: string;
  source: string;
  
  timestamp: string;
  text_summary: string;
  
  target: string;
  target_type: TargetType;
  
  raw_severity: number;
  data_source_mode: DataSourceMode;
}

export interface ExtractedSignal {
  signal_id: string;
  
  source: string;
  
  timestamp: string;
  
  target: string | null;
  target_type: TargetType | null;
  
  risk_category: string;
  
  severity: number;
  
  classified: boolean;
}

export interface RiskScore {
  target: string;
  target_type: TargetType;
  
  score: number;
  
  band: RiskBand;
  
  contributing_signal_ids: string[];
}

export interface ScenarioAssumption {
  
  key: string;
  label: string;
  value: number;
  min_value: number;
  max_value: number;
  adjustable: boolean;
  
  unit: string;
}

export interface Scenario {
  id: string;
  
  name: string;
  corridor: string;
  assumptions: ScenarioAssumption[];
}

export interface ImpactPoint {
  day: number;
  refinery_run_rate_pct: number;
  fuel_price_index: number;
  
  spr_days_of_cover: number;
  gdp_index: number;
}

export interface ImpactResult {
  scenario_id: string;
  
  assumptions_used: ScenarioAssumption[];
  
  timeline: ImpactPoint[];
  
  summary: Record<string, number>;
}

export interface SavedScenario {
  
  version: number;
  name: string;
  assumptions: ScenarioAssumption[];
}

export interface ProcurementOption {
  id: string;
  supplier_country: string;
  crude_grade: string;
  tanker_route: string;
  spot_price_usd_bbl: number;
  
  tanker_availability: number;
  
  port_congestion: number;
  
  grade_compatibility: number;
  
  recommendation_score: number;
  rationale: string;
}

export interface PipelineResult {
  signals: Signal[];
  risk_scores: RiskScore[];
  impact: ImpactResult | null;
  recommendations: ProcurementOption[];
  
  linked_actions: Record<string, unknown>[];
  
  latency_ms: number;
  data_source_modes: Record<string, string>;
}
