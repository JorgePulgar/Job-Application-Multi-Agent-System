"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUsers } from "@/lib/api";
import type { UserOut } from "@/lib/types";
import { setCurrentUser } from "@/lib/user";

type Status = "loading" | "ready" | "error";

/**
 * Landing-page user picker.
 *
 * Fetches the configured users, renders one card per user, and on selection
 * persists the choice to localStorage before redirecting to that user's
 * drafts. Handles loading, error (API down) and empty states.
 */
export function UserPicker() {
  const router = useRouter();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    let active = true;
    getUsers()
      .then((u) => {
        if (!active) return;
        setUsers(u);
        setStatus("ready");
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, []);

  function selectUser(username: string) {
    setCurrentUser(username);
    router.push(`/${username}/drafts`);
  }

  if (status === "loading") {
    return (
      <p className="text-sm text-muted-foreground">Cargando usuarios…</p>
    );
  }

  if (status === "error") {
    return (
      <p className="max-w-xs text-center text-sm text-muted-foreground">
        API no disponible — asegúrate de que{" "}
        <code className="font-mono text-xs">uvicorn api.main:app</code> está
        ejecutándose.
      </p>
    );
  }

  if (users.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No hay usuarios configurados.
      </p>
    );
  }

  return (
    <div className="flex w-full max-w-xs flex-col gap-3">
      <p className="mb-1 text-center text-sm text-muted-foreground">
        Selecciona un usuario para continuar
      </p>
      {users.map((u) => (
        <button
          key={u.username}
          onClick={() => selectUser(u.username)}
          className="flex flex-col items-center justify-center gap-1 rounded-lg border border-input bg-card px-6 py-6 text-lg font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          {u.nombre}
          <span className="text-xs font-normal text-muted-foreground">
            @{u.username}
          </span>
        </button>
      ))}
    </div>
  );
}
