const FIX_STATUS = {
  verified: { label: "Verified", tone: "good" },
  unverified: { label: "Not verified", tone: "warn" },
  syntax_passed: { label: "Not verified", tone: "warn" },
  error: { label: "Error", tone: "bad" },
  blocked: { label: "Blocked", tone: "bad" },
  rejected: { label: "Rejected", tone: "bad" },
  skipped: { label: "Skipped", tone: "muted" },
  not_attempted: { label: "Not attempted", tone: "muted" },
  reviewed: { label: "Reviewed, not tested", tone: "warn" },
};

export function statusMeta(status) {
  return FIX_STATUS[status] ?? { label: status || "Unknown", tone: "muted" };
}

export function formatPercent(value) {
  return value == null ? "-" : `${Number(value).toFixed(1)}%`;
}

export function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function toNumber(value, min, max) {
  const number = Number(value);
  if (Number.isNaN(number)) return min;
  return Math.min(max, Math.max(min, number));
}
