import RiskBadge from "./RiskBadge";

function FindingRow({ finding, isSelected, onSelect }) {
  return (
    <button
      className={`table-row ${isSelected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <span className="function-name">{finding.function}()</span>
      <span className="file-name">{finding.file}</span>
      <span>{finding.score}</span>
      <RiskBadge level={finding.level} />
    </button>
  );
}

export default FindingRow;
