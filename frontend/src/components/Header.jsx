function Header({ busy }) {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-icon" aria-hidden="true">
          <svg
            viewBox="0 0 32 32"
            fill="none"
            width="22"
            height="22"
          >
            <path
              d="M16 3L27 7v8c0 7.2-4.3 12.9-11 16-6.7-3.1-11-8.8-11-16V7l11-4Z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />

            <path
              d="m11 16 3.3 3.3L21.5 13"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <div className="brand-content">
          <h1>Code Guardian AI</h1>
          <p>Intelligent static code risk analysis</p>
        </div>
      </div>

      <div
        className={`status-pill ${busy ? "busy" : ""}`}
        aria-live="polite"
      >
        <span className="status-dot" />

        <span>
          {busy ? "Analyzing repository" : "Static Analyzer"}
        </span>
      </div>
    </header>
  );
}

export default Header;