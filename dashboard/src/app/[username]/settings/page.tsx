import { ProfileForm } from "@/components/profile-form";
import { getProfile } from "@/lib/api";
import type {
  CertificationEntry,
  EducationEntry,
  ExperienceEntry,
  LocationPreferenceIO,
  UserProfileFull,
} from "@/lib/types";

export const dynamic = "force-dynamic";

type RawProfile = Partial<Omit<UserProfileFull, "location_preference">> & {
  location_preference?: Partial<LocationPreferenceIO>;
};

/** Fill in defaults for any optional keys missing from the stored YAML. */
function normalize(raw: Record<string, unknown>, username: string): UserProfileFull {
  const r = raw as RawProfile;
  const loc = r.location_preference ?? {};
  return {
    username: r.username ?? username,
    nombre: r.nombre ?? "",
    email: r.email ?? "",
    phone: r.phone ?? null,
    github_url: r.github_url ?? null,
    linkedin_url: r.linkedin_url ?? null,
    location: r.location ?? "",
    target_roles: r.target_roles ?? [],
    target_sectors: r.target_sectors ?? [],
    tech_stack: r.tech_stack ?? [],
    languages: r.languages ?? [],
    min_salary: r.min_salary ?? null,
    experience_level: r.experience_level ?? null,
    location_preference: {
      modality: loc.modality ?? "remote",
      cities: loc.cities ?? [],
    },
    red_flags: r.red_flags ?? [],
    cv_summary: r.cv_summary ?? "",
    experiences: (r.experiences ?? []).map(
      (e: Partial<ExperienceEntry>): ExperienceEntry => ({
        company: e.company ?? "",
        role: e.role ?? "",
        start_date: e.start_date ?? "",
        end_date: e.end_date ?? null,
        achievements: e.achievements ?? [],
        technologies: e.technologies ?? [],
      }),
    ),
    education: (r.education ?? []).map(
      (e: Partial<EducationEntry>): EducationEntry => ({
        institution: e.institution ?? "",
        degree: e.degree ?? "",
        start_date: e.start_date ?? "",
        end_date: e.end_date ?? null,
      }),
    ),
    certifications: (r.certifications ?? []).map(
      (c: Partial<CertificationEntry>): CertificationEntry => ({
        name: c.name ?? "",
        issuer: c.issuer ?? "",
        date: c.date ?? "",
      }),
    ),
  };
}

export default async function SettingsPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;

  let initial: UserProfileFull;
  try {
    const raw = await getProfile(username);
    initial = normalize(raw, username);
  } catch (e) {
    return (
      <p className="text-sm text-muted-foreground">
        No se pudo cargar el perfil ({(e as Error).message}).
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Ajustes</h1>
      <ProfileForm initial={initial} />
    </div>
  );
}
