import ErrorBanner from "./ErrorBanner";

function RepositoryForm({
  repositoryPath,
  onRepositoryPathChange,
  onAnalyze,
  loading,
  error,
}) {
  return (
    <section className="analyze-section">
      <label>Repository Path</label>

      <div className="input-row">
        <input
          type="text"
          value={repositoryPath}
          onChange={(event) => onRepositoryPathChange(event.target.value)}
          placeholder="Enter repository path"
        />

        <button onClick={onAnalyze} disabled={loading || !repositoryPath}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      <ErrorBanner message={error} />
    </section>
  );
}

export default RepositoryForm;
