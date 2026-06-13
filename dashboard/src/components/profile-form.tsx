"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { putProfile } from "@/lib/api";
import type {
  CertificationEntry,
  EducationEntry,
  ExperienceEntry,
  UserProfileFull,
} from "@/lib/types";

const SELECT_CLASS =
  "h-9 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";

const EXPERIENCE_OPTS = [
  { value: "", label: "Sin especificar" },
  { value: "junior", label: "Junior (0-2 años)" },
  { value: "mid", label: "Mid (2-5 años)" },
  { value: "senior", label: "Senior (5+ años)" },
];

const MODALITY_OPTS = [
  { value: "remote", label: "Remoto" },
  { value: "hybrid", label: "Híbrido" },
  { value: "onsite", label: "Presencial" },
];

// ---------------------------------------------------------------------------
// Small reusable inputs
// ---------------------------------------------------------------------------

function Labeled({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

/** Editable list of strings: removable chips + an add input. */
function ListInput({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");
  function add() {
    const v = draft.trim();
    if (v && !items.includes(v)) onChange([...items, v]);
    setDraft("");
  }
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.length === 0 && (
          <span className="text-sm text-muted-foreground">—</span>
        )}
        {items.map((it) => (
          <Badge key={it} variant="outline" className="gap-1">
            {it}
            <button
              type="button"
              onClick={() => onChange(items.filter((x) => x !== it))}
              className="ml-1 text-muted-foreground hover:text-foreground"
              aria-label={`Quitar ${it}`}
            >
              ×
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
        />
        <Button type="button" variant="outline" onClick={add}>
          Añadir
        </Button>
      </div>
    </div>
  );
}

/** Optional text input: empty string is stored as null (erased). */
function NullableInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string | null;
  onChange: (next: string | null) => void;
  placeholder?: string;
}) {
  return (
    <Labeled label={label}>
      <Input
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
        placeholder={placeholder}
      />
    </Labeled>
  );
}

// ---------------------------------------------------------------------------
// Array-of-object editors
// ---------------------------------------------------------------------------

function EntryShell({
  title,
  onRemove,
  children,
}: {
  title: string;
  onRemove: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-md border p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{title}</span>
        <Button type="button" variant="ghost" size="xs" onClick={onRemove}>
          Eliminar
        </Button>
      </div>
      {children}
    </div>
  );
}

function ExperiencesEditor({
  items,
  onChange,
}: {
  items: ExperienceEntry[];
  onChange: (next: ExperienceEntry[]) => void;
}) {
  function patch(i: number, p: Partial<ExperienceEntry>) {
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...p } : it)));
  }
  function add() {
    onChange([
      ...items,
      { company: "", role: "", start_date: "", end_date: null, achievements: [], technologies: [] },
    ]);
  }
  return (
    <div className="flex flex-col gap-3">
      {items.map((exp, i) => (
        <EntryShell
          key={i}
          title={`Experiencia ${i + 1}`}
          onRemove={() => onChange(items.filter((_, idx) => idx !== i))}
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Labeled label="Empresa">
              <Input value={exp.company} onChange={(e) => patch(i, { company: e.target.value })} />
            </Labeled>
            <Labeled label="Puesto">
              <Input value={exp.role} onChange={(e) => patch(i, { role: e.target.value })} />
            </Labeled>
            <Labeled label="Inicio (YYYY-MM)">
              <Input
                value={exp.start_date}
                onChange={(e) => patch(i, { start_date: e.target.value })}
              />
            </Labeled>
            <NullableInput
              label="Fin (YYYY-MM, vacío = actualidad)"
              value={exp.end_date}
              onChange={(v) => patch(i, { end_date: v })}
            />
          </div>
          <ListInput
            label="Logros"
            items={exp.achievements}
            onChange={(v) => patch(i, { achievements: v })}
            placeholder="Añade un logro"
          />
          <ListInput
            label="Tecnologías"
            items={exp.technologies}
            onChange={(v) => patch(i, { technologies: v })}
            placeholder="p. ej. Python"
          />
        </EntryShell>
      ))}
      <Button type="button" variant="outline" onClick={add} className="self-start">
        Añadir experiencia
      </Button>
    </div>
  );
}

