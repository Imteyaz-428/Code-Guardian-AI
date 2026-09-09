// Falls back to localhost for local dev, but can be overridden per
// environment via a Vite env var (VITE_API_URL) without touching code.
export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Ask the backend to analyze a repository and return risk findings.
 *
 * Throws an Error with a readable message on failure, so callers can
 * show it directly to the user.
 */
export async function analyzeRepository(repositoryPath) {
  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ repository_path: repositoryPath }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Analysis failed");
  }

  return response.json();
}
