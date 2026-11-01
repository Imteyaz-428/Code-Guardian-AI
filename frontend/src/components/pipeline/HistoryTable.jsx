import StatusPill from "./StatusPill";
import { formatDate } from "../../utils/pipeline";

export default function HistoryTable({ proposals, busyId, onApprove, onApply }) {
  if (proposals.length === 0) {
    return <p className="pl-empty">No patch proposals yet.</p>;
  }

  return (
    <div className="pl-table pl-history">
      <div className="pl-row pl-head">
        <span>File</span>
        <span>Status</span>
        <span>Approved</span>
        <span>Applied</span>
        <span>Created</span>
        <span />
      </div>

      {proposals.map((item) => (
        <div key={item.proposal_id} className="pl-row pl-body-static">
          <span className="pl-fn">
            <strong>{item.file_path}</strong>
            <small>{item.repository_path}</small>
          </span>

          <StatusPill status={item.verification_status} />
          <span>{item.approved ? "Yes" : "No"}</span>
          <span>{item.applied ? "Yes" : "No"}</span>
          <span className="pl-muted">{formatDate(item.created_at)}</span>

          <span className="pl-row-actions">
            {item.verification_status === "verified" && !item.approved && (
              <button
                type="button"
                className="pl-ghost"
                disabled={busyId === item.proposal_id}
                onClick={() => onApprove(item.proposal_id)}
              >
                Approve
              </button>
            )}

            {item.approved && !item.applied && (
              <button
                type="button"
                className="pl-ghost"
                disabled={busyId === item.proposal_id}
                onClick={() => onApply(item.proposal_id)}
              >
                Apply
              </button>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
