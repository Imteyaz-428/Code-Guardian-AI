export function getLevelClass(level) {
  return String(level ?? "unknown").toLowerCase();
}

export function sortFindingsByScore(findings) {
  return [...findings].sort(
    (a, b) =>
      Number(b.risk_score ?? b.risk_percent ?? b.score ?? 0) -
      Number(a.risk_score ?? a.risk_percent ?? a.score ?? 0)
  );
}

export function countByLevel(findings, level) {
  return findings.filter((item) => {
    const itemLevel =
      item.risk_level ?? item.level ?? item.severity ?? "unknown";

    return (
      String(itemLevel).toLowerCase() === String(level).toLowerCase()
    );
  }).length;
}