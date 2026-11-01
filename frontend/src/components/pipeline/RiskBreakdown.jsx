import { formatPercent } from "../../utils/pipeline";

export default function RiskBreakdown({ fn }) {
  const items = [
    { label: "Final risk", value: formatPercent(fn.final_risk_percent) },
    { label: "Static risk", value: formatPercent(fn.static_risk_percent) },
    {
      label: `GNN risk${fn.gnn_label ? ` (${fn.gnn_label})` : ""}`,
      value: formatPercent(fn.gnn_risk_percent),
    },
  ];

  return (
    <div className="pl-meta">
      {items.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}
