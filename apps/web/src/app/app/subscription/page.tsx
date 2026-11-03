"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Check } from "lucide-react";

const tiers = [
  {
    name: "Free",
    description: "Explore the platform with limited quotas.",
    features: ["3 decisions", "100 simulations/month", "Basic charts", "1 workspace"],
    active: true,
  },
  {
    name: "Pro",
    description: "For individual professional use.",
    features: ["Unlimited decisions", "1,000 simulations/month", "Sensitivity analysis", "Report exports"],
    active: false,
  },
  {
    name: "Team",
    description: "Collaborative workspaces with members.",
    features: ["Everything in Pro", "10,000 simulations/month", "Team members", "Scenario comparison"],
    active: false,
  },
  {
    name: "Business",
    description: "Advanced quotas, audit exports, and SSO-ready.",
    features: ["Everything in Team", "100,000 simulations/month", "SSO-ready", "Audit exports"],
    active: false,
  },
];

export default function SubscriptionPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Subscription</h1>
      <p className="text-sm text-slate-400 mb-8">
        Your current plan and available upgrades. Payment integration requires explicit configuration.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {tiers.map((tier) => (
          <Card
            key={tier.name}
            className={tier.active ? "border-cyan/40 bg-cyan/5" : ""}
          >
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {tier.name}
                {tier.active && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-cyan/20 text-cyan">Current</span>
                )}
              </CardTitle>
              <CardDescription>{tier.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                    <Check className="h-4 w-4 text-cyan shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-slate-500 mt-4">
                {tier.active ? "You are on this plan." : "Not yet available — pricing coming soon."}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
