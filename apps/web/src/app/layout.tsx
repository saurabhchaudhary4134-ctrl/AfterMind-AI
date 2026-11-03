import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/providers/auth-context";
import { WorkspaceProvider } from "@/components/providers/workspace-context";
import { ToastProvider } from "@/components/ui/toast";

export const metadata: Metadata = {
  title: "AfterMind AI — Decision Intelligence Platform",
  description: "Understand the consequences of decisions before you act.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <AuthProvider>
          <WorkspaceProvider>
            <ToastProvider>{children}</ToastProvider>
          </WorkspaceProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
