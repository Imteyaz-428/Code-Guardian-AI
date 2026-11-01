import { useState } from "react";
import { toNumber } from "../../utils/pipeline";

const SOURCES = [
  { id: "path", label: "Local path", placeholder: "/Users/you/project" },
  {
    id: "github",
    label: "GitHub URL",
    placeholder: "https://github.com/owner/repo",
  },
];

export default function PipelineForm({ onRun, loading }) {
  const [source, setSource] = useState("path");
  const [value, setValue] = useState("");
  const [explainTop, setExplainTop] = useState(3);
  const [fixTop, setFixTop] = useState(1);
  const [minFixRisk, setMinFixRisk] = useState(50);

  const current = SOURCES.find((item) => item.id === source);

  const submit = (event) => {
    event.preventDefault();
    if (loading || !value.trim()) return;
    onRun({ source, value: value.trim(), explainTop, fixTop, minFixRisk });
  };

  return (
    <form className="pl-form" onSubmit={submit}>
      <div className="pl-tabs" role="tablist">
        {SOURCES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={source === item.id}
            className={`pl-tab ${source === item.id ? "active" : ""}`}
            onClick={() => setSource(item.id)}
            disabled={loading}
          >
            {item.label}
          </button>
        ))}
      </div>

      <input
        className="pl-input"
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={current.placeholder}
        spellCheck="false"
        autoComplete="off"
        disabled={loading}
        aria-label={current.label}
      />

      <div className="pl-options">
        <label>
          <span>Explain top</span>
          <input
            type="number"
            min="0"
            max="10"
            value={explainTop}
            onChange={(e) => setExplainTop(toNumber(e.target.value, 0, 10))}
            disabled={loading}
          />
        </label>

        <label>
          <span>Fix top</span>
          <input
            type="number"
            min="0"
            max="5"
            value={fixTop}
            onChange={(e) => setFixTop(toNumber(e.target.value, 0, 5))}
            disabled={loading}
          />
        </label>

        <label>
          <span>Min risk % to fix</span>
          <input
            type="number"
            min="0"
            max="100"
            value={minFixRisk}
            onChange={(e) => setMinFixRisk(toNumber(e.target.value, 0, 100))}
            disabled={loading}
          />
        </label>
      </div>

      <div className="pl-form-actions">
        <button
          type="submit"
          className="pl-primary"
          disabled={loading || !value.trim()}
        >
          {loading ? "Running..." : "Analyze and generate fixes"}
        </button>

        {loading && (
          <span className="pl-hint">
            Analyzing, asking the AI and verifying in Docker. This can take a
            minute.
          </span>
        )}
      </div>
    </form>
  );
}
