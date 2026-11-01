import "../styles/pipeline.css";

import EmptyState from "../components/pipeline/EmptyState";
import FunctionRiskTable from "../components/pipeline/FunctionRiskTable";
import VerificationCard from "../components/pipeline/VerificationCard";

export default function PatchVerificationPage({ pipeline, onNavigate }) {
  const { result, functions, selected, setSelectedId } = pipeline;

  if (!result) {
    return (
      <EmptyState
        title="No verification results yet"
        text="Run the pipeline from AI Corrections. Every generated fix is tested in the Docker sandbox and shown here."
        actionLabel="Go to AI Corrections"
        onAction={() => onNavigate("fixes")}
      />
    );
  }

  return (
    <>
      <section className="dashboard-section">
        <h2 className="dashboard-section-heading">Select a function</h2>

        <div className="dashboard-card">
          <FunctionRiskTable
            functions={functions}
            selectedId={selected?.function_id}
            onSelect={setSelectedId}
          />
        </div>
      </section>

      {selected && (
        <section className="dashboard-section">
          <h2 className="dashboard-section-heading">
            Verification: {selected.function}()
          </h2>

          <div className="dashboard-card">
            {selected.fix ? (
              <VerificationCard fix={selected.fix} />
            ) : (
              <p className="pl-empty">
                No fix was attempted for this function. {selected.fix_message}
              </p>
            )}
          </div>
        </section>
      )}
    </>
  );
}
