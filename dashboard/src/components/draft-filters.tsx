"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

const SELECT_CLASS =
  "h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";

type Opt = { value: string; label: string };

const STATE_OPTS: Opt[] = [
  { value: "draft_ready", label: "Estado: listos" },
  { value: "needs_manual_context", label: "Estado: contexto manual" },
  { value: "all", label: "Estado: todos" },
];

const PLATFORM_OPTS: Opt[] = [
  { value: "", label: "Plataforma: todas" },
  { value: "adzuna", label: "Adzuna" },
  { value: "jooble", label: "Jooble" },
  { value: "wttj", label: "WTTJ" },
];

const RECO_OPTS: Opt[] = [
  { value: "", label: "Recomendación: todas" },
  { value: "solicitar", label: "Solicitar" },
  { value: "considerar", label: "Considerar" },
  { value: "descartar", label: "Descartar" },
];

const SORT_OPTS: Opt[] = [
  { value: "score", label: "Orden: puntuación" },
  { value: "created_at", label: "Orden: fecha" },
  { value: "company", label: "Orden: empresa" },
];

/**
 * Drafts list filter/sort controls. State lives in the URL query string so the
 * server component can read it and the view is shareable/bookmarkable.
 */
export function DraftFilters({ sectors }: { sectors: string[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  }

  const state = searchParams.get("state") ?? "draft_ready";
  const platform = searchParams.get("platform") ?? "";
  const sector = searchParams.get("sector") ?? "";
  const reco = searchParams.get("recomendacion") ?? "";
  const sort = searchParams.get("sort") ?? "score";

  const sectorOpts: Opt[] = [
    { value: "", label: "Sector: todos" },
    ...sectors.map((s) => ({ value: s, label: s })),
  ];

  return (
    <div className="flex flex-wrap gap-2">
      <select
        className={SELECT_CLASS}
        value={state}
        onChange={(e) => update("state", e.target.value)}
      >
        {STATE_OPTS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={SELECT_CLASS}
        value={platform}
        onChange={(e) => update("platform", e.target.value)}
      >
        {PLATFORM_OPTS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={SELECT_CLASS}
        value={sector}
        onChange={(e) => update("sector", e.target.value)}
      >
        {sectorOpts.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={SELECT_CLASS}
        value={reco}
        onChange={(e) => update("recomendacion", e.target.value)}
      >
        {RECO_OPTS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={SELECT_CLASS}
        value={sort}
        onChange={(e) => update("sort", e.target.value)}
      >
        {SORT_OPTS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
