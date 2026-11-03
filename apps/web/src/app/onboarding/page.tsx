"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-context";
import { useWorkspace } from "@/components/providers/workspace-context";
import { decisionApi, scenarioApi } from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, ArrowRight, Loader2 } from "lucide-react";

const SAMPLE_DNA = {
  variables: [
    {
      name: "revenue",
      label: "Annual Revenue",
      unit: "$",
      distribution: { type: "normal", params: { mean: 1200000, std: 240000 } },
    },
    {
      name: "costs",
      label: "Annual Costs",
      unit: "$",
      distribution: { type: "normal", params: { mean: 800000, std: 120000 } },
    },
    {
      name: "market_growth",
      label: "Market Growth Rate",
      unit: "%",
      distribution: { type: "triangular", params: { low: 0.02, peak: 0.08, high: 0.20 } },
    },
  ],
  formulas: [
    {
      name: "profit",
      expression: "revenue - costs",
      description: "Gross profit",
    },
    {
      name: "adjusted_profit",
      expression: "profit * (1 + market_growth)",
      description: "Profit adjusted for market growth",
    },
  ],
  objective: "adjusted_profit",
  constraints: [],
};

type Step = "intro" | "creating" | "done" | "error";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { activeWorkspace, loading: wsLoading, refresh } = useWorkspace();
  const [step, setStep] = useState<Step>("intro");
  const [decisionId, setDecisionId] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Redirect to register if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/register?next=/onboarding");
    }
  }, [authLoading, user, router]);

  const handleCreate = async () => {
    if (!activeWorkspace) return;
    setStep("creating");
    setErrorMsg("");
    try {
      // 1. Create the decision
      const decision = await decisionApi.create(activeWorkspace.id, {
        title: "Market Expansion Decision (Sample)",
        description:
          "Should we expand into a new market next year? This sample models revenue, costs, " +
          "and market growth uncertainty to estimate adjusted profit.",
        objective: "Maximize adjusted annual profit",
        time_horizon_days: 365,
      });

      // 2. Set the Decision DNA
      await decisionApi.updateDna(
        decision.id,
        activeWorkspace.id,
        SAMPLE_DNA,
        "Initial DNA from onboarding sample",
      );

      // 3. Create two scenarios
      await Promise.all([
        scenarioApi.create(activeWorkspace.id, {
          decision_id: decision.id,
          name: "Base Case",
          description: "Expected conditions — no overrides",
          assumption_overrides: {},
        }),
        scenarioApi.create(activeWorkspace.id, {
          decision_id: decision.id,
          name: "Pessimistic",
          description: "Lower revenue and higher costs",
          assumption_overrides: {
            revenue: { distribution: { type: "normal", params: { mean: 900000, std: 180000 } } },
            costs: { distribution: { type: "normal", params: { mean: 950000, std: 150000 } } },
          },
        }),
      ]);

      setDecisionId(decision.id);
      setStep("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create sample decision");
      setStep("error");
    }
  };

  if (authLoading || wsLoading) {
    return (
      <div className="min-h-screen bg-navy-950 flex items-center justify-center">
        <Skeleton className="w-96 h-64" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy-950 flex items-center justify-center px-4">
      <Card className="w-full max-w-lg">
        {step === "intro" && (
          <>
            <CardHeader>
              <CardTitle className="text-2xl">Welcome to AfterMind AI</CardTitle>
              <CardDescription>
                Let&apos;s create a sample decision so you can explore the platform in 30 seconds.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                {[
                  "A real decision with three input variables and two formulas",
                  "Two scenarios: Base Case and Pessimistic",
                  "Ready to run a Monte Carlo simulation immediately",
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm text-slate-300">
                    <CheckCircle className="h-5 w-5 text-cyan shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
              <div className="bg-navy-800 rounded-lg p-4 text-sm text-slate-400 border border-border">
                <p className="font-medium text-slate-300 mb-1">Sample: Market Expansion Decision</p>
                <p>Models annual profit with revenue N($1.2M, $240k), costs N($800k, $120k),
                  and market growth Triangular(2%–20%). Objective: maximize adjusted profit.</p>
              </div>
              <div className="flex gap-3">
                <Button onClick={handleCreate} className="flex-1">
                  Create sample decision
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
                <Button variant="outline" onClick={() => router.push("/app")}>
                  Skip
                </Button>
              </div>
            </CardContent>
          </>
        )}

        {step === "creating" && (
          <CardContent className="py-16 text-center space-y-4">
            <Loader2 className="h-12 w-12 text-cyan animate-spin mx-auto" />
            <p className="text-white font-medium">Creating your sample decision…</p>
            <p className="text-sm text-slate-400">Setting up Decision DNA, variables, and scenarios</p>
          </CardContent>
        )}

        {step === "done" && (
          <>
            <CardHeader>
              <CardTitle>Your sample is ready!</CardTitle>
              <CardDescription>
                The Market Expansion Decision has been created with two scenarios and a full
                Decision DNA model. Run a simulation to see it in action.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {[
                  "✓ Decision created with title, objective, and time horizon",
                  "✓ Decision DNA set — 3 variables, 2 formulas, 1 objective",
                  "✓ Base Case scenario created",
                  "✓ Pessimistic scenario created with assumption overrides",
                ].map((item, i) => (
                  <p key={i} className="text-sm text-green-400">{item}</p>
                ))}
              </div>
              <Button
                className="w-full"
                onClick={() => router.push(`/app/decisions/${decisionId}`)}
              >
                Open the decision workspace
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </CardContent>
          </>
        )}

        {step === "error" && (
          <CardContent className="py-12 text-center space-y-4">
            <p className="text-red-400">{errorMsg}</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={() => setStep("intro")}>Try again</Button>
              <Button variant="outline" onClick={() => router.push("/app")}>
                Go to dashboard
              </Button>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
