import type { Metadata } from "next";
import { headers } from "next/headers";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { ErrorBoundary } from "@/components/error-boundary";
import { OfflineBanner } from "@/components/offline-banner";
import { Providers } from "@/components/providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "maviriq — validate your idea",
  description:
    "5 ai agents research your startup idea and deliver a build or skip verdict",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headersList = await headers();
  const nonce = headersList.get("x-nonce") ?? "";

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} antialiased bg-background text-foreground`}
      >
        <Providers>
          <OfflineBanner />
          <Nav />
          <main className="min-h-screen">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
        </Providers>
      </body>
    </html>
  );
}
