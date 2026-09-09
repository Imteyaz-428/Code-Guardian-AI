import { useState } from "react";
import { analyzeRepository } from "../services/api";

/**
 * Owns the full lifecycle of a repository analysis request:
 * the current path, loading/error state, the result, and the
 * currently selected finding.
 */
export function useRepositoryAnalysis(initialPath) {
  const [repositoryPath, setRepositoryPath] = useState(initialPath);
  const [data, setData] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runAnalysis = async () => {
    setLoading(true);
    setError("");
    setData(null);
    setSelectedFinding(null);

    try {
      const result = await analyzeRepository(repositoryPath);

      setData(result);

      if (result.findings.length > 0) {
        setSelectedFinding(result.findings[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return {
    repositoryPath,
    setRepositoryPath,
    data,
    selectedFinding,
    setSelectedFinding,
    loading,
    error,
    runAnalysis,
  };
}
