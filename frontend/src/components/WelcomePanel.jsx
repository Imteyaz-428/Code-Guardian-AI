function WelcomePanel() {
  return (
    <div className="welcome">
      <svg className="shield" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <path
          d="M16 2.5 27 6.8v8.1c0 7.6-4.7 13.4-11 16.6-6.3-3.2-11-9-11-16.6V6.8z"
          fill="#171b24"
          stroke="#4f7cff"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path
          d="M11 16.2l3.4 3.4 6.6-7"
          stroke="#4f7cff"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      <h2>Analyze your codebase</h2>
      <p>
        Enter a repository path and Code Guardian will analyze its
        structure and identify potentially risky functions.
      </p>
    </div>
  );
}

export default WelcomePanel;
