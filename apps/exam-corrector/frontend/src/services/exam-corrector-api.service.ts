import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ExamCorrectorApiService {
  private http = inject(HttpClient);

  listTemplates() {
    return firstValueFrom(
      this.http.get<{ ok: boolean; templates: Array<{ id: string; name: string }> }>(
        '/exam-corrector/api/templates'
      )
    );
  }

  startCorrection(formData: FormData) {
    return firstValueFrom(
      this.http.post<{ ok: boolean; job_id: string; error?: string }>(
        '/exam-corrector/start',
        formData
      )
    );
  }

  getStatus(jobId: string) {
    return firstValueFrom(
      this.http.get<{
        ok: boolean;
        status: string;
        progress?: number;
        message?: string;
        error?: string;
      }>(`/exam-corrector/status/${jobId}`)
    );
  }

  getResult(jobId: string) {
    return firstValueFrom(
      this.http.get<{ ok: boolean; status: string; result?: any; error?: string }>(
        `/exam-corrector/api/result/${jobId}`
      )
    );
  }

  startBatch(formData: FormData) {
    return firstValueFrom(
      this.http.post<{ ok: boolean; batch_id: string; error?: string }>(
        '/exam-corrector/batch/start',
        formData
      )
    );
  }

  getBatchStatus(batchId: string) {
    return firstValueFrom(
      this.http.get<{
        ok: boolean;
        total: number;
        done: number;
        failed: number;
        finished: boolean;
        progress: number;
        current_item: string | null;
        needs_review: number;
        error?: string;
      }>(`/exam-corrector/batch/status/${batchId}`)
    );
  }

  getBatchItems(batchId: string) {
    return firstValueFrom(
      this.http.get<{
        ok: boolean;
        items: Array<{
          filename: string;
          status: string;
          nombre?: string;
          total_puntos?: number;
          max_puntos?: number;
          porcentaje_puntos?: number;
          confidence?: number;
          needs_review?: boolean;
          reviewed?: boolean;
          error?: string;
        }>;
      }>(`/exam-corrector/batch/items/${batchId}`)
    );
  }

  getReviewItems(batchId: string) {
    return firstValueFrom(
      this.http.get<{
        ok: boolean;
        items: Array<{
          idx: number;
          filename: string;
          confidence: number;
          reviewed: boolean;
          nombre: string;
          total_puntos: number;
          max_puntos: number;
          porcentaje_puntos: number;
          feedback: Array<{
            pregunta_label: string;
            respuesta_dada: string;
            respuesta_correcta: string;
            estado: string;
            confianza: number;
          }>;
        }>;
      }>(`/exam-corrector/batch/review/${batchId}`)
    );
  }

  markReviewed(batchId: string, idx: number) {
    return firstValueFrom(
      this.http.post<{ ok: boolean }>(`/exam-corrector/batch/review/${batchId}/${idx}`, {})
    );
  }

  batchResultUrl(batchId: string): string {
    return `/exam-corrector/batch/result/${batchId}`;
  }
}
