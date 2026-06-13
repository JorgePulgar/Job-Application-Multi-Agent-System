import { OfferFilters } from "@/components/offer-filters";
import { OfferCard, OfferRow } from "@/components/offer-list-row";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getOfferCounts, getOffers } from "@/lib/api";
import type { OfferCounts, OfferListItem, OfferListResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function OffersPage({
  params,
  searchParams,
}: {
  params: Promise<{ username: string }>;
  searchParams: SearchParams;
}) {
  const { username } = await params;
  const sp = await searchParams;

  const bucket = one(sp.bucket); // "" / undefined = todas
  const estado = one(sp.estado);
  const plataforma = one(sp.plataforma);
  const q = one(sp.q);

  let data: OfferListResponse | null = null;
  let counts: OfferCounts | null = null;
  let apiError = false;
  try {
    [data, counts] = await Promise.all([
      getOffers(username, { bucket, estado, plataforma, q, per_page: 200 }),
      getOfferCounts(username),
    ]);
  } catch {
    apiError = true;
  }

  const items: OfferListItem[] = data?.items ?? [];
  const buckets = {
    sin_analizar: counts?.buckets?.sin_analizar ?? 0,
    analizadas: counts?.buckets?.analizadas ?? 0,
    total: counts?.total ?? 0,
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Ofertas</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total} {data.total === 1 ? "oferta" : "ofertas"}
          </span>
        )}
      </div>

      {!apiError && <OfferFilters buckets={buckets} />}

      {apiError ? (
        <p className="text-sm text-muted-foreground">
          API no disponible — asegúrate de que{" "}
          <code className="font-mono text-xs">uvicorn api.main:app</code> está
          ejecutándose.
        </p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No hay ofertas para este filtro.
        </p>
      ) : (
        <>
          {/* Desktop: table */}
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Oferta</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead>Plataforma</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Detectada</TableHead>
                  <TableHead>Enlace</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <OfferRow key={item.id} item={item} username={username} />
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile: cards */}
          <div className="flex flex-col gap-2 md:hidden">
            {items.map((item) => (
              <OfferCard key={item.id} item={item} username={username} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
