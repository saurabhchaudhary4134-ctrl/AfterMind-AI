"use client";

import { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "@/components/providers/workspace-context";
import { useToast } from "@/components/ui/toast";
import { decisionApi } from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CardSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input, Label, ErrorMessage } from "@/components/ui/input";
import { formatDate } from "@/lib/utils";
import { FolderOpen, Plus, AlertCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Decision } from "@/lib/api/types";

export default function DecisionsPage() {
  const { activeWorkspace } = useWorkspace();
  const toast = useToast();
  const router = useRouter();

  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [objective, setObjective] = useState("");
  const [horizon, setHorizon] = useState(365);
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setError("");
    try {
      const resp = await decisionApi.list(activeWorkspace.id);
      setDecisions(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    setFormError("");
    if (!title.trim()) {
      setFormError("Title is required");
      return;
    }
    setCreating(true);
    try {
      const decision = await decisionApi.create(activeWorkspace.id, {
        title,
        description,
        objective,
        time_horizon_days: horizon,
      });
      toast("Decision created", "success");
      router.push(`/app/decisions/${decision.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create decision");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-white">Decisions</h1>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="h-4 w-4 mr-2" />
          New Decision
        </Button>
      </div>

      {showCreate && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create a New Decision</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Should we expand to the European market?"
                  required
                />
              </div>
              <div>
                <Label htmlFor="desc">Description</Label>
                <textarea
                  id="desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the decision and its context..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-navy-800 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan min-h-[80px]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="obj">Objective</Label>
                  <Input
                    id="obj"
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    placeholder="e.g. Maximize net profit"
                  />
                </div>
                <div>
                  <Label htmlFor="horizon">Time Horizon (days)</Label>
                  <Input
                    id="horizon"
                    type="number"
                    value={horizon}
                    onChange={(e) => setHorizon(parseInt(e.target.value) || 365)}
                    min={1}
                  />
                </div>
              </div>
              {formError && <ErrorMessage>{formError}</ErrorMessage>}
              <div className="flex gap-3">
                <Button type="submit" loading={creating}>Create Decision</Button>
                <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton />
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
          <CardContent className="text-center py-16">
            <FolderOpen className="h-16 w-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">No decisions yet</h3>
            <p className="text-slate-400 mb-6 max-w-sm mx-auto">
              Create your first decision to start modeling scenarios, running simulations, and tracking outcomes.
            </p>
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Decision
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {decisions.map((d) => (
            <Link key={d.id} href={`/app/decisions/${d.id}`}>
              <Card className="hover:border-cyan/30 transition-colors cursor-pointer h-full">
                <CardContent>
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-white line-clamp-1">{d.title}</h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${
                        d.status === "active"
                          ? "bg-green-500/10 text-green-400"
                          : d.status === "archived"
                            ? "bg-slate-600/20 text-slate-500"
                            : "bg-slate-600/20 text-slate-400"
                      }`}
                    >
                      {d.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 line-clamp-2 mb-3">
                    {d.description || "No description"}
                  </p>
                  {d.objective && (
                    <p className="text-xs text-cyan mb-2">Objective: {d.objective}</p>
                  )}
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
