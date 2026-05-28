import type { Metadata } from "next";
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
          <div className="pt-14">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}