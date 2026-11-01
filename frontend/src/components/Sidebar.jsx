import {
  Activity,
  Bug,
  Boxes,
  Clock3,
  FileCode2,
  LayoutDashboard,
  ShieldCheck,
  Wrench,
} from "lucide-react";

const navigation = [
  {
    title: "WORKSPACE",
    items: [
      { id: "overview", label: "Overview", icon: LayoutDashboard },
      { id: "analysis", label: "Repository Analysis", icon: FileCode2 },
      { id: "findings", label: "Security Findings", icon: Bug },
      { id: "risk", label: "Risk Intelligence", icon: Activity },
    ],
  },
  {
    title: "REMEDIATION",
    items: [
      { id: "fixes", label: "AI Corrections", icon: Wrench },
      { id: "verification", label: "Patch Verification", icon: ShieldCheck },
      { id: "history", label: "Patch History", icon: Clock3 },
    ],
  },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-symbol">
          <ShieldCheck size={23} strokeWidth={2.2} />
        </div>

        <div>
          <div className="sidebar-brand-name">Code Guardian</div>
          <div className="sidebar-brand-caption">AI SECURITY PLATFORM</div>
        </div>
      </div>

      <div className="workspace-label">DEVELOPER WORKSPACE</div>

      <nav className="sidebar-navigation" aria-label="Main navigation">
        {navigation.map((group) => (
          <div className="nav-group" key={group.title}>
            <div className="nav-group-title">{group.title}</div>

            {group.items.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={`nav-item ${
                  activePage === id ? "active" : ""
                }`}
                onClick={() => onNavigate(id)}
                aria-current={activePage === id ? "page" : undefined}
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-security-icon">
          <Boxes size={19} />
        </div>
        <div>
          <div className="sidebar-bottom-title">Code intelligence</div>
          <div className="sidebar-bottom-caption">
            Static analysis · Structural risk
          </div>
        </div>
      </div>
    </aside>
  );
}