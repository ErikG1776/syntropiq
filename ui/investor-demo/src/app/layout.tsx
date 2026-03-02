import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Syntropiq | Autonomous AI Governance",
  description:
    "Live demonstration of recursive AI governance, trust-based agent routing, and autonomous drift containment.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-background antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
