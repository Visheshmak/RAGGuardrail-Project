import React, { useState } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  ShieldCheck,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  User as UserIcon,
  Layers,
  Menu,
  X,
} from "lucide-react";
import { clsx } from "clsx";

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard, exact: true },
    { name: "Projects", href: "/projects", icon: FolderKanban, exact: false },
  ];

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={clsx(
          "fixed lg:static inset-y-0 left-0 z-50 w-64 border-r border-slate-800/80 bg-slate-900/90 lg:bg-slate-900/60 backdrop-blur-xl flex flex-col justify-between shrink-0 transition-transform duration-200 lg:translate-x-0",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div>
          {/* Logo & Brand Header */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800/80">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
                <ShieldCheck className="h-5 w-5 text-white" />
              </div>
              <div>
                <span className="font-bold text-base tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  RAGGuard
                </span>
                <span className="block text-[10px] uppercase font-semibold tracking-wider text-indigo-400">
                  Platform Core
                </span>
              </div>
            </Link>

            <button
              onClick={() => setMobileMenuOpen(false)}
              className="lg:hidden text-slate-400 hover:text-slate-200"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = item.exact
                ? location.pathname === item.href
                : location.pathname.startsWith(item.href);

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={clsx(
                    "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all",
                    isActive
                      ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20 shadow-sm font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                  )}
                >
                  <Icon className={clsx("h-4 w-4", isActive ? "text-indigo-400" : "text-slate-400")} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center justify-between gap-3 p-2 rounded-lg bg-slate-950/40 border border-slate-800/50">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                <UserIcon className="h-4 w-4 text-slate-300" />
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-slate-200 truncate">{user?.name || "Developer"}</p>
                <p className="text-[10px] text-slate-400 truncate">{user?.email || "dev@company.internal"}</p>
              </div>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/50 text-indigo-300 capitalize">
              {user?.role || "admin"}
            </span>
          </div>

          <button
            onClick={() => logout()}
            className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 border border-transparent hover:border-rose-900/30 rounded-lg transition-colors cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-xl px-4 sm:px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Layers className="h-4 w-4 text-indigo-400" />
              <span>Workspace</span>
              <span className="text-slate-600">/</span>
              <span className="text-slate-200 font-medium capitalize truncate">
                {location.pathname === "/"
                  ? "Dashboard"
                  : location.pathname.split("/")[1] || "Platform"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-xs font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              API Online
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-4 sm:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
