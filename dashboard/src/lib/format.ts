/** Shared formatting helpers. */

/** Format an ISO datetime string as a short es-ES date, or "—" if absent. */
export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Format a 0–1 ratio as a whole-number percentage. */
export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}
