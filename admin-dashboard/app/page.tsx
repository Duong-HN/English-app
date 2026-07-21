import type { Metadata } from "next";
import { AdminApp } from "./admin-app";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Bảng điều khiển vận hành và quản trị hệ thống LearnMate AI.",
};

export default function Home() {
  const defaultApiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  return <AdminApp defaultApiBaseUrl={defaultApiBaseUrl} />;
}
