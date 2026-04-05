import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl =
    (window as any).__BACKEND_URL__ || 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  listTemplates() {
    return firstValueFrom(
      this.http.get<{ ok: boolean; templates: Array<{ id: string; name: string }> }>(
        `${this.baseUrl}/exam-corrector/api/templates`
      )
    );
  }

  startCorrection(formData: FormData) {
    return firstValueFrom(
      this.http.post<{ ok: boolean; job_id: string; error?: string }>(
        `${this.baseUrl}/exam-corrector/start`,
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
      }>(`${this.baseUrl}/exam-corrector/status/${jobId}`)
    );
  }

  getResult(jobId: string) {
    return firstValueFrom(
      this.http.get<{ ok: boolean; status: string; result?: any; error?: string }>(
        `${this.baseUrl}/exam-corrector/api/result/${jobId}`
      )
    );
  }
}
