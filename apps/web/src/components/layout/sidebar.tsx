"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/providers/auth-context";
import { useWorkspace } from "@/components/providers/workspace-context";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  CreditCard,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/decisions", label: "Decisions", icon: FolderOpen },
  { href: "/app/settings", label: "Settings", icon: Settings },
  { href: "/app/subscription", label: "Subscription", icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { workspaces, activeWorkspace, setActiveWorkspaceId } = useWorkspace();
  const [wsOpen, setWsOpen] = useState(false);

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-navy-900 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-border">
        <Link href="/app" className="flex items-center gap-2">
          <span className="text-xl font-bold">
            <span className="text-white">After</span>
            <span className="text-cyan">Mind</span>
          </span>
        </Link>
      </div>

      {/* Workspace selector */}
      <div className="px-3 py-3 border-b border-border relative">
        <button
          onClick={() => setWsOpen(!wsOpen)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-navy-800 hover:bg-navy-700 transition-colors"
        >
          <span className="text-sm text-slate-200 truncate">
            {activeWorkspace?.name || "Select workspace"}
          </span>
          <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
        </button>
        {wsOpen && (
          <div className="absolute left-3 right-3 top-full mt-1 rounded-lg border border-border bg-navy-800 shadow-xl z-50">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => {
                  setActiveWorkspaceId(ws.id);
                  setWsOpen(false);
                }}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm hover:bg-navy-700 rounded-lg",
                  ws.id === activeWorkspace?.id && "text-cyan",
                )}
              >
                {ws.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                active
                  ? "bg-cyan/10 text-cyan"
                  : "text-slate-400 hover:bg-navy-800 hover:text-slate-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="h-8 w-8 rounded-full bg-navy-700 flex items-center justify-center text-sm font-medium text-slate-300">
            {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-200 truncate">{user?.full_name || "User"}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="text-slate-400 hover:text-red-400 transition-colors"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
