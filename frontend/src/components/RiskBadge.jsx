import { getLevelClass } from "../utils/risk";

function RiskBadge({ level, size = "small" }) {
  if (size === "large") {
    return (
      <div className={`large-risk-badge ${getLevelClass(level)}`}>
        {level} RISK
      </div>
    );
  }

  return <span className={`risk-badge ${getLevelClass(level)}`}>{level}</span>;
}

export default RiskBadge;
