import Link from "next/link";
import { CompanyDossierPanel } from "@/components/company-dossier-panel";
import { DraftEditor } from "@/components/draft-editor";
import { EvaluationPanel } from "@/components/evaluation-panel";
import { OfferPanel } from "@/components/offer-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDraft, getProfile } from "@/lib/api";
import type { DraftDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

const DEFAULT_PS =
  "P.D.: Gestiono mi búsqueda con un sistema propio de agentes que prepara " +
  "borradores; reviso, edito y envío todo personalmente.";

interface ProfileExperience {
  company?: string;
  role?: string;
  start_date?: string;
  end_date?: string | null;
  achievements?: string[];
}

interface ProfileShape {
  experiences?: ProfileExperience[];
  ps_asistencia_ia?: string;
}

function ExperiencesPanel({ experiences }: { experiences: ProfileExperience[] }) {
  if (!experiences.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Experiencias destacadas</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {experiences.map((exp, i) => (
          <div key={`${exp.company}-${i}`} className="text-sm">
            <div className="font-medium">
              {exp.role} — {exp.company}
            </div>
            <div className="text-xs text-muted-foreground">
              {exp.start_date} – {exp.end_date ?? "actualidad"}
            </div>
            {exp.achievements && exp.achievements.length > 0 && (
              <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                {exp.achievements.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default async function DraftDetailPage({
  params,
}: {
  params: Promise<{ username: string; id: string }>;
}) {
  const { username, id } = await params;
  const draftId = Number(id);

  if (!Number.isInteger(draftId)) {
    return <p className="text-sm text-muted-foreground">Borrador no válido.</p>;
  }

  let draft: DraftDetail;
  try {
    draft = await getDraft(draftId);
  } catch (e) {
    return (
      <p className="text-sm text-muted-foreground">
        No se pudo cargar el borrador ({(e as Error).message}).
      </p>
    );
  }

  let profile: ProfileShape = {};
  try {
    profile = (await getProfile(username)) as ProfileShape;
  } catch {
    // Non-fatal — experiences/P.S. fall back to defaults.
  }

  const psDefault = profile.ps_asistencia_ia ?? DEFAULT_PS;

  return (
    <div className="flex flex-col gap-4 pb-4">
      <Link
        href={`/${username}/drafts`}
        className="text-sm text-muted-foreground hover:underline"
      >
        ← Volver a borradores
      </Link>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <OfferPanel offer={draft.offer} />
          <CompanyDossierPanel company={draft.company} />
          <EvaluationPanel evaluation={draft.evaluation} />
          <ExperiencesPanel experiences={profile.experiences ?? []} />
        </div>

        <div className="flex flex-col gap-4">
          <DraftEditor draft={draft} username={username} psDefault={psDefault} />
        </div>
      </div>
    </div>
  );
}
