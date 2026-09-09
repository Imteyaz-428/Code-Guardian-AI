import FindingRow from "./FindingRow";
import { sortFindingsByScore } from "../utils/risk";

function FindingsTable({ findings, selectedFinding, onSelectFinding }) {
  const sortedFindings = sortFindingsByScore(findings);

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Function Risk</h2>
        <span>{findings.length} functions</span>
      </div>

      <div className="table">
        <div className="table-header">
          <span>Function</span>
          <span>File</span>
          <span>Score</span>
          <span>Risk</span>
        </div>

        {sortedFindings.map((finding, index) => (
          <FindingRow
            key={`${finding.file}-${finding.function}-${index}`}
            finding={finding}
            isSelected={selectedFinding === finding}
            onSelect={() => onSelectFinding(finding)}
          />
        ))}
      </div>
    </div>
  );
}

export default FindingsTable;
