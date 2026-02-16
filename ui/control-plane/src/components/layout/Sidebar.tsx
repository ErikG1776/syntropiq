import { NavLink } from "react-router-dom";
import { Badge } from "../ui/Badge";

const NAV_ITEMS = [
  { label: "Overview", to: "/" },
  { label: "Agents", to: "/agents" },
  { label: "Governance Cycles", to: "/governance-cycles" },
  { label: "Events", to: "/events" },
  { label: "Mutation", to: "/mutation" },
  { label: "Reflections", to: "/reflections" },
  { label: "Settings", to: "/settings" },
];

export function Sidebar() {
  return (
    <aside className="border-r border-border bg-panel px-3 py-4">
      <div className="mb-4 text-[11px] uppercase tracking-[0.12em] text-textMuted">Navigation</div>
      <nav className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs transition ${
                isActive ? "bg-accent/20 text-[#c9ddff]" : "text-textMuted hover:bg-panelAlt hover:text-text"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {item.label}
                {isActive ? <Badge label="Selected" tone="accent" /> : null}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
