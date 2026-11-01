import RiskBadge from "../RiskBadge";
import StatusPill from "./StatusPill";
import { formatPercent } from "../../utils/pipeline";

export default function FunctionRiskTable({ functions, selectedId, onSelect }) {
  if (functions.length === 0) {
    return <p className="pl-empty">No functions were returned.</p>;
  }

  return (
    <div className="pl-table" role="table">
      <div className="pl-row pl-head" role="row">
        <span>#</span>
        <span>Function</span>
        <span>Risk</span>
        <span>Level</span>
        <span>Fix</span>
      </div>

      {functions.map((fn) => (
        <button
          key={fn.function_id}
          type="button"
          role="row"
          className={`pl-row pl-body ${
            fn.function_id === selectedId ? "selected" : ""
          }`}
          onClick={() => onSelect(fn.function_id)}
        >
          <span className="pl-muted">{fn.rank}</span>

          <span className="pl-fn">
            <strong>{fn.function}()</strong>
            <small>
              {fn.file}:{fn.line}
            </small>
          </span>

          <span className="pl-risk">
            <span className="pl-bar">
              <i style={{ width: `${Math.min(100, fn.final_risk_percent)}%` }} />
            </span>
            {formatPercent(fn.final_risk_percent)}
          </span>

          <RiskBadge level={fn.level} />
          <StatusPill status={fn.fix_status} />
        </button>
      ))}
    </div>
  );
}
