import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [repositoryPath, setRepositoryPath] = useState(
    "tests/sample_project"
  );

  const [data, setData] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const analyzeRepository = async () => {
    setLoading(true);
    setError("");
    setData(null);
    setSelectedFinding(null);

    try {
      const response = await fetch(
        `${API_URL}/analyze?repository_path=${encodeURIComponent(
          repositoryPath
        )}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Analysis failed");
      }

      const result = await response.json();

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

  const getLevelClass = (level) => {
    return level.toLowerCase();
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>🛡️ Code Guardian AI</h1>
          <p>Intelligent static code risk analysis</p>
        </div>
      </header>

      <main className="container">
        {/* Repository input */}

        <section className="analyze-section">
          <label>Repository Path</label>

          <div className="input-row">
            <input
              type="text"
              value={repositoryPath}
              onChange={(event) =>
                setRepositoryPath(event.target.value)
              }
              placeholder="Enter repository path"
            />

            <button
              onClick={analyzeRepository}
              disabled={loading || !repositoryPath}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>

          {error && <div className="error">{error}</div>}
        </section>

        {/* Results */}

        {data && (
          <>
            <section className="summary-grid">
              <div className="summary-card">
                <span>Files</span>
                <strong>{data.summary.files_analyzed}</strong>
              </div>

              <div className="summary-card">
                <span>Functions</span>
                <strong>{data.summary.functions_analyzed}</strong>
              </div>

              <div className="summary-card">
                <span>High Risk</span>
                <strong>
                  {
                    data.findings.filter(
                      (item) => item.level === "HIGH"
                    ).length
                  }
                </strong>
              </div>

              <div className="summary-card">
                <span>Medium Risk</span>
                <strong>
                  {
                    data.findings.filter(
                      (item) => item.level === "MEDIUM"
                    ).length
                  }
                </strong>
              </div>
            </section>

            <section className="content-grid">
              {/* Risk table */}

              <div className="panel">
                <div className="panel-header">
                  <h2>Function Risk</h2>
                  <span>
                    {data.findings.length} functions
                  </span>
                </div>

                <div className="table">
                  <div className="table-header">
                    <span>Function</span>
                    <span>File</span>
                    <span>Score</span>
                    <span>Risk</span>
                  </div>

                  {data.findings
                    .sort((a, b) => b.score - a.score)
                    .map((finding, index) => (
                      <button
                        className={`table-row ${
                          selectedFinding === finding
                            ? "selected"
                            : ""
                        }`}
                        key={`${finding.file}-${finding.function}-${index}`}
                        onClick={() =>
                          setSelectedFinding(finding)
                        }
                      >
                        <span className="function-name">
                          {finding.function}()
                        </span>

                        <span className="file-name">
                          {finding.file}
                        </span>

                        <span>{finding.score}</span>

                        <span
                          className={`risk-badge ${getLevelClass(
                            finding.level
                          )}`}
                        >
                          {finding.level}
                        </span>
                      </button>
                    ))}
                </div>
              </div>

              {/* Details */}

              <div className="panel details-panel">
                <div className="panel-header">
                  <h2>Finding Details</h2>
                </div>

                {selectedFinding ? (
                  <div className="details">
                    <h3>
                      {selectedFinding.function}()
                    </h3>

                    <p className="file-location">
                      {selectedFinding.file}:
                      {selectedFinding.line}
                    </p>

                    <div className="score">
                      <span>Risk Score</span>
                      <strong>
                        {selectedFinding.score}
                        <small>/100</small>
                      </strong>
                    </div>

                    <div
                      className={`large-risk-badge ${getLevelClass(
                        selectedFinding.level
                      )}`}
                    >
                      {selectedFinding.level} RISK
                    </div>

                    <h4>Why?</h4>

                    {selectedFinding.reasons.length > 0 ? (
                      <ul>
                        {selectedFinding.reasons.map(
                          (reason, index) => (
                            <li key={index}>{reason}</li>
                          )
                        )}
                      </ul>
                    ) : (
                      <p>
                        No major structural concerns detected.
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="empty">
                    Select a function to see details.
                  </p>
                )}
              </div>
            </section>
          </>
        )}

        {!data && !loading && !error && (
          <div className="welcome">
            <div className="shield">🛡️</div>
            <h2>Analyze your codebase</h2>
            <p>
              Enter a repository path and Code Guardian will
              analyze its structure and identify potentially
              risky functions.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;