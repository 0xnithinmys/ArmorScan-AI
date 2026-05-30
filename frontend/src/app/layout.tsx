import type { Metadata } from "next";
import { Suspense } from "react";
import { IBM_Plex_Mono, Libre_Baskerville } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "./lib/auth-context";
import Navbar from "./components/navbar";
import { ScanlineOverlay } from "./components/ui";

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
});

const serif = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: "ArmorScan AI — Security Intelligence Platform",
  description:
    "Autonomous AI-driven vulnerability scanning with ArmorIQ policy governance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${mono.variable} ${serif.variable}`}>
      <body className="bg-[#04080f] text-white antialiased">
        <AuthProvider>
          <ScanlineOverlay />
          <Navbar />
          <div className="pt-14">
            <Suspense
              fallback={
                <div className="flex min-h-screen items-center justify-center bg-[#04080f]">
                  <div className="text-center">
                    <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-[#a8ff3e]" />
                    <p className="mt-4 font-mono text-xs text-white/30">Loading...</p>
                  </div>
                </div>
              }
            >
              {children}
            </Suspense>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}