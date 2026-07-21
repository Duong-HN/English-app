import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: {
    default: "LearnMate Admin",
    template: "%s | LearnMate Admin",
  },
  description: "Trung tâm quản trị LearnMate AI.",
  openGraph: {
    title: "LearnMate Admin",
    description: "Vận hành học tập bằng dữ liệu thật.",
    images: ["/og-learnmate-admin.png"],
    locale: "vi_VN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LearnMate Admin",
    description: "Vận hành học tập bằng dữ liệu thật.",
    images: ["/og-learnmate-admin.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
