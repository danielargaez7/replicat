import type { Metadata } from "next";
import { Space_Grotesk, Manrope } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-headline",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const manrope = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Bundlescope",
  description: "AI-Powered Kubernetes Support Bundle Analyzer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${manrope.variable} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-surface text-on-surface font-[var(--font-body)] relative overflow-x-hidden">
        {/* Dynamic Background Layer */}
        <div className="fixed inset-0 z-[-2] overflow-hidden pointer-events-none">
          <div className="absolute inset-0 obsidian-grid opacity-30" />
          <div className="absolute inset-0 fog-overlay" />
          <div
            className="floating-crystal"
            style={{ top: "15%", left: "10%", animation: "float 12s infinite ease-in-out" }}
          />
          <div
            className="floating-crystal"
            style={{ top: "60%", left: "80%", animation: "float 18s infinite ease-in-out -2s" }}
          />
          <div
            className="floating-crystal"
            style={{
              top: "80%",
              left: "20%",
              animation: "float 15s infinite ease-in-out -5s",
              width: "100px",
              height: "100px",
            }}
          />
          <div
            className="floating-crystal"
            style={{
              top: "30%",
              left: "70%",
              animation: "float 20s infinite ease-in-out -7s",
              width: "200px",
              height: "200px",
            }}
          />
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full blur-[120px]" style={{ background: "rgba(255, 100, 180, 0.08)" }} />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full blur-[120px]" style={{ background: "rgba(160, 100, 255, 0.08)" }} />
        </div>

        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
