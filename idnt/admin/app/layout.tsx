import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IDNT Admin",
  description: "IDNT 아이덴트 관리자 포털",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
