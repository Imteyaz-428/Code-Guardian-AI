import SummaryStats from "./SummaryStats";
import FindingsTable from "./FindingsTable";
import FindingDetails from "./FindingDetails";
import CallGraphPanel from "./CallGraphPanel";

function AnalysisResults({ data, selectedFinding, onSelectFinding }) {
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
          onSelect={onSelectFinding}
        />

        <FindingDetails finding={selectedFinding} />
      </section>

      <CallGraphPanel callGraph={data.call_graph} />
    </section>
  );
}

export default AnalysisResults;