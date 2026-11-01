import { API_URL } from "./api";

function readDetail(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return JSON.stringify(detail);
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure it is running."
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      readDetail(body.detail) || `Request failed (${response.status})`
    );
  }

  return response.json();
}

/** Full pipeline: analyze -> risk % -> explain -> fix -> sandbox verify. */
export function runPipeline({ source, value, explainTop, fixTop, minFixRisk }) {
  const body = {
    top_n: 10,
    explain_top: explainTop,
    fix_top: fixTop,
    min_fix_risk: minFixRisk,
  };

  if (source === "github") {
    body.github_url = value;
  } else {
    body.repository_path = value;
  }

  return request("/pipeline/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getPatchHistory(limit = 50) {
  return request(`/correction/history?limit=${limit}`);
}

export function approvePatch(proposalId) {
  return request(`/correction/${encodeURIComponent(proposalId)}/approve`, {
    method: "POST",
  });
}

export function applyPatch(proposalId) {
  return request("/correction/apply", {
    method: "POST",
    body: JSON.stringify({ proposal_id: proposalId }),
  });
}
