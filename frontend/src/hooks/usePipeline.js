import { useCallback, useState } from "react";
import { runPipeline } from "../services/pipelineApi";

/**
 * Owns one full pipeline run (analyze -> explain -> fix -> verify)
 * and which function is currently selected.
 */
export function usePipeline() {
  const [result, setResult] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async (options) => {
    setLoading(true);
    setError("");
    setResult(null);
    setSelectedId(null);

    try {
      const data = await runPipeline(options);
      const functions = data.functions ?? [];

      setResult({ ...data, functions, summary: data.summary ?? {} });
      setSelectedId(functions[0]?.function_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const functions = result?.functions ?? [];
  const selected =
    functions.find((item) => item.function_id === selectedId) ?? null;

  return { result, functions, selected, setSelectedId, loading, error, run };
}
