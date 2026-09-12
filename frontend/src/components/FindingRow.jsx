import RiskBadge from "./RiskBadge";

function FindingRow({ finding, isSelected, onSelect }) {
  return (
    <button
      type="button"
      className={`table-row ${isSelected ? "selected" : ""}`}
      onClick={() => onSelect(finding)}
      aria-pressed={isSelected}
    >
      <span className="function-name">
        {finding.function}()
      </span>

      <span className="file-name">
        {finding.file}
      </span>

      <span className="risk-score">
        {finding.score}
      </span>

      <RiskBadge level={finding.level} />
    </button>
  );
}

export default FindingRow;