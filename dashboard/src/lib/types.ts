/** TypeScript types matching the FastAPI response schemas. */

export interface UserOut {
  id: number;
  username: string;
  nombre: string;
}

export interface DraftListItem {
  id: number;
  estado: string;
  asunto: string | null;
  created_at: string;
  updated_at: string;
  offer_id: number;
  offer_titulo: string;
  offer_empresa: string;
  offer_ubicacion: string | null;
  offer_fuente: string;
  offer_url: string | null;
  offer_estado: string;
  company_nombre: string | null;
  company_sector: string | null;
  puntuacion: number | null;
  recomendacion: string | null;
}

export interface DraftListResponse {
  items: DraftListItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface OfferOut {
  id: number;
  titulo: string;
  empresa: string;
  ubicacion: string | null;
  descripcion: string | null;
  url: string | null;
  fuente: string;
  fecha_publicacion: string | null;
  fecha_detectada: string;
  estado: string;
}

export interface OfferListItem {
  id: number;
  titulo: string;
  empresa: string;
  ubicacion: string | null;
  fuente: string;
  url: string | null;
  fecha_publicacion: string | null;
  fecha_detectada: string;
  estado: string;
  razon_descarte: string | null;
  has_draft: boolean;
  has_evaluation: boolean;
  draft_id: number | null;
}

export interface OfferListResponse {
  items: OfferListItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface OfferCounts {
  counts: Record<string, number>;
  buckets: Record<string, number>;
  total: number;
}

export interface CompanyOut {
  id: number;
  nombre: string;
  website: string | null;
  sector: string | null;
  descripcion: string | null;
  dossier_json: unknown;
}

/** Shape of `companies.dossier_json` (CompanyResearcher output). */
export interface CompanyDossier {
  sector: string;
  tamano: string;
  ubicacion_hq: string;
  descripcion: string;
  stack_tecnologico: string[];
  cultura_notas: string[];
  red_flags_detectadas: string[];
  productos_o_servicios: string[];
  equipo_ai_detectado: boolean;
  fuentes: string[];
}

export interface EvaluationOut {
  id: number;
  puntuacion: number;
  pros: unknown;
  contras: unknown;
  recomendacion: string;
  razonamiento: string | null;
}

export interface ApplicationOut {
  id: number;
  metodo_envio: string;
  fecha_envio: string;
  notas: string | null;
  tipo_respuesta: string | null;
  fecha_respuesta: string | null;
}

export interface DraftDetail {
  id: number;
  estado: string;
  asunto: string | null;
  cuerpo_email: string | null;
  carta_presentacion: string | null;
  intento_num: number;
  created_at: string;
  updated_at: string;
  offer: OfferOut;
  company: CompanyOut | null;
  evaluation: EvaluationOut | null;
  application: ApplicationOut | null;
}

export interface DraftPatchRequest {
  asunto?: string;
  cuerpo_email?: string;
  carta_presentacion?: string;
}

export interface MarkSentRequest {
  method: string;
  notes?: string;
  ps_text?: string;
}

export interface MarkSentResponse {
  application_id: number;
  offer_estado: string;
}

export interface RegenerateResponse {
  draft_id: number;
  estado: string;
  asunto: string | null;
  cuerpo_email: string | null;
  carta_presentacion: string | null;
  needs_manual_context: boolean;
}

export interface HistoryItem {
  application_id: number;
  offer_titulo: string;
  offer_empresa: string;
  offer_fuente: string;
  draft_asunto: string | null;
  metodo_envio: string;
  fecha_envio: string;
  tipo_respuesta: string | null;
  fecha_respuesta: string | null;
  notas: string | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  per_page: number;
}
