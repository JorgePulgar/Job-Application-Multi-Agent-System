/** Typed fetch client for the Job Agent FastAPI backend. */

import type {
  DraftDetail,
  DraftListResponse,
  DraftPatchRequest,
  HistoryResponse,
  MarkSentRequest,
  MarkSentResponse,
  OfferCounts,
  OfferListResponse,
  RegenerateResponse,
  UserOut,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export function getUsers(): Promise<UserOut[]> {
  return request<UserOut[]>("/users");
}

// ---------------------------------------------------------------------------
// Drafts list
// ---------------------------------------------------------------------------

export function getDrafts(
  username: string,
  params?: {
    state?: string;
    sort?: string;
    platform?: string;
    sector?: string;
    recomendacion?: string;
    page?: number;
    per_page?: number;
  },
): Promise<DraftListResponse> {
  const q = new URLSearchParams();
  if (params?.state) q.set("state", params.state);
  if (params?.sort) q.set("sort", params.sort);
  if (params?.platform) q.set("platform", params.platform);
  if (params?.sector) q.set("sector", params.sector);
  if (params?.recomendacion) q.set("recomendacion", params.recomendacion);
  if (params?.page) q.set("page", String(params.page));
  if (params?.per_page) q.set("per_page", String(params.per_page));
  const qs = q.toString();
  return request<DraftListResponse>(
    `/users/${username}/drafts${qs ? `?${qs}` : ""}`,
  );
}

// ---------------------------------------------------------------------------
// Offers list (all states, per user)
// ---------------------------------------------------------------------------

export function getOffers(
  username: string,
  params?: {
    estado?: string;
    bucket?: string;
    plataforma?: string;
    q?: string;
    page?: number;
    per_page?: number;
  },
): Promise<OfferListResponse> {
  const qs = new URLSearchParams();
  if (params?.estado) qs.set("estado", params.estado);
  if (params?.bucket) qs.set("bucket", params.bucket);
  if (params?.plataforma) qs.set("plataforma", params.plataforma);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  const s = qs.toString();
  return request<OfferListResponse>(
    `/users/${username}/offers${s ? `?${s}` : ""}`,
  );
}

export function getOfferCounts(username: string): Promise<OfferCounts> {
  return request<OfferCounts>(`/users/${username}/offers/counts`);
}

// ---------------------------------------------------------------------------
// Draft detail + actions
// ---------------------------------------------------------------------------

export function getDraft(draftId: number): Promise<DraftDetail> {
  return request<DraftDetail>(`/drafts/${draftId}`);
}

export function patchDraft(
  draftId: number,
  body: DraftPatchRequest,
): Promise<DraftDetail> {
  return request<DraftDetail>(`/drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function markSent(
  draftId: number,
  body: MarkSentRequest,
): Promise<MarkSentResponse> {
  return request<MarkSentResponse>(`/drafts/${draftId}/mark-sent`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function discardDraft(draftId: number): Promise<{ offer_estado: string }> {
  return request<{ offer_estado: string }>(`/drafts/${draftId}/discard`, {
    method: "POST",
  });
}

export function regenerateDraft(draftId: number): Promise<RegenerateResponse> {
  return request<RegenerateResponse>(`/drafts/${draftId}/regenerate`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

export function getHistory(
  username: string,
  params?: {
    state?: string;
    from?: string;
    to?: string;
    page?: number;
    per_page?: number;
  },
): Promise<HistoryResponse> {
  const q = new URLSearchParams();
  if (params?.state) q.set("state", params.state);
  if (params?.from) q.set("from", params.from);
  if (params?.to) q.set("to", params.to);
  if (params?.page) q.set("page", String(params.page));
  if (params?.per_page) q.set("per_page", String(params.per_page));
  const qs = q.toString();
  return request<HistoryResponse>(
    `/users/${username}/history${qs ? `?${qs}` : ""}`,
  );
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export function getProfile(username: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/users/${username}/profile`);
}
