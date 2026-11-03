"use client";

import { useState, useEffect, useCallback, use } from "react";
import { useWorkspace } from "@/components/providers/workspace-context";
import { useToast } from "@/components/ui/toast";
import { decisionApi, scenarioApi, simulationApi, outcomeApi } from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, ErrorMessage } from "@/components/ui/input";
import { CardSkeleton } from "@/components/ui/skeleton";
import { formatDate, formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
  ArrowLeft, FileText, FlaskConical, GitBranch, BarChart3, Target, Plus, Play, Copy, Trash2
} from "lucide-react";
import Link from "next/link";
import type { Decision, DecisionVersion, Scenario, SimulationRun } from "@/lib/api/types";

type Tab = "overview" | "assumptions" | "scenarios" | "simulations" | "results" | "reality";

const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: "overview", label: "Overview", icon: FileText },
  { id: "assumptions", label: "Decision DNA", icon: GitBranch },
  { id: "scenarios", label: "Scenarios", icon: FlaskConical },
  { id: "simulations", label: "Simulations", icon: BarChart3 },
  { id: "results", label: "Results", icon: Target },
  { id: "reality", label: "Reality Tracker", icon: Target },
];

export default function DecisionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { activeWorkspace } = useWorkspace();
  const toast = useToast();

  const [decision, setDecision] = useState<Decision | null>(null);
  const [versions, setVersions] = useState<DecisionVersion[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState("");

  const loadAll = useCallback(async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setError("");
    try {
      const [dec, vers, scens] = await Promise.all([
        decisionApi.get(id, activeWorkspace.id),
        decisionApi.listVersions(id, activeWorkspace.id),
        scenarioApi.list(id, activeWorkspace.id),
      ]);
      setDecision(dec);
      setVersions(vers);
      setScenarios(scens);
      try {
        const runsResp = await simulationApi.list(id, activeWorkspace.id);
        setRuns(runsResp.items);
      } catch {
        setRuns([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decision");
    } finally {
      setLoading(false);
    }
  }, [id, activeWorkspace]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !decision) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-red-400">{error || "Decision not found"}</p>
            <Link href="/app/decisions">
              <Button className="mt-4" variant="outline">Back to Decisions</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/app/decisions" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-cyan mb-4">
          <ArrowLeft className="h-4 w-4" /> Back to Decisions
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{decision.title}</h1>
            {decision.objective && (
              <p className="text-sm text-cyan mt-1">Objective: {decision.objective}</p>
            )}
          </div>
          <span className={cn(
            "text-xs px-3 py-1 rounded-full",
            decision.status === "active" ? "bg-green-500/10 text-green-400" : "bg-slate-600/20 text-slate-400",
          )}>
            {decision.status}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border mb-6 overflow-x-auto">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap",
                tab === t.id
                  ? "border-cyan text-cyan"
                  : "border-transparent text-slate-400 hover:text-slate-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {tab === "overview" && <OverviewTab decision={decision} versions={versions} />}
      {tab === "assumptions" && (
        <AssumptionsTab decision={decision} workspaceId={activeWorkspace!.id} onSaved={loadAll} toast={toast} />
      )}
      {tab === "scenarios" && (
        <ScenariosTab decision={decision} workspaceId={activeWorkspace!.id} scenarios={scenarios} onSaved={loadAll} toast={toast} />
      )}
      {tab === "simulations" && (
        <SimulationsTab decision={decision} workspaceId={activeWorkspace!.id} scenarios={scenarios} runs={runs} onSaved={loadAll} toast={toast} />
      )}
      {tab === "results" && (
        <ResultsTab workspaceId={activeWorkspace!.id} runs={runs} toast={toast} />
      )}
      {tab === "reality" && (
        <RealityTab decision={decision} workspaceId={activeWorkspace!.id} toast={toast} />
      )}
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────

function OverviewTab({ decision, versions }: { decision: Decision; versions: DecisionVersion[] }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Description</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-slate-300">{decision.description || "No description provided."}</p>
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-slate-500">Time Horizon:</span> <span className="text-slate-200">{decision.time_horizon_days} days</span></div>
            <div><span className="text-slate-500">Created:</span> <span className="text-slate-200">{formatDate(decision.created_at)}</span></div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Version History</CardTitle></CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <p className="text-sm text-slate-400">No DNA versions yet. Update the Decision DNA to create the first version.</p>
          ) : (
            <div className="space-y-3">
              {versions.map((v) => (
                <div key={v.id} className="flex items-center justify-between border-b border-border pb-3 last:border-0">
                  <div>
                    <span className="text-cyan font-medium">v{v.version_number}</span>
                    <span className="text-sm text-slate-400 ml-3">{v.change_summary || "No change summary"}</span>
                  </div>
                  <span className="text-xs text-slate-500">{formatDate(v.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Assumptions Tab (DNA Editor) ─────────────────────────────

function AssumptionsTab({ decision, workspaceId, onSaved, toast }: {
  decision: Decision; workspaceId: string; onSaved: () => void; toast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const [dnaText, setDnaText] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Load existing DNA if available
    if (decision.current_version_id) {
      decisionApi.listVersions(decision.id, workspaceId).then((versions) => {
        const latest = versions[versions.length - 1];
        if (latest) {
          setDnaText(JSON.stringify(latest.decision_dna, null, 2));
        }
      }).catch(() => {});
    }
  }, [decision, workspaceId]);

  const handleSave = async () => {
    setError("");
    setSaving(true);
    try {
      const dna = JSON.parse(dnaText);
      await decisionApi.updateDna(decision.id, workspaceId, dna, changeSummary);
      toast("Decision DNA saved as new version", "success");
      onSaved();
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Invalid JSON: " + err.message);
      } else {
        setError(err instanceof Error ? err.message : "Failed to save");
      }
    } finally {
      setSaving(false);
    }
  };

  const sampleDna = {
    variables: [
      { name: "revenue", label: "Revenue", unit: "$", distribution: { type: "normal", params: { mean: 100000, std: 20000 } } },
      { name: "costs", label: "Costs", unit: "$", distribution: { type: "normal", params: { mean: 60000, std: 10000 } } },
    ],
    formulas: [
      { name: "profit", expression: "revenue - costs", description: "Profit = Revenue - Costs" },
    ],
    objective: "profit",
    constraints: [],
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Decision DNA Editor</CardTitle>
          <CardDescription>Define variables, distributions, formulas, and the objective. Saving creates a new immutable version.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="dna">Decision DNA (JSON)</Label>
            <textarea
              id="dna"
              value={dnaText}
              onChange={(e) => setDnaText(e.target.value)}
              placeholder={JSON.stringify(sampleDna, null, 2)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-navy-800 text-slate-100 font-mono text-sm min-h-[300px] focus:outline-none focus:ring-2 focus:ring-cyan"
            />
          </div>
          <div>
            <Label htmlFor="summary">Change Summary</Label>
            <Input id="summary" value={changeSummary} onChange={(e) => setChangeSummary(e.target.value)} placeholder="Describe what changed in this version" />
          </div>
          {error && <ErrorMessage>{error}</ErrorMessage>}
          <div className="flex gap-3">
            <Button onClick={handleSave} loading={saving} disabled={!dnaText.trim()}>Save New Version</Button>
            <Button variant="outline" onClick={() => setDnaText(JSON.stringify(sampleDna, null, 2))}>Load Sample</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Scenarios Tab ─────────────────────────────────────────────

function ScenariosTab({ decision, workspaceId, scenarios, onSaved, toast }: {
  decision: Decision; workspaceId: string; scenarios: Scenario[]; onSaved: () => void; toast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await scenarioApi.create(workspaceId, {
        decision_id: decision.id,
        name,
        description: desc,
        assumption_overrides: {},
      });
      toast("Scenario created", "success");
      setName(""); setDesc(""); setShowCreate(false);
      onSaved();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create scenario", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleDuplicate = async (sid: string) => {
    try {
      await scenarioApi.duplicate(sid, workspaceId);
      toast("Scenario duplicated", "success");
      onSaved();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to duplicate", "error");
    }
  };

  const handleDelete = async (sid: string) => {
    if (!confirm("Delete this scenario?")) return;
    try {
      await scenarioApi.delete(sid, workspaceId);
      toast("Scenario deleted", "success");
      onSaved();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to delete", "error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Scenarios</h2>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="h-4 w-4 mr-2" /> New Scenario
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardContent className="space-y-3 pt-6">
            <div>
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Optimistic Growth" />
            </div>
            <div>
              <Label>Description</Label>
              <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="What makes this scenario different?" />
            </div>
            <Button onClick={handleCreate} loading={creating}>Create Scenario</Button>
          </CardContent>
        </Card>
      )}

      {scenarios.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FlaskConical className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 mb-4">No scenarios yet. Create alternative scenarios to compare outcomes.</p>
            <Button onClick={() => setShowCreate(true)}><Plus className="h-4 w-4 mr-2" /> Create First Scenario</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {scenarios.map((s) => (
            <Card key={s.id}>
              <CardContent className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-white">{s.name}</h3>
                  <p className="text-sm text-slate-400">{s.description || "No description"}</p>
                  {Object.keys(s.assumption_overrides).length > 0 && (
                    <p className="text-xs text-cyan mt-1">
                      {Object.keys(s.assumption_overrides).length} override(s) applied
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => handleDuplicate(s.id)}>
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => handleDelete(s.id)}>
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Simulations Tab ───────────────────────────────────────────

function SimulationsTab({ decision, workspaceId, scenarios, runs, onSaved, toast }: {
  decision: Decision; workspaceId: string; scenarios: Scenario[]; runs: SimulationRun[]; onSaved: () => void; toast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const [selectedScenario, setSelectedScenario] = useState("");
  const [iterations, setIterations] = useState(10000);
  const [seed, setSeed] = useState("");
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    if (!selectedScenario) {
      toast("Select a scenario first", "error");
      return;
    }
    setRunning(true);
    try {
      const run = await simulationApi.create(workspaceId, {
        decision_id: decision.id,
        scenario_id: selectedScenario,
        iterations,
        seed: seed ? parseInt(seed) : null,
      });
      toast(`Simulation ${run.status === "completed" ? "completed" : "queued"}`, "success");
      onSaved();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to start simulation", "error");
    } finally {
      setRunning(false);
    }
  };

  const handleCancel = async (runId: string) => {
    try {
      await simulationApi.cancel(runId, workspaceId);
      toast("Simulation cancelled", "info");
      onSaved();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to cancel", "error");
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Run a Simulation</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Scenario</Label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-navy-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan"
            >
              <option value="">Select a scenario...</option>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Iterations</Label>
              <Input type="number" value={iterations} onChange={(e) => setIterations(parseInt(e.target.value) || 10000)} min={1} max={100000} />
            </div>
            <div>
              <Label>Seed (optional)</Label>
              <Input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="Random" />
            </div>
          </div>
          <Button onClick={handleRun} loading={running} disabled={!selectedScenario || scenarios.length === 0}>
            <Play className="h-4 w-4 mr-2" /> Run Simulation
          </Button>
          {scenarios.length === 0 && (
            <p className="text-sm text-amber-400">Create a scenario first before running a simulation.</p>
          )}
        </CardContent>
      </Card>

      {runs.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Simulation History</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {runs.map((r) => (
                <div key={r.id} className="flex items-center justify-between border-b border-border pb-2 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "text-xs px-2 py-1 rounded-full",
                      r.status === "completed" ? "bg-green-500/10 text-green-400"
                        : r.status === "running" ? "bg-blue-500/10 text-blue-400"
                        : r.status === "failed" ? "bg-red-500/10 text-red-400"
                        : r.status === "cancelled" ? "bg-slate-600/20 text-slate-400"
                        : "bg-slate-600/20 text-slate-400",
                    )}>
                      {r.status}
                    </span>
                    <span className="text-sm text-slate-300">{formatNumber(r.iterations, 0)} iterations</span>
                    <span className="text-xs text-slate-500">seed: {r.seed}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{formatDate(r.created_at)}</span>
                    {r.status === "completed" && (
                      <Link href={`/app/decisions/${decision.id}?run=${r.id}`}>
                        <Button size="sm" variant="ghost">View Results</Button>
                      </Link>
                    )}
                    {(r.status === "queued" || r.status === "running") && (
                      <Button size="sm" variant="ghost" onClick={() => handleCancel(r.id)}>Cancel</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Results Tab ───────────────────────────────────────────────

function ResultsTab({ workspaceId, runs, toast }: {
  workspaceId: string; runs: SimulationRun[]; toast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const completedRuns = runs.filter((r) => r.status === "completed");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [result, setResult] = useState<import("@/lib/api/types").SimulationResult | null>(null);
  const [loadingResult, setLoadingResult] = useState(false);

  useEffect(() => {
    if (completedRuns.length > 0 && !selectedRunId) {
      setSelectedRunId(completedRuns[0].id);
    }
  }, [completedRuns, selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      setResult(null);
      return;
    }
    setLoadingResult(true);
    simulationApi.getResults(selectedRunId, workspaceId).then(setResult).catch(() => setResult(null)).finally(() => setLoadingResult(false));
  }, [selectedRunId, workspaceId]);

  if (completedRuns.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <Target className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No completed simulations yet. Run a simulation to see results here.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <Label>Select Run</Label>
        <select
          value={selectedRunId}
          onChange={(e) => setSelectedRunId(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-navy-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan"
        >
          {completedRuns.map((r) => (
            <option key={r.id} value={r.id}>{formatDate(r.created_at)} — {formatNumber(r.iterations, 0)} iterations</option>
          ))}
        </select>
      </div>

      {loadingResult ? (
        <CardSkeleton />
      ) : result ? (
        <div className="space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Mean" value={formatNumber(result.summary.mean)} />
            <StatCard label="Std Dev" value={formatNumber(result.summary.std)} />
            <StatCard label="P5" value={formatNumber(result.summary.p5)} accent="text-red-400" />
            <StatCard label="P95" value={formatNumber(result.summary.p95)} accent="text-green-400" />
            <StatCard label="P50 (Median)" value={formatNumber(result.summary.p50)} />
            <StatCard label="CVaR 5%" value={formatNumber(result.summary.cvar_5)} accent="text-amber-400" />
            <StatCard label="Min" value={formatNumber(result.summary.min)} />
            <StatCard label="Max" value={formatNumber(result.summary.max)} />
          </div>

          {/* Percentiles */}
          <Card>
            <CardHeader><CardTitle>Percentile Distribution</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(["p5", "p10", "p25", "p50", "p75", "p90", "p95"].map((p) => {
                  const val = result.summary[p];
                  const maxVal = Math.max(...(["p5", "p10", "p25", "p50", "p75", "p90", "p95"].map((k) => Math.abs(result.summary[k]))));
                  const pct = maxVal > 0 ? (Math.abs(val) / maxVal) * 100 : 0;
                  return (
                    <div key={p} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-10">{p.toUpperCase()}</span>
                      <div className="flex-1 h-6 bg-navy-800 rounded relative overflow-hidden">
                        <div
                          className={cn("h-full rounded", p === "p50" ? "bg-cyan" : "bg-violet/60")}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm text-slate-200 w-20 text-right">{formatNumber(val)}</span>
                    </div>
                  );
                }))}
              </div>
            </CardContent>
          </Card>

          {/* Sensitivity Tornado */}
          {result.sensitivity?.variables?.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Sensitivity Analysis (Tornado)</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {result.sensitivity.variables.map((v) => {
                    const maxSens = Math.max(...result.sensitivity.variables.map((s) => Math.abs(s.sensitivity)));
                    const pct = maxSens > 0 ? (Math.abs(v.sensitivity) / maxSens) * 100 : 0;
                    return (
                      <div key={v.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-slate-300">{v.label || v.name}</span>
                          <span className={cn("text-xs", v.direction === "positive" ? "text-green-400" : "text-red-400")}>
                            {v.direction === "positive" ? "↑" : "↓"} {formatNumber(v.sensitivity)}
                          </span>
                        </div>
                        <div className="h-3 bg-navy-800 rounded relative overflow-hidden">
                          <div
                            className={cn("h-full rounded", v.direction === "positive" ? "bg-green-500/60" : "bg-red-500/60")}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Objective + Config */}
          <Card>
            <CardHeader><CardTitle>Run Details</CardTitle></CardHeader>
            <CardContent className="text-sm text-slate-400 space-y-1">
              <p>Objective: <span className="text-cyan">{result.objective}</span></p>
              <p>Iterations: <span className="text-slate-200">{formatNumber(result.iterations, 0)}</span></p>
              <p>Seed: <span className="text-slate-200">{result.seed}</span></p>
              {result.elapsed_seconds && <p>Elapsed: <span className="text-slate-200">{result.elapsed_seconds.toFixed(2)}s</span></p>}
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card><CardContent><p className="text-slate-400">Failed to load results.</p></CardContent></Card>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <Card>
      <CardContent className="text-center py-4">
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        <p className={cn("text-xl font-bold", accent || "text-white")}>{value}</p>
      </CardContent>
    </Card>
  );
}

// ── Reality Tab ───────────────────────────────────────────────

function RealityTab({ decision, workspaceId, toast }: {
  decision: Decision; workspaceId: string; toast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const [outcomes, setOutcomes] = useState<import("@/lib/api/endpoints").ActualOutcome[]>([]);
  const [evaluation, setEvaluation] = useState<import("@/lib/api/endpoints").ForecastEvaluation | null>(null);
  const [metricName, setMetricName] = useState("");
  const [actualValue, setActualValue] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [outs, evalData] = await Promise.all([
          outcomeApi.list(decision.id, workspaceId),
          outcomeApi.forecastEval(decision.id, workspaceId),
        ]);
        setOutcomes(outs);
        setEvaluation(evalData);
      } catch { /* swallow */ }
      finally { setLoading(false); }
    };
    load();
  }, [decision.id, workspaceId]);

  const handleRecord = async () => {
    if (!metricName.trim() || !actualValue.trim()) {
      toast("Metric name and value are required", "error");
      return;
    }
    const value = parseFloat(actualValue);
    if (isNaN(value)) {
      toast("Value must be a number", "error");
      return;
    }
    setSaving(true);
    try {
      await outcomeApi.record(decision.id, workspaceId, {
        metric_name: metricName,
        actual_value: value,
        notes,
      });
      toast("Actual outcome recorded", "success");
      setMetricName(""); setActualValue(""); setNotes("");
      const [outs, evalData] = await Promise.all([
        outcomeApi.list(decision.id, workspaceId),
        outcomeApi.forecastEval(decision.id, workspaceId),
      ]);
      setOutcomes(outs);
      setEvaluation(evalData);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to record outcome", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <CardSkeleton />;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Record Actual Outcome</CardTitle>
          <CardDescription>
            After the decision period has passed, record what actually happened to evaluate forecast accuracy.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Metric Name</Label>
              <Input value={metricName} onChange={(e) => setMetricName(e.target.value)} placeholder="e.g. profit" />
            </div>
            <div>
              <Label>Actual Value</Label>
              <Input type="number" value={actualValue} onChange={(e) => setActualValue(e.target.value)} placeholder="e.g. 385000" />
            </div>
          </div>
          <div>
            <Label>Notes (optional)</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Any context about this measurement" />
          </div>
          <Button onClick={handleRecord} loading={saving}>Record Outcome</Button>
        </CardContent>
      </Card>

      {evaluation && (
        <Card>
          <CardHeader>
            <CardTitle>Forecast Evaluation</CardTitle>
            <CardDescription>{evaluation.limitation_note}</CardDescription>
          </CardHeader>
          {evaluation.metrics.length > 0 && (
            <CardContent>
              <div className="space-y-4">
                {evaluation.metrics.map((m, i) => (
                  <div key={i} className="border-b border-border pb-3 last:border-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-white">{m.metric_name}</span>
                      {m.pct_error != null && (
                        <span className={cn("text-sm font-medium", m.pct_error < 0.15 ? "text-green-400" : m.pct_error < 0.3 ? "text-amber-400" : "text-red-400")}>
                          {(m.pct_error * 100).toFixed(1)}% error
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div><span className="text-slate-400">Actual:</span> <span className="text-white">{formatNumber(m.actual_value)}</span></div>
                      {m.simulated_p50 != null && <div><span className="text-slate-400">Sim P50:</span> <span className="text-violet">{formatNumber(m.simulated_p50)}</span></div>}
                      {m.absolute_error != null && <div><span className="text-slate-400">Abs Error:</span> <span className="text-slate-200">{formatNumber(m.absolute_error)}</span></div>}
                    </div>
                    {m.note && <p className="text-xs text-slate-500 mt-1">{m.note}</p>}
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {outcomes.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Recorded Outcomes</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {outcomes.map((o) => (
                <div key={o.id} className="flex items-center justify-between border-b border-border pb-2 last:border-0">
                  <div>
                    <span className="text-white font-medium">{o.metric_name}</span>
                    {o.notes && <span className="text-slate-400 text-sm ml-2">{o.notes}</span>}
                  </div>
                  <div className="text-right">
                    <span className="text-cyan font-medium">{formatNumber(o.actual_value)}</span>
                    <p className="text-xs text-slate-500">{formatDate(o.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
