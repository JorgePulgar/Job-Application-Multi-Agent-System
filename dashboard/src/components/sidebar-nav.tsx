"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Briefcase, FileText, Clock, Settings } from "lucide-react";

const NAV_ITEMS = [
  { label: "Ofertas", href: "offers", icon: Briefcase },
  { label: "Borradores", href: "drafts", icon: FileText },
  { label: "Historial", href: "history", icon: Clock },
  { label: "Ajustes", href: "settings", icon: Settings },
];

export function SidebarNav({
  username,
  offersBadge,
}: {
  username: string;
  offersBadge?: number;
}) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
        const path = `/${username}/${href}`;
        const active = pathname === path || pathname.startsWith(`${path}/`);
        const badge = href === "offers" ? offersBadge : undefined;
        return (
          <Link
            key={href}
            href={path}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-accent text-accent-foreground font-medium"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="flex-1">{label}</span>
            {badge !== undefined && badge > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {badge}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
