import { countByLevel } from "../utils/risk";

function SummaryStats({ summary, findings }) {
  return (
    <section className="summary-grid">
      <div className="summary-card">
        <span>Files</span>
        <strong>{summary.files_analyzed}</strong>
      </div>

      <div className="summary-card">
        <span>Functions</span>
        <strong>{summary.functions_analyzed}</strong>
      </div>

      <div className="summary-card">
        <span>High Risk</span>
        <strong>{countByLevel(findings, "HIGH")}</strong>
      </div>

      <div className="summary-card">
        <span>Medium Risk</span>
        <strong>{countByLevel(findings, "MEDIUM")}</strong>
      </div>
    </section>
  );
}

export default SummaryStats;
