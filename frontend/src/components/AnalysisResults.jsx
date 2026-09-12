import SummaryStats from "./SummaryStats";
import FindingsTable from "./FindingsTable";
import FindingDetails from "./FindingDetails";
import CallGraphPanel from "./CallGraphPanel";
import CFGPanel from "./CFGPanel";

function AnalysisResults({
  data,
  selectedFinding,
  onSelectFinding,
}) {
  return (
    <section className="analysis-results">
      <SummaryStats
        summary={data.summary}
        findings={data.findings}
      />

      <section className="content-grid">
        <FindingsTable
        findings={data.findings}
        selectedFinding={selectedFinding}
        onSelectFinding={onSelectFinding}
      />

        <FindingDetails
          finding={selectedFinding}
        />
      </section>

      <CallGraphPanel
        callGraph={data.call_graph}
      />

      <CFGPanel
        controlFlowGraphs={data.control_flow_graphs}
        selectedFinding={selectedFinding}
      />
    </section>
  );
}

export default AnalysisResults;