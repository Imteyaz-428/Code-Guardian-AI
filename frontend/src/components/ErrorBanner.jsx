function ErrorBanner({ message }) {
  if (!message) {
    return null;
  }

  return (
    <div
      className="error"
      role="alert"
      aria-live="assertive"
    >
      <span className="error-title">Error</span>
      <span className="error-message">{message}</span>
    </div>
  );
}

export default ErrorBanner;