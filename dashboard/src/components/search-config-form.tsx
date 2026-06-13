"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { putSearchConfig } from "@/lib/api";
import type { SearchConfig } from "@/lib/types";

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

/** Editable list of strings rendered as removable chips + an add input. */
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

/**
 * Editable search-config form. Mirrors the server allow-list (roles, sectors,
 * seniority, location, salary) — CV/experiences are never edited here. Persists
 * via PUT /search-config; server validation errors surface as toasts.
 */
export function SearchConfigForm({
  username,
  initial,
}: {
  username: string;
  initial: SearchConfig;
}) {
  const router = useRouter();
  const [roles, setRoles] = useState<string[]>(initial.target_roles);
  const [sectors, setSectors] = useState<string[]>(initial.target_sectors);
  const [experience, setExperience] = useState<string>(
    initial.experience_level ?? "",
  );
  const [modality, setModality] = useState<string>(
    initial.location_preference.modality,
  );
  const [cities, setCities] = useState<string[]>(
    initial.location_preference.cities,
  );
  const [salary, setSalary] = useState<string>(
    initial.min_salary != null ? String(initial.min_salary) : "",
  );
  const [busy, setBusy] = useState(false);

  async function handleSave() {
    // Client guards mirroring the server validators.
    if (roles.length === 0) {
      toast.error("Añade al menos un rol objetivo");
      return;
    }
    let minSalary: number | null = null;
    if (salary.trim() !== "") {
      const n = Number(salary);
      if (!Number.isFinite(n) || n <= 0) {
        toast.error("El salario mínimo debe ser un número positivo");
        return;
      }
      minSalary = Math.trunc(n);
    }

    const body: SearchConfig = {
      target_roles: roles,
      target_sectors: sectors,
      experience_level: experience === "" ? null : experience,
      location_preference: { modality, cities },
      min_salary: minSalary,
    };

    setBusy(true);
    try {
      await putSearchConfig(username, body);
      toast.success("Configuración de búsqueda guardada");
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo guardar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Búsqueda</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <ListInput
          label="Roles objetivo"
          items={roles}
          onChange={setRoles}
          placeholder="p. ej. ML Engineer"
        />
        <ListInput
          label="Sectores objetivo"
          items={sectors}
          onChange={setSectors}
          placeholder="p. ej. Fintech"
        />

        <div className="flex flex-col gap-2">
          <span className="text-xs text-muted-foreground">Experiencia</span>
          <select
            className={SELECT_CLASS}
            value={experience}
            onChange={(e) => setExperience(e.target.value)}
          >
            {EXPERIENCE_OPTS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs text-muted-foreground">Modalidad</span>
          <select
            className={SELECT_CLASS}
            value={modality}
            onChange={(e) => setModality(e.target.value)}
          >
            {MODALITY_OPTS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <ListInput
          label="Ciudades"
          items={cities}
          onChange={setCities}
          placeholder="p. ej. Madrid"
        />

        <div className="flex flex-col gap-2">
          <span className="text-xs text-muted-foreground">
            Salario mínimo (€/año, opcional)
          </span>
          <Input
            inputMode="numeric"
            value={salary}
            onChange={(e) => setSalary(e.target.value)}
            placeholder="p. ej. 50000"
          />
        </div>

        <Button onClick={handleSave} disabled={busy} className="self-start">
          Guardar configuración
        </Button>
      </CardContent>
    </Card>
  );
}
