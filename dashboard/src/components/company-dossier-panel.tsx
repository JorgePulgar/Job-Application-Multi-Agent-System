import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CompanyDossier, CompanyOut } from "@/lib/types";

function TagList({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-1">
        {items.map((it) => (
          <Badge key={it} variant="outline">
            {it}
          </Badge>
        ))}
      </div>
    </div>
  );
}

/** Company dossier panel rendering the structured CompanyResearcher output. */
export function CompanyDossierPanel({ company }: { company: CompanyOut | null }) {
  if (!company) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Empresa</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sin investigación de empresa para esta oferta.
          </p>
        </CardContent>
      </Card>
    );
  }

  const d = company.dossier_json as CompanyDossier | null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{company.nombre}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-1 text-xs text-muted-foreground">
          {(d?.sector ?? company.sector) && (
            <Badge variant="secondary">{d?.sector ?? company.sector}</Badge>
          )}
          {d?.tamano && <Badge variant="secondary">{d.tamano}</Badge>}
          {d?.ubicacion_hq && <Badge variant="secondary">{d.ubicacion_hq}</Badge>}
          {d?.equipo_ai_detectado && <Badge variant="default">Equipo AI</Badge>}
        </div>

        {(d?.descripcion ?? company.descripcion) && (
          <p className="whitespace-pre-wrap text-sm">
            {d?.descripcion ?? company.descripcion}
          </p>
        )}

        {company.website && (
          <a
            href={company.website}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            {company.website} ↗
          </a>
        )}

        {d && (
          <>
            <TagList label="Stack tecnológico" items={d.stack_tecnologico} />
            <TagList label="Productos / servicios" items={d.productos_o_servicios} />
            <TagList label="Cultura" items={d.cultura_notas} />
            <TagList label="Red flags" items={d.red_flags_detectadas} />

            {d.fuentes?.length > 0 && (
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Fuentes</p>
                <ul className="flex flex-col gap-0.5">
                  {d.fuentes.map((url) => (
                    <li key={url}>
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary underline-offset-4 hover:underline break-all"
                      >
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
