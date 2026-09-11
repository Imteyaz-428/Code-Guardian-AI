import { getLevelClass } from "../utils/risk";

function RiskBadge({ level, size = "small" }) {
  const levelClass = getLevelClass(level);

  if (size === "large") {
    return (
      <div
        className={`large-risk-badge ${levelClass}`}
        aria-label={`${level} risk`}
      >
        <span className="risk-dot" />
        {level} RISK
      </div>
    );
  }

  return (
    <span
      className={`risk-badge ${levelClass}`}
      aria-label={`${level} risk`}
    >
      <span className="risk-dot" />
      {level}
    </span>
  );
}

export default RiskBadge;