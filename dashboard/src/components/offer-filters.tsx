"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

const SELECT_CLASS =
  "h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";

type Opt = { value: string; label: string };

const PLATFORM_OPTS: Opt[] = [
  { value: "", label: "Plataforma: todas" },
  { value: "adzuna", label: "Adzuna" },
  { value: "jooble", label: "Jooble" },
];

const ESTADO_OPTS: Opt[] = [
  { value: "", label: "Estado: todos" },
  { value: "nueva", label: "Nueva" },
  { value: "filtrada", label: "Filtrada" },
  { value: "descartada", label: "Descartada" },
  { value: "evaluada", label: "Evaluada" },
  { value: "borrador_generado", label: "Con borrador" },
  { value: "enviada", label: "Enviada" },
];

/**
 * Scraped-offers filter controls. State lives in the URL query string so the
 * server component reads it and the view is shareable. The bucket chips
 * (todas / sin_analizar / analizadas) are derived server-side from whether an
 * offer has an evaluation, not from its raw estado.
 */
export function OfferFilters({
  buckets,
}: {
  buckets: { sin_analizar: number; analizadas: number; total: number };
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const bucket = searchParams.get("bucket") ?? "";
  const plataforma = searchParams.get("plataforma") ?? "";
  const estado = searchParams.get("estado") ?? "";
  const [q, setQ] = useState(searchParams.get("q") ?? "");

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  }

  const chips: { value: string; label: string; count: number }[] = [
    { value: "", label: "Todas", count: buckets.total },
    { value: "sin_analizar", label: "Sin analizar", count: buckets.sin_analizar },
    { value: "analizadas", label: "Analizadas", count: buckets.analizadas },
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {chips.map((c) => (
          <button
            key={c.value || "todas"}
            type="button"
            onClick={() => update("bucket", c.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-sm transition-colors",
              bucket === c.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            {c.label}
            <span className="ml-1 opacity-70">{c.count}</span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className={SELECT_CLASS}
          value={plataforma}
          onChange={(e) => update("plataforma", e.target.value)}
        >
          {PLATFORM_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          className={SELECT_CLASS}
          value={estado}
          onChange={(e) => update("estado", e.target.value)}
        >
          {ESTADO_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <input
          className={cn(SELECT_CLASS, "min-w-48 flex-1")}
          placeholder="Buscar título o empresa…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") update("q", q.trim());
          }}
          onBlur={() => update("q", q.trim())}
        />
      </div>
    </div>
  );
}
