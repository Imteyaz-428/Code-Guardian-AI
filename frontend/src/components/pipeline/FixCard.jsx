import CopyButton from "./CopyButton";
import DiffView from "./DiffView";
import PatchActions from "./PatchActions";
import StatusPill from "./StatusPill";

export default function FixCard({ fn }) {
  const fix = fn.fix;

  return (
    <div className="pl-fix">
      <div className="pl-fix-head">
        <StatusPill status={fn.fix_status} />
        <span className="pl-hint">{fn.fix_message}</span>
      </div>

      {!fix?.corrected_code && (
        <p className="pl-empty">
          No corrected code is available. Only a fix that passes the sandbox
          is shown.
        </p>
      )}

      {fix?.corrected_code && (
        <>
          {fn.fix_status === "reviewed" && (
            <p className="pl-note">
              Not tested: this repo has no tests. The import check and the
              security re-scan passed. Review the patch before using it. It
              cannot be applied from here.
            </p>
          )}
          {fix.explanation && <p>{fix.explanation}</p>}

          <h4>Patch</h4>
          <DiffView patch={fix.patch} />

          <div className="pl-code-head">
            <h4>Corrected function</h4>
            <CopyButton text={fix.corrected_code} />
          </div>
          <pre className="pl-code">{fix.corrected_code}</pre>

          {fn.fix_status === "verified" && fix.proposal_id && (
            <PatchActions proposalId={fix.proposal_id} />
          )}
        </>
        
      )}
            {!fix?.corrected_code && fix?.verification?.message && (
        <p className="pl-hint">{fix.verification.message}</p>
      )}
            {!fix?.corrected_code && fix?.verification?.stdout && (
        <pre className="pl-code">{fix.verification.stdout}</pre>
      )}
    </div>
  );
}
