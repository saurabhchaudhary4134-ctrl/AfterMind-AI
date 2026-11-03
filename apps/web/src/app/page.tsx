"use client";

import Link from "next/link";
import { useAuth } from "@/components/providers/auth-context";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);
  useEffect(() => {
    if (mounted && !loading && user) {
      router.replace("/app");
    }
  }, [mounted, loading, user, router]);

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100">
      {/* Nav */}
      <header className="border-b border-border bg-navy-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="text-xl font-bold">
            <span className="text-white">After</span>
            <span className="text-cyan">Mind</span>
            <span className="text-violet"> AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-slate-300 hover:text-white px-4 py-2 rounded-lg transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="text-sm bg-cyan text-navy-950 font-semibold px-4 py-2 rounded-lg hover:bg-cyan-dark transition-colors"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan/10 border border-cyan/20 text-cyan text-xs font-medium mb-8">
          <span className="w-2 h-2 rounded-full bg-cyan animate-pulse" />
          Decision Intelligence Platform
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
          Understand consequences{" "}
          <span className="bg-gradient-to-r from-cyan to-violet bg-clip-text text-transparent">
            before you act
          </span>
        </h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10">
          Model your decisions, run probabilistic simulations, compare scenarios, and track
          forecast accuracy. Make better decisions with clarity, not guesswork.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/register"
            className="px-8 py-3 bg-cyan text-navy-950 font-semibold rounded-lg hover:bg-cyan-dark transition-colors text-base"
          >
            Start for free
          </Link>
          <Link
            href="/onboarding"
            className="px-8 py-3 border border-border text-slate-200 rounded-lg hover:bg-navy-800 transition-colors text-base"
          >
            Try a sample decision →
          </Link>
        </div>
      </section>

      {/* Feature grid */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: "🧬",
              title: "Decision DNA",
              desc: "Define variables with probability distributions, formulas, objectives, and constraints in a structured, validated model.",
            },
            {
              icon: "🎲",
              title: "Monte Carlo Simulation",
              desc: "Run up to 100,000 seeded iterations. Get P5–P95 percentiles, CVaR, downside risk, and reproducible results.",
            },
            {
              icon: "🌪️",
              title: "Sensitivity Analysis",
              desc: "Tornado charts reveal which assumptions drive the most uncertainty — so you focus on what matters.",
            },
            {
              icon: "🔀",
              title: "Scenario Builder",
              desc: "Create named alternatives with assumption overrides. Compare scenarios side-by-side to understand trade-offs.",
            },
            {
              icon: "🤖",
              title: "AI Extraction",
              desc: "Describe your decision in plain language. Our LLM assistant drafts a structured model — you review and confirm.",
            },
            {
              icon: "📊",
              title: "Reality Tracker",
              desc: "Record actual outcomes after the fact to measure forecast accuracy, calibration, and model drift over time.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-border bg-navy-900/60 p-6"
            >
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-slate-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-navy-900/40">
        <div className="max-w-3xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to model your next decision?
          </h2>
          <p className="text-slate-400 mb-8">
            Free to start. No credit card required.
          </p>
          <Link
            href="/register"
            className="px-8 py-3 bg-cyan text-navy-950 font-semibold rounded-lg hover:bg-cyan-dark transition-colors text-base"
          >
            Create your account
          </Link>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between text-sm text-slate-500">
          <span>© 2026 AfterMind AI</span>
          <span>Built with precision. Powered by probability.</span>
        </div>
      </footer>
    </div>
  );
}
