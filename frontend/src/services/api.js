export const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function analyzeRepository(repositoryInput) {
  const input = repositoryInput.trim();

  const isGitHubRepository =
    /^https?:\/\/github\.com\/[^/]+\/[^/]+\/?(?:\.git)?$/i.test(input);

  const endpoint = isGitHubRepository
    ? "/pipeline/scan"
    : "/analyze";
  const payload = isGitHubRepository
    ? { github_url: input.replace(/\/$/, "") }
    : { repository_path: input };

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      result.detail || result.message || "Repository analysis failed"
    );
  }

  // Preserve the existing local repository analysis response.
  if (!isGitHubRepository) {
    return {
      ...result,
      call_graph: result.call_graph ?? {
        nodes: [],
        edges: [],
      },
      control_flow_graphs: result.control_flow_graphs ?? [],
      findings: result.findings ?? [],
      errors: result.errors ?? [],
      summary: result.summary ?? {
        files_analyzed: 0,
        functions_analyzed: 0,
        files_failed: 0,
      },
    };
  }

  // Convert GitHub scan functions into dashboard findings.
  const findings = (result.functions ?? []).map((item, index) => ({
    id: item.function_id || `${item.file}-${item.function}-${index}`,
    title: item.function || "Unnamed function",
    function_name: item.function || "Unnamed function",
    file: item.file || "",
    file_path: item.file || "",
    line: item.line ?? 0,

    risk_score: item.final_risk_percent ?? 0,
    risk_percent: item.final_risk_percent ?? 0,
    risk_level: item.level || "Unknown",

    severity: item.level || "Unknown",
    description: item.basis || "Risk identified by code analysis.",
    reasons: item.reasons ?? [],
    vulnerabilities: item.vulnerabilities ?? [],

    static_risk_percent: item.static_risk_percent ?? 0,
    structural_score: item.structural_score ?? 0,
    vulnerability_score: item.vulnerability_score ?? 0,
    gnn_risk_percent: item.gnn_risk_percent ?? null,
    gnn_label: item.gnn_label ?? null,

    explanation: item.explanation ?? null,
    fix_request: item.fix_request ?? null,
  }));

  return {
    ...result,

    findings,

    summary: {
      ...(result.summary ?? {}),
      files_analyzed:
        result.summary?.files_analyzed ??
        result.summary?.total_files ??
        0,
      functions_analyzed:
        result.summary?.functions_analyzed ??
        result.summary?.total_functions ??
        findings.length,
      files_failed: result.summary?.files_failed ?? 0,
    },

    call_graph: {
      nodes: [],
      edges: [],
    },

    control_flow_graphs: [],
    errors: [],
  };
}