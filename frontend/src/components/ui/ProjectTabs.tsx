import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  Database,
  ShieldAlert,
  FileText,
  Sliders,
  Terminal,
} from "lucide-react";
import { clsx } from "clsx";

export function ProjectTabs({ projectId }: { projectId: string }) {
  const location = useLocation();
  const currentPath = location.pathname;

  const tabs = [
    { name: "Overview", href: `/projects/${projectId}`, icon: LayoutDashboard, exact: true },
    { name: "Evaluations", href: `/projects/${projectId}/evaluations`, icon: Activity },
    { name: "Datasets", href: `/projects/${projectId}/datasets`, icon: Database },
    { name: "Guardrails", href: `/projects/${projectId}/guardrails`, icon: ShieldAlert },
    { name: "Documents", href: `/projects/${projectId}/documents`, icon: FileText },
    { name: "Playground", href: `/projects/${projectId}/playground`, icon: Terminal },
    { name: "Settings", href: `/projects/${projectId}/settings`, icon: Sliders },
  ];

  return (
    <div className="flex items-center gap-1 border-b border-slate-800/80 mb-6 overflow-x-auto no-scrollbar">
      {tabs.map((t) => {
        const Icon = t.icon;
        const isActive = t.exact
          ? currentPath === t.href
          : currentPath.startsWith(t.href);

        return (
          <Link
            key={t.name}
            to={t.href}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all shrink-0 whitespace-nowrap",
              isActive
                ? "border-indigo-500 text-indigo-400 bg-indigo-500/5 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            )}
          >
            <Icon className={clsx("h-3.5 w-3.5", isActive ? "text-indigo-400" : "text-slate-400")} />
            {t.name}
          </Link>
        );
      })}
    </div>
  );
}
