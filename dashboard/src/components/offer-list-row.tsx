import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import type { OfferListItem } from "@/lib/types";

const ESTADO_LABEL: Record<string, string> = {
  nueva: "Nueva",
  filtrada: "Filtrada",
  descartada: "Descartada",
  investigada: "Investigada",
  evaluada: "Evaluada",
  borrador_generado: "Con borrador",
  enviada: "Enviada",
  error: "Error",
};

const ESTADO_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  nueva: "outline",
  filtrada: "outline",
  descartada: "secondary",
  investigada: "secondary",
  evaluada: "secondary",
  borrador_generado: "default",
  enviada: "default",
  error: "destructive",
};

function EstadoBadge({ estado }: { estado: string }) {
  return (
    <Badge variant={ESTADO_VARIANT[estado] ?? "outline"}>
      {ESTADO_LABEL[estado] ?? estado}
    </Badge>
  );
}

/** Relative-ish date: just the YYYY-MM-DD slice, locale-stable. */
function shortDate(iso: string): string {
  return iso.slice(0, 10);
}

function draftHref(username: string, item: OfferListItem): string | null {
  return item.has_draft && item.draft_id !== null
    ? `/${username}/drafts/${item.draft_id}`
    : null;
}

/** Desktop table row. */
export function OfferRow({
  item,
  username,
}: {
  item: OfferListItem;
  username: string;
}) {
  const href = draftHref(username, item);
  return (
    <TableRow>
      <TableCell className="max-w-sm whitespace-normal">
        {href ? (
          <Link href={href} className="font-medium hover:underline">
            {item.titulo}
          </Link>
        ) : (
          <span className="font-medium">{item.titulo}</span>
        )}
        <div className="text-xs text-muted-foreground">{item.empresa}</div>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {item.ubicacion ?? "—"}
      </TableCell>
      <TableCell>
        <Badge variant="outline">{item.fuente}</Badge>
      </TableCell>
      <TableCell>
        <span title={item.razon_descarte ?? undefined}>
          <EstadoBadge estado={item.estado} />
        </span>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {shortDate(item.fecha_detectada)}
      </TableCell>
      <TableCell>
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            Ver <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          "—"
        )}
      </TableCell>
    </TableRow>
  );
}

/** Mobile card. */
export function OfferCard({
  item,
  username,
}: {
  item: OfferListItem;
  username: string;
}) {
  const href = draftHref(username, item);
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-input bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        {href ? (
          <Link href={href} className="font-medium leading-snug hover:underline">
            {item.titulo}
          </Link>
        ) : (
          <span className="font-medium leading-snug">{item.titulo}</span>
        )}
        <EstadoBadge estado={item.estado} />
      </div>
      <div className="text-xs text-muted-foreground">{item.empresa}</div>
      <div className="text-xs text-muted-foreground">
        {[item.ubicacion, shortDate(item.fecha_detectada)]
          .filter(Boolean)
          .join(" · ")}
      </div>
      {item.razon_descarte && (
        <div className="text-xs text-muted-foreground italic">
          {item.razon_descarte}
        </div>
      )}
      <div className="mt-1 flex items-center gap-2">
        <Badge variant="outline">{item.fuente}</Badge>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            Ver oferta <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  );
}
