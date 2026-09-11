import { countByLevel } from "../utils/risk";

function SummaryStats({ summary, findings }) {
  const stats = [
    {
      label: "Files",
      value: summary.files_analyzed,
      description: "analyzed",
    },
    {
      label: "Functions",
      value: summary.functions_analyzed,
      description: "detected",
    },
    {
      label: "High Risk",
      value: countByLevel(findings, "HIGH"),
      description: "findings",
      emphasis: "high",
    },
    {
      label: "Medium Risk",
      value: countByLevel(findings, "MEDIUM"),
      description: "findings",
      emphasis: "medium",
    },
  ];

  return (
    <section className="summary-grid" aria-label="Analysis summary">
      {stats.map((stat) => (
        <article
          className={`summary-card ${
            stat.emphasis ? `summary-${stat.emphasis}` : ""
          }`}
          key={stat.label}
        >
          <div className="summary-card-header">
            <span>{stat.label}</span>
          </div>

          <div className="summary-card-value">
            <strong>{stat.value}</strong>
          </div>

          <small>{stat.description}</small>
        </article>
      ))}
    </section>
  );
}

export default SummaryStats;