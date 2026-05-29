import Sidebar from "@/components/sidebar";
import AuthHydrator from "@/components/auth-hydrator";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col md:flex-row">
      <AuthHydrator />
      <Sidebar />
      <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
    </div>
  );
}
