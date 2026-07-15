import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Khai Hoan Ads Dashboard",
  description: "Campaign tracking dashboard for Khai Hoan ads operations"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
