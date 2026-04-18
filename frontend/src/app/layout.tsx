import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { Providers } from "@/app/providers";
import "@/app/globals.css";
import "cesium/Build/Cesium/Widgets/widgets.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Orbital Risk Command",
  description: "Enterprise mission-control console for conjunction analysis and collision prediction."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable} font-[var(--font-sans)] mission-backdrop`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
