import Link from "next/link";
import { HistoryStats } from "@/components/history-stats";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getHistory } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { HistoryItem, HistoryResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

const TABS = [
  { value: "applied", label: "Aplicadas" },
  { value: "interview", label: "Entrevistas" },
  { value: "rejected", label: "Rechazos" },
  { value: "hired", label: "Otros" },
] as const;

const TIPO_LABEL: Record<string, string> = {
  sin_respuesta: "Sin respuesta",
  en_proceso: "En proceso",
  negativa: "Negativa",
  positiva: "Positiva",
};

function hasResponse(item: HistoryItem): boolean {
  return item.tipo_respuesta !== null && item.tipo_respuesta !== "sin_respuesta";
}

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function HistoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ username: string }>;
  searchParams: SearchParams;
}) {
  const { username } = await params;
  const sp = await searchParams;
  const state = one(sp.state) ?? "applied";

  let table: HistoryResponse | null = null;
  let all: HistoryItem[] = [];
  let apiError = false;
  try {
    [table, { items: all }] = await Promise.all([
      getHistory(username, { state, per_page: 100 }),
      getHistory(username, { per_page: 100 }),
    ]);
  } catch {
    apiError = true;
  }

  const items = table?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Historial</h1>

      {apiError ? (
        <p className="text-sm text-muted-foreground">
          API no disponible — asegúrate de que{" "}
          <code className="font-mono text-xs">uvicorn api.main:app</code> está
          ejecutándose.
        </p>
      ) : (
        <>
          <HistoryStats items={all} />

          {/* Tabs */}
          <div className="flex flex-wrap gap-1 border-b">
            {TABS.map((tab) => {
              const active = tab.value === state;
              return (
                <Link
                  key={tab.value}
                  href={`/${username}/history?state=${tab.value}`}
                  className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
                    active
                      ? "border-primary font-medium text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </Link>
              );
            })}
          </div>

          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No hay aplicaciones en esta categoría.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Empresa</TableHead>
                  <TableHead>Título</TableHead>
                  <TableHead>Fecha envío</TableHead>
                  <TableHead>Plataforma</TableHead>
                  <TableHead>Respuesta</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Fecha respuesta</TableHead>
                  <TableHead>Notas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.application_id}>
                    <TableCell className="font-medium">{item.offer_empresa}</TableCell>
                    <TableCell className="max-w-xs whitespace-normal">
                      {item.offer_titulo}
                    </TableCell>
                    <TableCell>{formatDate(item.fecha_envio)}</TableCell>
                    <TableCell>{item.offer_fuente}</TableCell>
                    <TableCell>{hasResponse(item) ? "Sí" : "No"}</TableCell>
                    <TableCell>
                      {item.tipo_respuesta
                        ? (TIPO_LABEL[item.tipo_respuesta] ?? item.tipo_respuesta)
                        : "—"}
                    </TableCell>
                    <TableCell>{formatDate(item.fecha_respuesta)}</TableCell>
                    <TableCell className="max-w-xs whitespace-normal text-muted-foreground">
                      {item.notas ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </>
      )}
    </div>
  );
}
