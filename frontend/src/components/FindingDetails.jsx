import RiskBadge from "./RiskBadge";

function FindingDetails({ finding }) {
  return (
    <div className="panel details-panel">
      <div className="panel-header">
        <h2>Finding Details</h2>
      </div>

      {finding ? (
        <div className="details">
          <div className="finding-heading">
            <h3>{finding.function}()</h3>

            <p className="file-location">
              {finding.file}:{finding.line}
            </p>
          </div>

          <div className="score">
            <span>Risk Score</span>

            <strong>
              {finding.score}
              <small>/100</small>
            </strong>
          </div>

          <RiskBadge
            level={finding.level}
            size="large"
          />

          <div className="risk-reasons">
            <h4>Why?</h4>

            {finding.reasons?.length > 0 ? (
              <ul>
                {finding.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="no-reasons">
                No major structural concerns detected.
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="empty">
          <p>Select a function to see details.</p>
        </div>
      )}
    </div>
  );
}

export default FindingDetails;