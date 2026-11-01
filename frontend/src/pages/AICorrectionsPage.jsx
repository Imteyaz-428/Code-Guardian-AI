import "../styles/pipeline.css";

import PipelineForm from "../components/pipeline/PipelineForm";
import PipelineSummary from "../components/pipeline/PipelineSummary";
import FunctionRiskTable from "../components/pipeline/FunctionRiskTable";
import RiskBreakdown from "../components/pipeline/RiskBreakdown";
import ExplanationCard from "../components/pipeline/ExplanationCard";
import FixCard from "../components/pipeline/FixCard";

export default function AICorrectionsPage({ pipeline }) {
  const { result, functions, selected, setSelectedId, loading, error, run } =
    pipeline;

  return (
    <>
      <section className="dashboard-section">
        <h2 className="dashboard-section-heading">Analyze and fix</h2>

        <div className="dashboard-card">
          <PipelineForm onRun={run} loading={loading} />
        </div>
      </section>

      {error && (
        <div className="dashboard-error" role="alert">
          <strong>Pipeline failed</strong>
          <p>{error}</p>
        </div>
      )}

      {result && (
        <>
          <section className="dashboard-section">
            <PipelineSummary summary={result.summary} />
          </section>

          <section className="dashboard-section">
            <h2 className="dashboard-section-heading">Risky functions</h2>

            <div className="dashboard-card">
              <FunctionRiskTable
                functions={functions}
                selectedId={selected?.function_id}
                onSelect={setSelectedId}
              />
            </div>

            {result.score_note && (
              <p className="pl-hint pl-footnote">{result.score_note}</p>
            )}
          </section>

          {selected && (
            <section className="pl-detail-grid">
              <div className="dashboard-card">
                <h3 className="pl-card-title">
                  {selected.function}() risk
                </h3>

                <RiskBreakdown fn={selected} />

                {selected.vulnerabilities.length > 0 && (
                  <ul className="pl-vulns">
                    {selected.vulnerabilities.map((item, index) => (
                      <li key={index}>
                        <strong>{item.name}</strong>
                        <span>
                          {item.source} to {item.sink}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                <ExplanationCard explanation={selected.explanation} />
              </div>

              <div className="dashboard-card">
                <h3 className="pl-card-title">Proposed fix</h3>
                <FixCard key={selected.function_id} fn={selected} />
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}
