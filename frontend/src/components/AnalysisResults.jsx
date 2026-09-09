import SummaryStats from "./SummaryStats";
import FindingsTable from "./FindingsTable";
import FindingDetails from "./FindingDetails";

function AnalysisResults({ data, selectedFinding, onSelectFinding }) {
  return (
    <>
      <SummaryStats summary={data.summary} findings={data.findings} />

      <section className="content-grid">
        <FindingsTable
          findings={data.findings}
          selectedFinding={selectedFinding}
          onSelectFinding={onSelectFinding}
        />

        <FindingDetails finding={selectedFinding} />
      </section>
    </>
  );
}

export default AnalysisResults;
