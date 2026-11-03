"use client";

import { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "@/components/providers/workspace-context";
import { decisionApi } from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CardSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { FolderOpen, TrendingUp, Activity, AlertCircle } from "lucide-react";
import Link from "next/link";
import { formatDate, formatNumber } from "@/lib/utils";
import type { Decision } from "@/lib/api/types";

export default function DashboardPage() {
  const { activeWorkspace } = useWorkspace();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setError("");
    try {
      const resp = await decisionApi.list(activeWorkspace.id);
      setDecisions(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decisions");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    load();
  }, [load]);

  const activeDecisions = decisions.filter((d) => d.status === "active");
  const draftDecisions = decisions.filter((d) => d.status === "draft");

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Welcome back. Here&apos;s an overview of your decision workspace.
          </p>
        </div>
        <Link href="/app/decisions">
          <Button>
            <FolderOpen className="h-4 w-4 mr-2" />
            View Decisions
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-cyan/10">
              <FolderOpen className="h-6 w-6 text-cyan" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Total Decisions</p>
              <p className="text-2xl font-bold text-white">{formatNumber(decisions.length, 0)}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-violet/10">
              <TrendingUp className="h-6 w-6 text-violet" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Active</p>
              <p className="text-2xl font-bold text-white">{formatNumber(activeDecisions.length, 0)}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-slate-700/30">
              <Activity className="h-6 w-6 text-slate-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Drafts</p>
              <p className="text-2xl font-bold text-white">{formatNumber(draftDecisions.length, 0)}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent decisions */}
      <h2 className="text-lg font-semibold text-white mb-4">Recent Decisions</h2>
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </CardContent>
        </Card>
      ) : decisions.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FolderOpen className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 mb-4">No decisions yet. Create your first decision to get started.</p>
            <Link href="/app/decisions">
              <Button>Create a Decision</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {decisions.slice(0, 6).map((d) => (
            <Link key={d.id} href={`/app/decisions/${d.id}`}>
              <Card className="hover:border-cyan/30 transition-colors cursor-pointer h-full">
                <CardContent>
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-white">{d.title}</h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        d.status === "active"
                          ? "bg-green-500/10 text-green-400"
                          : "bg-slate-600/20 text-slate-400"
                      }`}
                    >
                      {d.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 line-clamp-2 mb-3">{d.description || "No description"}</p>
                  <p className="text-xs text-slate-500">Created {formatDate(d.created_at)}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
