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
}
