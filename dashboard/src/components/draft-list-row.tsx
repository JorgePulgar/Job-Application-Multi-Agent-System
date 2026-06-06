import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import type { DraftListItem } from "@/lib/types";

/** Best-effort modality inference from free-text title + location. */
export function inferModality(
  titulo: string,
  ubicacion: string | null,
): string | null {
  const hay = `${titulo} ${ubicacion ?? ""}`.toLowerCase();
  if (/\b(remoto|remote|teletrabajo|en remoto)\b/.test(hay)) return "Remoto";
  if (/\b(h[íi]brido|hybrid)\b/.test(hay)) return "Híbrido";
  if (/\b(presencial|on[\s-]?site|oficina)\b/.test(hay)) return "Presencial";
  return null;
}

const RECOMENDACION_LABEL: Record<string, string> = {
  solicitar: "Solicitar",
  considerar: "Considerar",
  descartar: "Descartar",
};

const RECOMENDACION_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive"
> = {
  solicitar: "default",
  considerar: "secondary",
  descartar: "destructive",
};

function scoreVariant(score: number): "default" | "secondary" | "outline" {
  if (score >= 70) return "default";
  if (score >= 40) return "secondary";
  return "outline";
}

/** Square placeholder showing the company initial. */
function LogoPlaceholder({ name }: { name: string }) {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-muted-foreground">
      {name.trim().charAt(0).toUpperCase() || "?"}
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground">—</span>;
  return <Badge variant={scoreVariant(score)}>{score}</Badge>;
}

function RecomendacionBadge({ value }: { value: string | null }) {
  if (!value) return null;
  return (
    <Badge variant={RECOMENDACION_VARIANT[value] ?? "outline"}>
      {RECOMENDACION_LABEL[value] ?? value}
    </Badge>
  );
}

function ManualContextBadge({ estado }: { estado: string }) {
  if (estado !== "needs_manual_context") return null;
  return <Badge variant="destructive">Contexto manual</Badge>;
}

/** Desktop table row. */
export function DraftRow({
  item,
  href,
}: {
  item: DraftListItem;
  href: string;
}) {
  const company = item.company_nombre ?? item.offer_empresa;
  const modality = inferModality(item.offer_titulo, item.offer_ubicacion);
  return (
    <TableRow>
      <TableCell>
        <LogoPlaceholder name={company} />
      </TableCell>
      <TableCell className="max-w-xs whitespace-normal">
        <Link href={href} className="font-medium hover:underline">
          {item.offer_titulo}
        </Link>
        <div className="text-xs text-muted-foreground">{company}</div>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {item.offer_ubicacion ?? "—"}
      </TableCell>
      <TableCell className="text-muted-foreground">{modality ?? "—"}</TableCell>
      <TableCell>
        <ScoreBadge score={item.puntuacion} />
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          <RecomendacionBadge value={item.recomendacion} />
          <ManualContextBadge estado={item.estado} />
        </div>
      </TableCell>
    </TableRow>
  );
}

/** Mobile card. */
export function DraftCard({
  item,
  href,
}: {
  item: DraftListItem;
  href: string;
}) {
  const company = item.company_nombre ?? item.offer_empresa;
  const modality = inferModality(item.offer_titulo, item.offer_ubicacion);
  return (
    <Link
      href={href}
      className="flex gap-3 rounded-lg border border-input bg-card p-3 transition-colors hover:bg-accent/50"
    >
      <LogoPlaceholder name={company} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="font-medium leading-snug">{item.offer_titulo}</div>
        <div className="text-xs text-muted-foreground">{company}</div>
        <div className="text-xs text-muted-foreground">
          {[item.offer_ubicacion, modality].filter(Boolean).join(" · ") || "—"}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <ScoreBadge score={item.puntuacion} />
          <RecomendacionBadge value={item.recomendacion} />
          <ManualContextBadge estado={item.estado} />
        </div>
      </div>
    </Link>
  );
}
