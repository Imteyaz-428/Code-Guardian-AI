import { useState } from "react";
import {
  Activity,
  ArrowRight,
  Clock3,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import "./App.css";

import Sidebar from "./components/Sidebar";
import RepositoryForm from "./components/RepositoryForm";
import AnalysisResults from "./components/AnalysisResults";
import WelcomePanel from "./components/WelcomePanel";
import SummaryStats from "./components/SummaryStats";
import FindingsTable from "./components/FindingsTable";
import FindingDetails from "./components/FindingDetails";
import CallGraphPanel from "./components/CallGraphPanel";
import CFGPanel from "./components/CFGPanel";

import { useRepositoryAnalysis } from "./hooks/useRepositoryAnalysis";

const pageInfo = {
  overview: {
    title: "Security Overview",
    subtitle:
      "Monitor repository health, discover code risks, and understand your security posture.",
  },
  analysis: {
    title: "Repository Analysis",
    subtitle:
      "Analyze your codebase and inspect structural and security analysis results.",
  },
  findings: {
    title: "Security Findings",
    subtitle:
      "Review detected risks, investigate individual findings, and understand their impact.",
  },
  risk: {
    title: "Risk Intelligence",
    subtitle:
      "Explore risk summaries, function relationships, and control-flow information.",
  },
  fixes: {
    title: "AI Corrections",
    subtitle:
      "Investigate findings and generate proposed code corrections.",
  },
  verification: {
    title: "Patch Verification",
    subtitle:
      "Validate proposed code changes before accepting them.",
  },
  history: {
    title: "Patch History",
    subtitle:
      "Review correction proposals and verification outcomes.",
  },
};

function EmptyAnalysisState({ onNavigate }) {
  return (
    <section className="dashboard-card dashboard-empty-state">
      <div className="empty-state-icon">
        <Activity size={25} />
      </div>

      <h2>No analysis results yet</h2>

      <p>
        Analyze a repository first. Your findings, risk metrics,
        and code intelligence will appear here.
      </p>

      <button
        type="button"
        className="dashboard-primary-button"
        onClick={() => onNavigate("analysis")}
      >
        Analyze Repository
        <ArrowRight size={16} />
      </button>
    </section>
  );
}

function FeatureComingSoon({ page }) {
  const features = {
    fixes: {
      icon: Sparkles,
      heading: "AI-Powered Code Corrections",
      description:
        "Connect to the existing correction API to generate and review proposed fixes.",
    },
    verification: {
      icon: ShieldCheck,
      heading: "Verified Patch Workflow",
      description:
        "Connect to the existing verification API to display actual patch verification results.",
    },
    history: {
      icon: Clock3,
      heading: "Correction History",
      description:
        "Connect to the existing history API to display correction proposals and their statuses.",
    },
  };

  const feature = features[page];
  const Icon = feature.icon;

  return (
    <section className="dashboard-card feature-placeholder">
      <div className="feature-placeholder-icon">
        <Icon size={27} />
      </div>

      <span className="feature-status">
        Integration Pending
      </span>

      <h2>{feature.heading}</h2>

      <p>{feature.description}</p>

      <div className="feature-note">
        <ShieldCheck size={17} />

        <span>
          Backend integration is pending. No simulated results are displayed.
        </span>
      </div>
    </section>
  );
}

function App() {
  const [activePage, setActivePage] = useState("overview");

  const {
    repositoryPath,
    setRepositoryPath,
    data,
    selectedFinding,
    setSelectedFinding,
    loading,
    error,
    runAnalysis,
  } = useRepositoryAnalysis("tests/sample_project");

  const hasAnalysis = Boolean(data);
  const currentPage = pageInfo[activePage];

  return (
    <div className="app-shell">
      <div className="dashboard-layout">
        <Sidebar
          activePage={activePage}
          onNavigate={setActivePage}
        />

        <main className="dashboard-main">
          <header className="dashboard-topbar">
            <div>
              <p className="dashboard-eyebrow">
                CODE GUARDIAN AI / WORKSPACE
              </p>

              <h1 className="dashboard-title">
                {currentPage.title}
              </h1>

              <p className="dashboard-subtitle">
                {currentPage.subtitle}
              </p>
            </div>

            <div
              className={`dashboard-status ${
                loading ? "dashboard-status-busy" : ""
              }`}
              aria-live="polite"
            >
              <span className="dashboard-status-dot" />

              {loading ? "Analyzing..." : "Analysis Workspace"}
            </div>
          </header>

          <div className="dashboard-content">

            {/* OVERVIEW PAGE */}
            {activePage === "overview" && (
              <>
                <section className="dashboard-welcome">
                  <div>
                    <div className="dashboard-welcome-label">
                      <ShieldCheck size={15} />
                      CODE INTELLIGENCE
                    </div>

                    <h2>
                      Understand Your Code.
                      <br />
                      <span>
                        Identify Risk Before It Becomes a Problem.
                      </span>
                    </h2>

                    <p>
                      Analyze repositories, investigate risky functions,
                      and explore your code structure from one workspace.
                    </p>
                  </div>

                  <div className="dashboard-welcome-icon">
                    <ShieldCheck
                      size={66}
                      strokeWidth={1.2}
                    />
                  </div>
                </section>

                <section className="dashboard-section">
                  <h2 className="dashboard-section-heading">
                    Repository Workspace
                  </h2>

                  <div className="dashboard-card">
                    <RepositoryForm
                      repositoryPath={repositoryPath}
                      onRepositoryPathChange={setRepositoryPath}
                      onAnalyze={runAnalysis}
                      loading={loading}
                      error={error}
                    />
                  </div>
                </section>

                {error && (
                  <div className="dashboard-error" role="alert">
                    <strong>Analysis Failed</strong>
                    <p>{error}</p>
                  </div>
                )}

                {hasAnalysis ? (
                  <>
                    <section className="dashboard-section">
                      <h2 className="dashboard-section-heading">
                        Latest Analysis Summary
                      </h2>

                      <SummaryStats
                        summary={data.summary}
                        findings={data.findings}
                      />
                    </section>

                    <section className="dashboard-section">
                      <div className="dashboard-section-header">
                        <h2 className="dashboard-section-heading">
                          Findings and Investigation
                        </h2>

                        <button
                          type="button"
                          className="dashboard-text-button"
                          onClick={() => setActivePage("findings")}
                        >
                          View Findings
                          <ArrowRight size={15} />
                        </button>
                      </div>

                      <FindingsTable
                        findings={data.findings}
                        selectedFinding={selectedFinding}
                        onSelectFinding={setSelectedFinding}
                      />
                    </section>
                  </>
                ) : (
                  !loading &&
                  !error && <WelcomePanel />
                )}
              </>
            )}

            {/* REPOSITORY ANALYSIS PAGE */}
            {activePage === "analysis" && (
              <>
                <section className="dashboard-section">
                  <h2 className="dashboard-section-heading">
                    Analyze Repository
                  </h2>

                  <div className="dashboard-card">
                    <RepositoryForm
                      repositoryPath={repositoryPath}
                      onRepositoryPathChange={setRepositoryPath}
                      onAnalyze={runAnalysis}
                      loading={loading}
                      error={error}
                    />
                  </div>
                </section>

                {error && (
                  <div className="dashboard-error" role="alert">
                    <strong>Analysis Failed</strong>
                    <p>{error}</p>
                  </div>
                )}

                {hasAnalysis && (
                  <section className="dashboard-section">
                    <AnalysisResults
                      data={data}
                      selectedFinding={selectedFinding}
                      onSelectFinding={setSelectedFinding}
                    />
                  </section>
                )}

                {!hasAnalysis && !loading && !error && (
                  <WelcomePanel />
                )}
              </>
            )}

            {/* SECURITY FINDINGS PAGE */}
            {activePage === "findings" && (
              hasAnalysis ? (
                <>
                  <section className="dashboard-section">
                    <SummaryStats
                      summary={data.summary}
                      findings={data.findings}
                    />
                  </section>

                  <section className="dashboard-section">
                    <div className="dashboard-card">
                      <FindingsTable
                        findings={data.findings}
                        selectedFinding={selectedFinding}
                        onSelectFinding={setSelectedFinding}
                      />
                    </div>
                  </section>

                  <section className="dashboard-section">
                    <h2 className="dashboard-section-heading">
                      Finding Investigation
                    </h2>

                    <div className="dashboard-card">
                      <FindingDetails
                        finding={selectedFinding}
                      />
                    </div>
                  </section>
                </>
              ) : (
                <EmptyAnalysisState
                  onNavigate={setActivePage}
                />
              )
            )}

            {/* RISK INTELLIGENCE PAGE */}
            {activePage === "risk" && (
              hasAnalysis ? (
                <>
                  <section className="dashboard-section">
                    <SummaryStats
                      summary={data.summary}
                      findings={data.findings}
                    />
                  </section>

                  <section className="dashboard-section">
                    <CallGraphPanel
                      callGraph={data.call_graph}
                    />
                  </section>

                  <section className="dashboard-section">
                    <CFGPanel
                      controlFlowGraphs={data.control_flow_graphs}
                      selectedFinding={selectedFinding}
                    />
                  </section>
                </>
              ) : (
                <EmptyAnalysisState
                  onNavigate={setActivePage}
                />
              )
            )}

            {/* REMEDIATION PAGES */}
            {["fixes", "verification", "history"].includes(
              activePage
            ) && (
              <section className="dashboard-section">
                <FeatureComingSoon page={activePage} />
              </section>
            )}

          </div>

          <footer className="dashboard-footer">
            <span>Code Guardian AI</span>
            <span>Analyze · Explain · Verify</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default App;