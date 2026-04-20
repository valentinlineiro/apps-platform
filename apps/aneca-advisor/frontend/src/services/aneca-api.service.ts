import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Article {
  tipo: string;
  titulo: string;
  revista: string;
  cuartil: string;
  posicion: string;
  es_corresponding: boolean;
  num_autores: number;
  citas: number;
  roles: string[];
  score?: number;
  es_riesgo?: boolean;
}

export interface EvaluateParams {
  field_key: string;
  figura: string;
  sexenios: number;
  horas: number;
  docentia: string;
  expediente: Article[];
  sexenio_transferencia: boolean;
  patentes: number;
  spin_offs: number;
  contratos_art83: number;
  divulgacion: boolean;
}

export interface EvaluationResult {
  apto: boolean;
  fast_track: boolean;
  detalle: {
    field_label: string;
    figura: string;
    investigacion: {
      ok: boolean; fast_track: boolean; sexenios: number;
      min_sexenios: number; validos: number | null; min_validos: number;
    };
    docencia: {
      ok: boolean; horas: number; min_horas: number; horas_ok: boolean;
      docentia: string; min_docentia: string; docentia_ok: boolean;
    };
    transferencia: {
      ok: boolean; points: number; min_points: number;
      sexenio_transferencia: boolean; patentes: number;
      spin_offs: number; contratos_art83: number; divulgacion: boolean;
    };
    compensacion: { ok: boolean; min_validos: number };
  };
  action_plan: { priority: string; title: string; why: string }[];
  explainability: {
    decision: string; decision_path: string; research_reason: string;
    teaching_reason: string; transfer_reason: string; compensation_reason: string;
  };
}

@Injectable({ providedIn: 'root' })
export class AnecaApiService {
  private http = inject(HttpClient);

  getFields(): Observable<Record<string, string>> {
    return this.http.get<Record<string, string>>('/api/aneca/fields');
  }

  getArticles(): Observable<Article[]> {
    return this.http.get<Article[]>('/api/aneca/articles');
  }

  putArticles(articles: Article[]): Observable<Article[]> {
    return this.http.put<Article[]>('/api/aneca/articles', articles);
  }

  syncOrcid(orcidId: string): Observable<Article[]> {
    return this.http.post<Article[]>('/api/aneca/orcid/sync', { orcid_id: orcidId });
  }

  evaluate(params: EvaluateParams): Observable<EvaluationResult> {
    return this.http.post<EvaluationResult>('/api/aneca/evaluate', params);
  }
}
