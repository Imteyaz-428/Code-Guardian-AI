import ErrorBanner from "./ErrorBanner";

function RepositoryForm({
  repositoryPath,
  onRepositoryPathChange,
  onAnalyze,
  loading,
  error,
}) {
  const input = repositoryPath.trim();

  const isGitHubRepository =
    /^https?:\/\/github\.com\/[^/]+\/[^/]+\/?(?:\.git)?$/i.test(input);

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!loading && input) {
      onAnalyze();
    }
  };

  return (
    <section className="analyze-section">
      <div className="analyze-header">
        <div>
          <label htmlFor="repository-path">
            Repository Workspace
          </label>

          <p>
            Analyze a local repository or a public GitHub repository.
          </p>
        </div>
      </div>

      <form className="input-row" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <span className="input-prefix" aria-hidden="true">
            {isGitHubRepository ? "↗" : "$"}
          </span>

          <input
            id="repository-path"
            name="repository-path"
            type="text"
            value={repositoryPath}
            onChange={(event) =>
              onRepositoryPathChange(event.target.value)
            }
            placeholder="Local path or https://github.com/owner/repo"
            autoComplete="off"
            spellCheck="false"
            disabled={loading}
            aria-describedby="repository-help"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !input}
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
        {isGitHubRepository
          ? "GitHub repository detected. The GitHub URL will be sent to the backend."
          : "Enter a local folder path, such as tests/sample_project, or paste a GitHub repository URL."}
      </p>

      {error && <ErrorBanner message={error} />}
    </section>
  );
}

export default RepositoryForm;