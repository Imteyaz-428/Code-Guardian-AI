import StatusPill from "./StatusPill";

function Meta({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function VerificationCard({ fix }) {
  const v = fix.verification;
  const security = v?.security;
  const review = fix.ai_review;

  return (
    <div className="pl-verify">
      <div className="pl-fix-head">
        <StatusPill status={v?.status ?? fix.status} />
        <span className="pl-hint">{v?.message ?? fix.message}</span>
      </div>

      {v && (
        <div className="pl-meta">
          <Meta label="Check level" value={v.verification_level} />
          <Meta label="Sandbox" value={v.sandbox} />
          <Meta label="Duration" value={`${v.duration_seconds}s`} />
          <Meta label="Regressions" value={v.regressions?.length ?? 0} />
        </div>
      )}

      {security && (
        <>
          <h4>Security re-scan</h4>
          <div className="pl-meta">
            <Meta label="Findings before" value={security.findings_before} />
            <Meta label="Findings after" value={security.findings_after} />
            <Meta
              label="New findings"
              value={security.introduced?.length ?? 0}
            />
            <Meta
              label="Original issue fixed"
              value={security.fix_confirmed ? "Yes" : "No"}
            />
          </div>
        </>
      )}

      {review && (
        <>
          <h4>AI review ({review.verdict})</h4>
          <p>{review.reasoning}</p>
        </>
      )}

      {(v?.stdout || v?.stderr) && (
        <>
          <h4>Sandbox output</h4>
          <pre className="pl-code">{(v.stdout || "") + (v.stderr || "")}</pre>
        </>
      )}

      {fix.attempts?.length > 0 && (
        <>
          <h4>Attempts</h4>
          <ul className="pl-attempts">
            {fix.attempts.map((item) => (
              <li key={item.attempt}>
                <StatusPill status={item.status} />
                <span>Attempt {item.attempt}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
