"use client";

import { useTheme } from "next-themes";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getUsers } from "@/lib/api";
import type { UserOut } from "@/lib/types";
import { setCurrentUser, useCurrentUser } from "@/lib/user";
import { Button } from "@/components/ui/button";
import { Moon, Sun, Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { SidebarNav } from "@/components/sidebar-nav";

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const username = useCurrentUser();

  const [users, setUsers] = useState<UserOut[]>([]);

  useEffect(() => {
    getUsers()
      .then(setUsers)
      .catch(() => {});
  }, []);

  function handleUserChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value;
    if (next) {
      setCurrentUser(next);
      router.push(`/${next}/drafts`);
    }
  }

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b bg-background px-4">
      {/* Mobile hamburger */}
      <Sheet>
        <SheetTrigger className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground transition-colors">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Menu</span>
        </SheetTrigger>
        <SheetContent side="left" className="w-56 p-4">
          {username && <SidebarNav username={username} />}
        </SheetContent>
      </Sheet>

      <Link href="/" className="font-semibold tracking-tight text-sm mr-auto">
        Job Agent
      </Link>

      {/* User selector */}
      {users.length > 0 && (
        <select
          value={username ?? ""}
          onChange={handleUserChange}
          className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">Select user</option>
          {users.map((u) => (
            <option key={u.username} value={u.username}>
              {u.nombre}
            </option>
          ))}
        </select>
      )}

      {/* Theme toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      >
        <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    </header>
  );
}
