import { SidebarNav } from "@/components/sidebar-nav";
import { getOfferCounts } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function UserLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;

  // Non-fatal: badge shows the count of unanalyzed offers when the API is up.
  let offersBadge: number | undefined;
  try {
    const counts = await getOfferCounts(username);
    offersBadge = counts.buckets?.sin_analizar;
  } catch {
    offersBadge = undefined;
  }

  return (
    <div className="flex w-full">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-52 md:flex-col md:border-r md:p-4 md:shrink-0">
        <SidebarNav username={username} offersBadge={offersBadge} />
      </aside>
      <main className="flex-1 p-4 md:p-6">{children}</main>
    </div>
  );
}
