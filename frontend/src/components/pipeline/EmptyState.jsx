import { Activity, ArrowRight } from "lucide-react";

export default function EmptyState({ title, text, actionLabel, onAction }) {
  return (
    <section className="dashboard-card dashboard-empty-state">
      <div className="empty-state-icon">
        <Activity size={25} />
      </div>

      <h2>{title}</h2>
      <p>{text}</p>

      {onAction && (
        <button
          type="button"
          className="dashboard-primary-button"
          onClick={onAction}
        >
          {actionLabel}
          <ArrowRight size={16} />
        </button>
      )}
    </section>
  );
}
