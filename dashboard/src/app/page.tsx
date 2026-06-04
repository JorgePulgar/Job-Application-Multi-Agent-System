import Link from "next/link";
import { getUsers } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let users: { username: string; nombre: string }[] = [];
  try {
    users = await getUsers();
  } catch {
    // API not running yet — show empty state
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-bold tracking-tight">Job Agent</h1>
      {users.length > 0 ? (
        <div className="flex flex-col gap-2 w-full max-w-xs">
          <p className="text-sm text-muted-foreground text-center mb-2">
            Selecciona un usuario para continuar
          </p>
          {users.map((u) => (
            <Link
              key={u.username}
              href={`/${u.username}/drafts`}
              className="flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              {u.nombre}
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          API no disponible — asegúrate de que{" "}
          <code className="font-mono text-xs">uvicorn api.main:app</code> está
          ejecutándose.
        </p>
      )}
    </main>
  );
}
