import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getProfile } from "@/lib/api";

export const dynamic = "force-dynamic";

interface Experience {
  company?: string;
  role?: string;
  start_date?: string;
  end_date?: string | null;
  achievements?: string[];
  technologies?: string[];
}

interface Education {
  institution?: string;
  degree?: string;
  start_date?: string;
  end_date?: string | null;
}

interface Certification {
  name?: string;
  issuer?: string;
  date?: string;
}

interface LocationPreference {
  modality?: string;
  cities?: string[];
}

interface Profile {
  nombre?: string;
  email?: string;
  phone?: string;
  location?: string;
  github_url?: string;
  linkedin_url?: string;
  target_roles?: string[];
  target_sectors?: string[];
  tech_stack?: string[];
  languages?: string[];
  min_salary?: number;
  location_preference?: LocationPreference;
  red_flags?: string[];
  cv_summary?: string;
  experiences?: Experience[];
  education?: Education[];
  certifications?: Certification[];
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">{children}</CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value?: string | number }) {
  if (value === undefined || value === "") return null;
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="break-words">{value}</dd>
    </div>
  );
}

function Chips({ items }: { items?: string[] }) {
  if (!items?.length) return <span className="text-muted-foreground">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((it) => (
        <Badge key={it} variant="outline">
          {it}
        </Badge>
      ))}
    </div>
  );
}

export default async function SettingsPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;

  let profile: Profile;
  try {
    profile = (await getProfile(username)) as Profile;
  } catch (e) {
    return (
      <p className="text-sm text-muted-foreground">
        No se pudo cargar el perfil ({(e as Error).message}).
      </p>
    );
  }

  const pref = profile.location_preference ?? {};

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Ajustes</h1>

      <p className="rounded-md border border-dashed bg-muted/40 p-3 text-sm text-muted-foreground">
        Para editar, modifica{" "}
        <code className="font-mono text-xs">
          config/users/{username}.yaml
        </code>{" "}
        y vuelve a ejecutar <code className="font-mono text-xs">profile load</code>.
      </p>

      <Section title="Datos personales">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="Nombre" value={profile.nombre} />
          <Field label="Email" value={profile.email} />
          <Field label="Teléfono" value={profile.phone} />
          <Field label="Ubicación" value={profile.location} />
          <Field label="GitHub" value={profile.github_url} />
          <Field label="LinkedIn" value={profile.linkedin_url} />
        </dl>
      </Section>

      <Section title="Objetivos">
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Roles objetivo</p>
          <Chips items={profile.target_roles} />
        </div>
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Sectores objetivo</p>
          <Chips items={profile.target_sectors} />
        </div>
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Stack tecnológico</p>
          <Chips items={profile.tech_stack} />
        </div>
      </Section>

      <Section title="Idiomas">
        <Chips items={profile.languages} />
      </Section>

      <Section title="Preferencias">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="Modalidad" value={pref.modality} />
          <Field
            label="Salario mínimo"
            value={
              profile.min_salary
                ? `${profile.min_salary.toLocaleString("es-ES")} €/año`
                : undefined
            }
          />
        </dl>
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Ciudades</p>
          <Chips items={pref.cities} />
        </div>
      </Section>

      <Section title="Red flags">
        <Chips items={profile.red_flags} />
      </Section>

      <Section title="Resumen CV">
        <p className="whitespace-pre-wrap break-words">
          {profile.cv_summary ?? "—"}
        </p>
      </Section>

      <Section title="Experiencias">
        {profile.experiences?.length ? (
          profile.experiences.map((exp, i) => (
            <div key={`${exp.company}-${i}`} className="border-b pb-3 last:border-0 last:pb-0">
              <div className="font-medium">
                {exp.role} — {exp.company}
              </div>
              <div className="text-xs text-muted-foreground">
                {exp.start_date} – {exp.end_date ?? "actualidad"}
              </div>
              {exp.achievements?.length ? (
                <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                  {exp.achievements.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              ) : null}
              {exp.technologies?.length ? (
                <div className="mt-1">
                  <Chips items={exp.technologies} />
                </div>
              ) : null}
            </div>
          ))
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </Section>

      <Section title="Educación">
        {profile.education?.length ? (
          <ul className="flex flex-col gap-2">
            {profile.education.map((edu, i) => (
              <li key={`${edu.institution}-${i}`}>
                <span className="font-medium">{edu.degree}</span> — {edu.institution}
                <span className="text-xs text-muted-foreground">
                  {" "}
                  ({edu.start_date} – {edu.end_date ?? "actualidad"})
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </Section>

      <Section title="Certificaciones">
        {profile.certifications?.length ? (
          <ul className="flex flex-col gap-2">
            {profile.certifications.map((cert, i) => (
              <li key={`${cert.name}-${i}`}>
                <span className="font-medium">{cert.name}</span> — {cert.issuer}
                <span className="text-xs text-muted-foreground"> ({cert.date})</span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </Section>
    </div>
  );
}
