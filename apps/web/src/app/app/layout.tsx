"use client";

import { useAuth } from "@/components/providers/auth-context";
import { useWorkspace } from "@/components/providers/workspace-context";
import { Sidebar } from "@/components/layout/sidebar";
import { CardSkeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const { loading: wsLoading } = useWorkspace();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  if (loading || (!user && !loading)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-navy-950">
        <div className="w-full max-w-2xl space-y-4 px-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-navy-950">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden">
        {wsLoading ? (
          <div className="p-8 space-y-4">
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
