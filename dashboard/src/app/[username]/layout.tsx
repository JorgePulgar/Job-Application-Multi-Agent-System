import { SidebarNav } from "@/components/sidebar-nav";

export default async function UserLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;

  return (
    <div className="flex w-full">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-52 md:flex-col md:border-r md:p-4 md:shrink-0">
        <SidebarNav username={username} />
      </aside>
      <main className="flex-1 p-4 md:p-6">{children}</main>
    </div>
  );
}
