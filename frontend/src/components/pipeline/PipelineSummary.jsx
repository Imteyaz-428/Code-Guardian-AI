export default function PipelineSummary({ summary }) {
  const stats = [
    { label: "Files", value: summary.files_analyzed ?? 0, note: "analyzed" },
    {
      label: "Functions",
      value: summary.functions_analyzed ?? 0,
      note: "analyzed",
    },
    { label: "Fixes", value: summary.fixes_attempted ?? 0, note: "attempted" },
    {
      label: "Verified",
      value: summary.fixes_verified ?? 0,
      note: "in the sandbox",
      emphasis: "medium",
    },
  ];

  return (
    <section className="summary-grid" aria-label="Pipeline summary">
      {stats.map((stat) => (
        <article
          key={stat.label}
          className={`summary-card ${
            stat.emphasis ? `summary-${stat.emphasis}` : ""
          }`}
        >
          <div className="summary-card-header">
            <span>{stat.label}</span>
          </div>
          <div className="summary-card-value">
            <strong>{stat.value}</strong>
          </div>
          <small>{stat.note}</small>
        </article>
      ))}
    </section>
  );
}
