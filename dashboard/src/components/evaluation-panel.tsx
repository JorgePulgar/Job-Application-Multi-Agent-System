import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EvaluationOut } from "@/lib/types";

const RECO_LABEL: Record<string, string> = {
  solicitar: "Solicitar",
  considerar: "Considerar",
  descartar: "Descartar",
};

const RECO_VARIANT: Record<string, "default" | "secondary" | "destructive"> = {
  solicitar: "default",
  considerar: "secondary",
  descartar: "destructive",
};

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((x): x is string => typeof x === "string") : [];
}

function BulletList({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone?: "danger";
}) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <ul className="list-disc pl-5 text-sm">
        {items.map((it) => (
          <li key={it} className={tone === "danger" ? "text-destructive" : undefined}>
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Viability evaluation panel: score, pros/cons, red flags, reasoning. */
export function EvaluationPanel({ evaluation }: { evaluation: EvaluationOut | null }) {
  if (!evaluation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Evaluación</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Sin evaluación.</p>
        </CardContent>
      </Card>
    );
  }

  const ventajas = asStringList(evaluation.pros);
  const contras =
    evaluation.contras && typeof evaluation.contras === "object"
      ? (evaluation.contras as Record<string, unknown>)
      : {};
  const desventajas = asStringList(contras.desventajas ?? evaluation.contras);
  const redFlags = asStringList(contras.red_flags_match);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Evaluación</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{evaluation.puntuacion} / 100</Badge>
          <Badge variant={RECO_VARIANT[evaluation.recomendacion] ?? "outline"}>
            {RECO_LABEL[evaluation.recomendacion] ?? evaluation.recomendacion}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <BulletList label="Ventajas" items={ventajas} />
        <BulletList label="Desventajas" items={desventajas} />
        <BulletList label="Red flags" items={redFlags} tone="danger" />
        {evaluation.razonamiento && (
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Razonamiento</p>
            <p className="whitespace-pre-wrap text-sm">{evaluation.razonamiento}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
