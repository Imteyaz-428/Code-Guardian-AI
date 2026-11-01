import { useState } from "react";
import { applyPatch, approvePatch } from "../../services/pipelineApi";

/** Human-in-the-loop: approve first, then apply to the repository. */
export default function PatchActions({ proposalId }) {
  const [approved, setApproved] = useState(false);
  const [applied, setApplied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const run = async (task, onDone) => {
    setBusy(true);
    setMessage("");
    try {
      const result = await task();
      onDone();
      setMessage(result.message || "Done.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = () =>
    run(() => approvePatch(proposalId), () => setApproved(true));

  const apply = () => {
    const ok = window.confirm(
      "This will modify the file in your repository. Continue?"
    );
    if (ok) run(() => applyPatch(proposalId), () => setApplied(true));
  };

  return (
    <div className="pl-actions">
      <button
        type="button"
        className="pl-primary"
        onClick={approve}
        disabled={busy || approved}
      >
        {approved ? "Approved" : "Approve patch"}
      </button>

      <button
        type="button"
        className="pl-secondary"
        onClick={apply}
        disabled={busy || !approved || applied}
      >
        {applied ? "Applied" : "Apply to repository"}
      </button>

      {message && <span className="pl-hint">{message}</span>}
    </div>
  );
}
