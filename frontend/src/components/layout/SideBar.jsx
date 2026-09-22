import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FilePlus2,
  ShieldCheck,
} from "lucide-react";

function Sidebar() {
  const items = [
    {
      label: "Dashboard",
      path: "/",
      icon: LayoutDashboard,
    },
    {
      label: "New Claim",
      path: "/claims/new",
      icon: FilePlus2,
    },
  ];

  return (
    <aside className="hidden w-64 flex-col bg-slate-950 text-white lg:flex">
      <div className="border-b border-slate-800 px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600">
            <ShieldCheck size={22} />
          </div>

          <div>
            <h1 className="text-lg font-semibold">
              ClaimPilot
            </h1>

            <p className="text-xs text-slate-400">
              AI Claims Intelligence
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-2 px-4 py-6">
        {items.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition",
                  isActive
                    ? "bg-indigo-600 text-white"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white",
                ].join(" ")
              }
            >
              <Icon size={18} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 px-6 py-5">
        <p className="text-xs text-slate-500">
          ClaimPilot v0.2.2
        </p>

        <p className="mt-1 text-xs text-slate-400">
          Multimodal claims review
        </p>
      </div>
    </aside>
  );
}

export default Sidebar;