import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShadowStrangler — Autonomous Legacy-to-Cloud Migration & Live Traffic Diff Swarm",
  description: "Google Cloud Consulting Modernization Engagement — Google ADK 2.0 Closed-Loop Behavioral Verification Workbench",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f8f9fa] text-zinc-900 antialiased selection:bg-blue-100 selection:text-blue-900">
        {children}
      </body>
    </html>
  );
}
