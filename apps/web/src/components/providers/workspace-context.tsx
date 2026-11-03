"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { workspaceApi } from "@/lib/api/endpoints";
import type { Workspace } from "@/lib/api/types";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  loading: boolean;
  setActiveWorkspaceId: (id: string) => void;
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const list = await workspaceApi.list();
      setWorkspaces(list);
      const stored = typeof window !== "undefined" ? localStorage.getItem("active_workspace_id") : null;
      const id = stored && list.some((w) => w.id === stored) ? stored : list[0]?.id || null;
      setActiveWorkspaceId(id);
      if (id && typeof window !== "undefined") {
        localStorage.setItem("active_workspace_id", id);
      }
    } catch {
      setWorkspaces([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setActiveWorkspaceIdAndStore = useCallback((id: string) => {
    setActiveWorkspaceId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem("active_workspace_id", id);
    }
  }, []);

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) || null;

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        activeWorkspace,
        loading,
        setActiveWorkspaceId: setActiveWorkspaceIdAndStore,
        refresh,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (ctx === undefined) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return ctx;
}
