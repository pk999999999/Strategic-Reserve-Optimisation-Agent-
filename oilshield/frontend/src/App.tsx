import { DashboardShell, KpiStrip } from "./components";
import {
  RiskRadarView,
  ScenarioSimulatorView,
  ProcurementView,
  PipelineRunnerView,
} from "./views";

function App() {
  return (
    <DashboardShell
      dataSourceMode="simulated"
      dataSourceModes={{ news: "simulated", prices: "simulated" }}
      overview={<KpiStrip />}
      riskRadar={<RiskRadarView />}
      scenarioSimulator={<ScenarioSimulatorView />}
      procurement={<ProcurementView />}
      pipeline={<PipelineRunnerView />}
    />
  );
}

export default App;
