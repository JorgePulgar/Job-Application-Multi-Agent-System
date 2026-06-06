import { Card } from "@/components/ui/card";
import { formatPercent } from "@/lib/format";
import { computeHistoryStats } from "@/lib/stats";
import type { HistoryItem } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card className="flex-1 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </Card>
  );
}

/**
 * Top stats strip: volume in the last 30/90 days, response rate, interview
 * rate. Computed from the full (unfiltered) application history.
 */
export function HistoryStats({ items }: { items: HistoryItem[] }) {
  const stats = computeHistoryStats(items);
  return (
    <div className="flex flex-wrap gap-2">
      <Stat label="Enviadas (30 días)" value={String(stats.sent30)} />
      <Stat label="Enviadas (90 días)" value={String(stats.sent90)} />
      <Stat label="Tasa de respuesta" value={formatPercent(stats.responseRate)} />
      <Stat label="Tasa de entrevista" value={formatPercent(stats.interviewRate)} />
    </div>
  );
}
