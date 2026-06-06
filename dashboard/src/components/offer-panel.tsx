import { inferModality } from "@/components/draft-list-row";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OfferOut } from "@/lib/types";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

/** Original offer panel: key facts + collapsible full description. */
export function OfferPanel({ offer }: { offer: OfferOut }) {
  const modality = inferModality(offer.titulo, offer.ubicacion) ?? "—";
  return (
    <Card>
      <CardHeader>
        <CardTitle>{offer.titulo}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="Empresa" value={offer.empresa} />
          <Field label="Ubicación" value={offer.ubicacion ?? "—"} />
          <Field label="Modalidad" value={modality} />
          <Field label="Salario" value="—" />
          <Field label="Plataforma" value={offer.fuente} />
        </dl>

        {offer.url && (
          <a
            href={offer.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            Ver oferta original ↗
          </a>
        )}

        {offer.descripcion && (
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground select-none">
              Descripción completa
            </summary>
            <p className="mt-2 whitespace-pre-wrap text-foreground">
              {offer.descripcion}
            </p>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
