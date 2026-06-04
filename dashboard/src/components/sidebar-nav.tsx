"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { FileText, Clock, Settings } from "lucide-react";

const NAV_ITEMS = [
  { label: "Borradores", href: "drafts", icon: FileText },
  { label: "Historial", href: "history", icon: Clock },
  { label: "Ajustes", href: "settings", icon: Settings },
];

export function SidebarNav({ username }: { username: string }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
        const path = `/${username}/${href}`;
        const active = pathname === path || pathname.startsWith(`${path}/`);
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
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