function EducationEditor({
  items,
  onChange,
}: {
  items: EducationEntry[];
  onChange: (next: EducationEntry[]) => void;
}) {
  function patch(i: number, p: Partial<EducationEntry>) {
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...p } : it)));
  }
  function add() {
    onChange([...items, { institution: "", degree: "", start_date: "", end_date: null }]);
  }
  return (
    <div className="flex flex-col gap-3">
      {items.map((edu, i) => (
        <EntryShell
          key={i}
          title={`Formación ${i + 1}`}
          onRemove={() => onChange(items.filter((_, idx) => idx !== i))}
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Labeled label="Institución">
              <Input
                value={edu.institution}
                onChange={(e) => patch(i, { institution: e.target.value })}
              />
            </Labeled>
            <Labeled label="Título">
              <Input value={edu.degree} onChange={(e) => patch(i, { degree: e.target.value })} />
            </Labeled>
            <Labeled label="Inicio">
              <Input
                value={edu.start_date}
                onChange={(e) => patch(i, { start_date: e.target.value })}
              />
            </Labeled>
            <NullableInput
              label="Fin (vacío = actualidad)"
              value={edu.end_date}
              onChange={(v) => patch(i, { end_date: v })}
            />
          </div>
        </EntryShell>
      ))}
      <Button type="button" variant="outline" onClick={add} className="self-start">
        Añadir formación
      </Button>
    </div>
  );
}

function CertificationsEditor({
  items,
  onChange,
}: {
  items: CertificationEntry[];
  onChange: (next: CertificationEntry[]) => void;
}) {
  function patch(i: number, p: Partial<CertificationEntry>) {
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...p } : it)));
  }
  function add() {
    onChange([...items, { name: "", issuer: "", date: "" }]);
  }
  return (
    <div className="flex flex-col gap-3">
      {items.map((cert, i) => (
        <EntryShell
          key={i}
          title={`Certificación ${i + 1}`}
          onRemove={() => onChange(items.filter((_, idx) => idx !== i))}
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Labeled label="Nombre">
              <Input value={cert.name} onChange={(e) => patch(i, { name: e.target.value })} />
            </Labeled>
            <Labeled label="Emisor">
              <Input value={cert.issuer} onChange={(e) => patch(i, { issuer: e.target.value })} />
            </Labeled>
            <Labeled label="Fecha">
              <Input value={cert.date} onChange={(e) => patch(i, { date: e.target.value })} />
            </Labeled>
          </div>
        </EntryShell>
      ))}
      <Button type="button" variant="outline" onClick={add} className="self-start">
        Añadir certificación
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main form
// ---------------------------------------------------------------------------

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
      <CardContent className="flex flex-col gap-4 text-sm">{children}</CardContent>
    </Card>
  );
}

/**
 * Full profile editor — every field is editable and erasable except `username`
 * (the profile's identity: file name + DB key + offer FKs). Persists the whole
 * profile via PUT /users/{username}/profile; server validation surfaces as toasts.
 */
