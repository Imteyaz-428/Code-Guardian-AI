const SECTIONS = [
  { key: "why_risky", title: "Why it is risky" },
  { key: "attack_scenario", title: "Attack scenario" },
  { key: "fix_strategy", title: "Fix strategy" },
];

export default function ExplanationCard({ explanation }) {
  if (!explanation) {
    return (
      <p className="pl-empty">
        No AI explanation for this function. The explainer only runs on the top
        functions, or no AI provider was available.
      </p>
    );
  }

  return (
    <div className="pl-explain">
      <p className="pl-lead">{explanation.summary}</p>

      {explanation.likely_false_positive && (
        <p className="pl-note">
          The AI thinks this may be a false positive.
        </p>
      )}

      {SECTIONS.map(
        ({ key, title }) =>
          explanation[key] && (
            <div key={key}>
              <h4>{title}</h4>
              <p>{explanation[key]}</p>
            </div>
          )
      )}
    </div>
  );
}
