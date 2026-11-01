import { statusMeta } from "../../utils/pipeline";

export default function StatusPill({ status }) {
  const { label, tone } = statusMeta(status);

  return <span className={`pl-pill pl-pill-${tone}`}>{label}</span>;
}
