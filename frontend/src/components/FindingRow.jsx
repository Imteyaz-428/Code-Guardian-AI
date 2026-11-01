import RiskBadge from "./RiskBadge";

function FindingRow({ finding, isSelected, onSelect }) {
  const functionName =
    finding.function_name ??
    finding.function ??
    finding.title ??
    finding.name ??
    "Unnamed function";

  const fileName =
    finding.file_path ??
    finding.file ??
    finding.file_name ??
    "Unknown file";

  const score =
    finding.risk_score ??
    finding.risk_percent ??
    finding.score ??
    finding.final_risk_percent ??
    0;

  const level =
    finding.risk_level ??
    finding.level ??
    finding.severity ??
    "unknown";

  return (
    <button
      type="button"
      className={`table-row ${isSelected ? "selected" : ""}`}
      onClick={() => onSelect(finding)}
      aria-pressed={isSelected}
    >
      <span className="function-name">
        {functionName}
        {!functionName.endsWith("()") ? "()" : ""}
      </span>

      <span className="file-name">{fileName}</span>

      <span className="risk-score">
        {`${Number(score).toFixed(1)}%`}
      </span>

      <RiskBadge level={level} />
    </button>
  );
}

export default FindingRow;