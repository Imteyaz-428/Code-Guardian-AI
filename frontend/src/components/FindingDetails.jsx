import RiskBadge from "./RiskBadge";

function FindingDetails({ finding }) {
  return (
    <div className="panel details-panel">
      <div className="panel-header">
        <h2>Finding Details</h2>
      </div>

      {finding ? (
        <div className="details">
          <h3>{finding.function}()</h3>

          <p className="file-location">
            {finding.file}:{finding.line}
          </p>

          <div className="score">
            <span>Risk Score</span>
            <strong>
              {finding.score}
              <small>/100</small>
            </strong>
          </div>

          <RiskBadge level={finding.level} size="large" />

          <h4>Why?</h4>

          {finding.reasons.length > 0 ? (
            <ul>
              {finding.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          ) : (
            <p>No major structural concerns detected.</p>
          )}
        </div>
      ) : (
        <p className="empty">Select a function to see details.</p>
      )}
    </div>
  );
}

export default FindingDetails;
