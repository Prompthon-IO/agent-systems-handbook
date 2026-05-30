import type { Metadata } from "next";

import { AntdRegistry } from "@ant-design/nextjs-registry";

import "antd/dist/reset.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Customer Email Assist Starter",
  description: "Minimal-token Gmail triage, review, and reply dashboard starter.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AntdRegistry>{children}</AntdRegistry>
      </body>
    </html>
  );
}