export function ProfileForm({ initial }: { initial: UserProfileFull }) {
  const router = useRouter();
  const [p, setP] = useState<UserProfileFull>(initial);
  const [busy, setBusy] = useState(false);

  function set(patch: Partial<UserProfileFull>) {
    setP((prev) => ({ ...prev, ...patch }));
  }
  function setLoc(patch: Partial<UserProfileFull["location_preference"]>) {
    setP((prev) => ({
      ...prev,
      location_preference: { ...prev.location_preference, ...patch },
    }));
  }

  async function handleSave() {
    if (!p.nombre.trim() || !p.email.trim() || !p.location.trim()) {
      toast.error("Nombre, email y ubicación son obligatorios");
      return;
    }
    setBusy(true);
    try {
      const saved = await putProfile(p.username, p);
      setP(saved);
      toast.success("Perfil guardado");
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo guardar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Section title="Datos personales">
        <Labeled label="Usuario (no editable)">
          <Input value={p.username} disabled />
        </Labeled>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Labeled label="Nombre">
            <Input value={p.nombre} onChange={(e) => set({ nombre: e.target.value })} />
          </Labeled>
          <Labeled label="Email">
            <Input value={p.email} onChange={(e) => set({ email: e.target.value })} />
          </Labeled>
          <NullableInput
            label="Teléfono"
            value={p.phone}
            onChange={(v) => set({ phone: v })}
          />
          <Labeled label="Ubicación">
            <Input value={p.location} onChange={(e) => set({ location: e.target.value })} />
          </Labeled>
          <NullableInput
            label="GitHub"
            value={p.github_url}
            onChange={(v) => set({ github_url: v })}
          />
          <NullableInput
            label="LinkedIn"
            value={p.linkedin_url}
            onChange={(v) => set({ linkedin_url: v })}
          />
        </div>
      </Section>

      <Section title="Búsqueda">
        <ListInput
          label="Roles objetivo"
          items={p.target_roles}
          onChange={(v) => set({ target_roles: v })}
          placeholder="p. ej. ML Engineer"
        />
        <ListInput
          label="Sectores objetivo"
          items={p.target_sectors}
          onChange={(v) => set({ target_sectors: v })}
          placeholder="p. ej. Fintech"
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Labeled label="Experiencia">
            <select
              className={SELECT_CLASS}
              value={p.experience_level ?? ""}
              onChange={(e) => set({ experience_level: e.target.value || null })}
            >
              {EXPERIENCE_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Labeled>
          <Labeled label="Modalidad">
            <select
              className={SELECT_CLASS}
              value={p.location_preference.modality}
              onChange={(e) => setLoc({ modality: e.target.value })}
            >
              {MODALITY_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Labeled>
          <Labeled label="Salario mínimo (€/año, opcional)">
            <Input
              inputMode="numeric"
              value={p.min_salary === null ? "" : String(p.min_salary)}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "") return set({ min_salary: null });
                const n = Number(v);
                if (Number.isFinite(n)) set({ min_salary: Math.trunc(n) });
              }}
              placeholder="p. ej. 50000"
            />
          </Labeled>
        </div>
        <ListInput
          label="Ciudades"
          items={p.location_preference.cities}
          onChange={(v) => setLoc({ cities: v })}
          placeholder="p. ej. Madrid"
        />
      </Section>

      <Section title="Perfil técnico">
        <ListInput
          label="Stack tecnológico"
          items={p.tech_stack}
          onChange={(v) => set({ tech_stack: v })}
          placeholder="p. ej. Python"
        />
        <ListInput
          label="Idiomas"
          items={p.languages}
          onChange={(v) => set({ languages: v })}
          placeholder="p. ej. Inglés (C1)"
        />
        <ListInput
          label="Red flags"
          items={p.red_flags}
          onChange={(v) => set({ red_flags: v })}
          placeholder="patrón de auto-descarte"
        />
      </Section>

      <Section title="Resumen CV">
        <Textarea
          value={p.cv_summary}
          onChange={(e) => set({ cv_summary: e.target.value })}
          rows={8}
        />
      </Section>

      <Section title="Experiencias">
        <ExperiencesEditor items={p.experiences} onChange={(v) => set({ experiences: v })} />
      </Section>

      <Section title="Educación">
        <EducationEditor items={p.education} onChange={(v) => set({ education: v })} />
      </Section>

      <Section title="Certificaciones">
        <CertificationsEditor
          items={p.certifications}
          onChange={(v) => set({ certifications: v })}
        />
      </Section>

      <Button onClick={handleSave} disabled={busy} className="self-start">
        Guardar perfil
      </Button>
    </div>
  );
}
