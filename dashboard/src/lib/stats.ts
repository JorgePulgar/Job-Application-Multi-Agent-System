/** Pure computation of application-history statistics. */

import type { HistoryItem } from "./types";

const DAY_MS = 86_400_000;

export interface HistoryStatsData {
  sent30: number;
  sent90: number;
  responseRate: number;
  interviewRate: number;
}

function hasResponse(item: HistoryItem): boolean {
  return item.tipo_respuesta !== null && item.tipo_respuesta !== "sin_respuesta";
}

/** Compute volume + rate stats from the full application history. */
export function computeHistoryStats(items: HistoryItem[]): HistoryStatsData {
  const now = Date.now();
  const sent30 = items.filter(
    (i) => now - new Date(i.fecha_envio).getTime() <= 30 * DAY_MS,
  ).length;
  const sent90 = items.filter(
    (i) => now - new Date(i.fecha_envio).getTime() <= 90 * DAY_MS,
  ).length;

  const total = items.length;
  const responded = items.filter(hasResponse).length;
  const interviews = items.filter((i) => i.tipo_respuesta === "en_proceso").length;

  return {
    sent30,
    sent90,
    responseRate: total ? responded / total : 0,
    interviewRate: total ? interviews / total : 0,
  };
}
