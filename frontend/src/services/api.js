// Falls back to localhost for local dev, but can be overridden per
// environment via a Vite env var (VITE_API_URL) without touching code.
export const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Ask the backend to analyze a repository.
 *
 * The API response is normalized here so the rest of the
 * frontend can safely consume every analysis section.
 */
export async function analyzeRepository(repositoryPath) {
  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_path: repositoryPath,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    throw new Error(
      errorData.detail || "Analysis failed"
    );
  }

  const result = await response.json();

  return {
    ...result,

    // Keep all graph sections predictable for the UI.
    call_graph: result.call_graph ?? {
      nodes: [],
      edges: [],
    },

    control_flow_graphs:
      result.control_flow_graphs ?? [],

    findings: result.findings ?? [],
    errors: result.errors ?? [],

    summary: result.summary ?? {
      files_analyzed: 0,
      functions_analyzed: 0,
      files_failed: 0,
    },
  };
}