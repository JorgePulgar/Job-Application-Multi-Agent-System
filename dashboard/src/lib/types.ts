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

export interface CompanyOut {
  id: number;
  nombre: string;
  website: string | null;
  sector: string | null;
  descripcion: string | null;
  dossier_json: unknown;
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
