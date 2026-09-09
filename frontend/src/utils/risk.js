export function getLevelClass(level) {
  return level.toLowerCase();
}

export function sortFindingsByScore(findings) {
  return [...findings].sort((a, b) => b.score - a.score);
}

export function countByLevel(findings, level) {
  return findings.filter((item) => item.level === level).length;
}
