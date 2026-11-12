import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
export const metadata: Metadata = {
  title: {
    default: "CodePulse — Open-source intelligence",
    template: "%s · CodePulse",
  },
  description:
    "Discover open-source projects gaining unusual traction. Real GitHub observations and explainable momentum.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
