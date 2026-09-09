import "./App.css";
import Header from "./components/Header";
import RepositoryForm from "./components/RepositoryForm";
import AnalysisResults from "./components/AnalysisResults";
import WelcomePanel from "./components/WelcomePanel";
import { useRepositoryAnalysis } from "./hooks/useRepositoryAnalysis";

function App() {
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

  return (
    <div className="app">
      <Header busy={loading} />

      <main className="container">
        <RepositoryForm
          repositoryPath={repositoryPath}
          onRepositoryPathChange={setRepositoryPath}
          onAnalyze={runAnalysis}
          loading={loading}
          error={error}
        />

        {data && (
          <AnalysisResults
            data={data}
            selectedFinding={selectedFinding}
            onSelectFinding={setSelectedFinding}
          />
        )}

        {!data && !loading && !error && <WelcomePanel />}
      </main>

      <footer className="footer">Code Guardian AI · Static code analysis</footer>
    </div>
  );
}

export default App;
