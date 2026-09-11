import ErrorBanner from "./ErrorBanner";

function RepositoryForm({
  repositoryPath,
  onRepositoryPathChange,
  onAnalyze,
  loading,
  error,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();

    const path = repositoryPath.trim();

    if (!loading && path) {
      onAnalyze();
    }
  };

  return (
    <section className="analyze-section">
      <div className="analyze-header">
        <div>
          <label htmlFor="repository-path">
            Repository Path
          </label>

          <p>
            Enter the local path of the repository you want to analyze.
          </p>
        </div>
      </div>

      <form className="input-row" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <span className="input-prefix" aria-hidden="true">
            $
          </span>

          <input
            id="repository-path"
            name="repository-path"
            type="text"
            value={repositoryPath}
            onChange={(event) =>
              onRepositoryPathChange(event.target.value)
            }
            placeholder="tests/sample_project"
            autoComplete="off"
            spellCheck="false"
            disabled={loading}
            aria-describedby="repository-help"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !repositoryPath.trim()}
        >
          {loading ? (
            <>
              <span
                className="button-spinner"
                aria-hidden="true"
              />
              Analyzing...
            </>
          ) : (
            "Analyze Repository"
          )}
        </button>
      </form>

      <p id="repository-help" className="input-help">
        Example: tests/sample_project
      </p>

      {error && <ErrorBanner message={error} />}
    </section>
  );
}

export default RepositoryForm;