import { DraftFilters } from "@/components/draft-filters";
import { DraftCard, DraftRow } from "@/components/draft-list-row";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getDrafts } from "@/lib/api";
import type { DraftListItem, DraftListResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function DraftsPage({
  params,
  searchParams,
}: {
  params: Promise<{ username: string }>;
  searchParams: SearchParams;
}) {
  const { username } = await params;
  const sp = await searchParams;

  const stateRaw = one(sp.state) ?? "draft_ready";
  const sort = one(sp.sort) ?? "score";
  const platform = one(sp.platform);
  const sector = one(sp.sector);
  const recomendacion = one(sp.recomendacion);

  // "all" means no server-side state filter; the API maps draft_ready -> pendiente.
  const state =
    stateRaw === "draft_ready" || stateRaw === "needs_manual_context"
      ? stateRaw
      : undefined;

  let data: DraftListResponse | null = null;
  let apiError = false;
  try {
    data = await getDrafts(username, {
      state,
      sort,
      platform,
      sector,
      recomendacion,
    });
  } catch {
    apiError = true;
  }

  // Sector options: distinct sectors across the current state (ignoring other
  // filters) so the dropdown is stable. Low volume — one extra fetch is fine.
  let sectors: string[] = [];
  try {
    const all = await getDrafts(username, { state, per_page: 100 });
    sectors = [
      ...new Set(
        all.items
          .map((i) => i.company_sector)
          .filter((s): s is string => Boolean(s)),
      ),
    ].sort((a, b) => a.localeCompare(b));
  } catch {
    // Non-fatal — leave the sector dropdown with just "todos".
  }

  const items: DraftListItem[] = data?.items ?? [];
  const hrefFor = (id: number) => `/${username}/drafts/${id}`;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Borradores</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total} {data.total === 1 ? "borrador" : "borradores"}
          </span>
        )}
      </div>

      <DraftFilters sectors={sectors} />

      {apiError ? (
        <p className="text-sm text-muted-foreground">
          API no disponible — asegúrate de que{" "}
          <code className="font-mono text-xs">uvicorn api.main:app</code> está
          ejecutándose.
        </p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No hay borradores. Ejecuta una pasada del orquestador.
        </p>
      ) : (
        <>
          {/* Desktop: table */}
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12" />
                  <TableHead>Oferta</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead>Modalidad</TableHead>
                  <TableHead>Puntuación</TableHead>
                  <TableHead>Recomendación</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <DraftRow key={item.id} item={item} href={hrefFor(item.id)} />
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile: cards */}
          <div className="flex flex-col gap-2 md:hidden">
            {items.map((item) => (
              <DraftCard key={item.id} item={item} href={hrefFor(item.id)} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
