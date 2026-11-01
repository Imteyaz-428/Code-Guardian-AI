import { useCallback, useEffect, useState } from "react";
import "../styles/pipeline.css";

import HistoryTable from "../components/pipeline/HistoryTable";
import {
  applyPatch,
  approvePatch,
  getPatchHistory,
} from "../services/pipelineApi";

export default function PatchHistoryPage() {
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getPatchHistory();
      setProposals(data.proposals ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (proposalId, task) => {
    setBusyId(proposalId);
    setError("");

    try {
      await task(proposalId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleApply = (proposalId) => {
    if (window.confirm("This will modify the file in your repository. Continue?")) {
      act(proposalId, applyPatch);
    }
  };

  return (
    <section className="dashboard-section">
      <div className="dashboard-section-header">
        <h2 className="dashboard-section-heading">Patch proposals</h2>

        <button
          type="button"
          className="pl-ghost"
          onClick={load}
          disabled={loading}
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="dashboard-error" role="alert">
          <strong>Something went wrong</strong>
          <p>{error}</p>
        </div>
      )}

      <div className="dashboard-card">
        <HistoryTable
          proposals={proposals}
          busyId={busyId}
          onApprove={(id) => act(id, approvePatch)}
          onApply={handleApply}
        />
      </div>
    </section>
  );
}
