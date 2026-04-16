import {
  ChangeDetectionStrategy, Component, inject, resource, signal,
} from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ExamCorrectorApiService } from './services/exam-corrector-api.service';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const BATCH_POLL_TIMEOUT_MS = 60 * 60 * 1000;
const POLL_INTERVAL_MS = 1500;

type Tab = 'single' | 'batch' | 'templates';

@Component({
  selector: 'app-exam-corrector-page',
  standalone: true,
  imports: [FormsModule, DecimalPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './exam-corrector-page.component.html',
  styleUrl: './exam-corrector-page.component.css',
})
export class ExamCorrectorPageComponent {
  private api = inject(ExamCorrectorApiService);

  activeTab = signal<Tab>('single');

  // Single-exam signals
  selectedTemplateId = signal('__upload__');
  templateName = signal('');
  saveTemplate = signal(true);
  templateFile = signal<File | null>(null);
  examFile = signal<File | null>(null);
  loading = signal(false);
  status = signal('');
  progressValue = signal(0);
  result = signal<any>(null);

  // Drop-zone active states
  templateDrop = signal(false);
  examDrop = signal(false);
  batchDrop = signal(false);

  // Batch signals
  batchTemplateId = signal('');
  batchFile = signal<File | null>(null);
  batchLoading = signal(false);
  batchStatus = signal('');
  batchProgress = signal(0);
  batchFinished = signal(false);
  batchId = signal('');
  batchCurrentItem = signal<string | null>(null);
  batchNeedsReview = signal(0);
  batchItems = signal<Array<{
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
  }>>([]);
  reviewItems = signal<Array<{
    idx: number;
    filename: string;
    confidence: number;
    reviewed: boolean;
    nombre: string;
    total_puntos: number;
    max_puntos: number;
    porcentaje_puntos: number;
    feedback: Array<{ pregunta_label: string; respuesta_dada: string; respuesta_correcta: string; estado: string; confianza: number }>;
  }>>([]);
  expandedReviewIdx = signal<number | null>(null);

  // Template tab
  templateDeleteError = signal('');

  templatesResource = resource({
    loader: () => this.api.listTemplates().then(r => r.templates ?? []),
  });

  batchResultUrl(): string {
    return this.api.batchResultUrl(this.batchId());
  }

  // ── File handlers ───────────────────────────────────────

  onTemplateChange(id: string) {
    this.selectedTemplateId.set(id);
    if (id !== '__upload__') this.templateFile.set(null);
  }

  onTemplateFile(ev: Event) {
    this.templateFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
    this.templateDrop.set(false);
  }

  onExamFile(ev: Event) {
    this.examFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
    this.examDrop.set(false);
  }

  onBatchFile(ev: Event) {
    this.batchFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
    this.batchDrop.set(false);
  }

  onTemplateDrop(ev: DragEvent) {
    ev.preventDefault();
    this.templateDrop.set(false);
    const file = ev.dataTransfer?.files?.[0];
    if (file) this.templateFile.set(file);
  }

  onExamDrop(ev: DragEvent) {
    ev.preventDefault();
    this.examDrop.set(false);
    const file = ev.dataTransfer?.files?.[0];
    if (file) this.examFile.set(file);
  }

  onBatchDrop(ev: DragEvent) {
    ev.preventDefault();
    this.batchDrop.set(false);
    const file = ev.dataTransfer?.files?.[0];
    if (file) this.batchFile.set(file);
  }

  // ── Single-exam flow ────────────────────────────────────

  async onSubmit(ev: Event) {
    ev.preventDefault();
    if (!this.examFile()) { this.status.set('Selecciona un examen.'); return; }
    if (this.selectedTemplateId() === '__upload__' && !this.templateFile()) {
      this.status.set('Selecciona una plantilla o usa una guardada.'); return;
    }
    this.loading.set(true);
    this.result.set(null);
    this.progressValue.set(0);
    this.status.set('Subiendo archivos...');
    const fd = new FormData();
    fd.append('examen', this.examFile()!);
    fd.append('template_id', this.selectedTemplateId());
    fd.append('template_name', this.templateName());
    fd.append('save_template', this.saveTemplate() ? '1' : '0');
    const tf = this.templateFile();
    if (tf) fd.append('plantilla', tf);
    try {
      const start = await this.api.startCorrection(fd);
      if (!start.ok || !start.job_id) throw new Error(start.error || 'No se pudo iniciar la corrección.');
      await this.pollJob(start.job_id);
    } catch (e: any) {
      this.status.set(`Error: ${e.message || e}`);
      this.loading.set(false);
    }
  }

  async pollJob(jobId: string) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (true) {
      if (Date.now() > deadline) {
        this.status.set('La corrección tardó demasiado. Por favor inténtalo de nuevo.');
        this.loading.set(false);
        return;
      }
      const s = await this.api.getStatus(jobId);
      if (!s.ok && s.error) throw new Error(s.error);
      if (s.status === 'done') {
        const res = await this.api.getResult(jobId);
        if (!res.ok) throw new Error(res.error || 'No se pudo obtener el resultado.');
        this.result.set(res.result);
        this.progressValue.set(100);
        this.status.set('Corrección completada.');
        this.loading.set(false);
        this.templatesResource.reload();
        return;
      }
      if (s.status === 'error') throw new Error(s.error || 'Error en procesamiento.');
      this.progressValue.set(s.progress ?? 0);
      this.status.set(`${s.progress ?? 0}% · ${s.message || 'Procesando...'}`);
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  // ── Batch flow ──────────────────────────────────────────

  async onBatchSubmit(ev: Event) {
    ev.preventDefault();
    if (!this.batchTemplateId()) { this.batchStatus.set('Selecciona una plantilla guardada.'); return; }
    if (!this.batchFile()) { this.batchStatus.set('Selecciona un archivo PDF o ZIP.'); return; }
    this.batchLoading.set(true);
    this.batchFinished.set(false);
    this.batchProgress.set(0);
    this.batchCurrentItem.set(null);
    this.batchItems.set([]);
    this.reviewItems.set([]);
    this.expandedReviewIdx.set(null);
    this.batchNeedsReview.set(0);
    this.batchStatus.set('Subiendo archivo...');
    const fd = new FormData();
    fd.append('template_id', this.batchTemplateId());
    fd.append('examenes', this.batchFile()!);
    try {
      const start = await this.api.startBatch(fd);
      if (!start.ok || !start.batch_id) throw new Error(start.error || 'No se pudo iniciar el lote.');
      this.batchId.set(start.batch_id);
      await this.pollBatch(start.batch_id);
    } catch (e: any) {
      this.batchStatus.set(`Error: ${e.message || e}`);
      this.batchLoading.set(false);
    }
  }

  async pollBatch(batchId: string) {
    const deadline = Date.now() + BATCH_POLL_TIMEOUT_MS;
    while (true) {
      if (Date.now() > deadline) {
        this.batchStatus.set('El lote tardó demasiado. Recarga la página para ver el estado.');
        this.batchLoading.set(false);
        return;
      }
      const [s, itemsRes] = await Promise.all([
        this.api.getBatchStatus(batchId),
        this.api.getBatchItems(batchId),
      ]);
      if (!s.ok) throw new Error(s.error || 'Error consultando el lote.');
      this.batchProgress.set(s.progress);
      this.batchCurrentItem.set(s.current_item ?? null);
      if (itemsRes.ok) this.batchItems.set(itemsRes.items);
      const failedNote = s.failed > 0 ? `, ${s.failed} con error` : '';
      this.batchStatus.set(`${s.done + s.failed}/${s.total} procesados${failedNote}`);
      this.batchNeedsReview.set(s.needs_review ?? 0);
      if (s.finished) {
        this.batchLoading.set(false);
        this.batchFinished.set(true);
        const reviewNote = s.needs_review ? `, ${s.needs_review} para revisar` : '';
        const summary = `Lote completado: ${s.done} correctos, ${s.failed} errores${reviewNote}.`;
        this.batchStatus.set(summary);
        if (s.needs_review) {
          const rev = await this.api.getReviewItems(batchId);
          if (rev.ok) this.reviewItems.set(rev.items);
        }
        window.dispatchEvent(new CustomEvent('app-toast', {
          bubbles: true,
          detail: { message: summary, type: s.needs_review ? 'warn' : 'ok' },
        }));
        return;
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  async markReviewed(idx: number) {
    await this.api.markReviewed(this.batchId(), idx);
    this.reviewItems.update(items => items.map(i => i.idx === idx ? { ...i, reviewed: true } : i));
    this.batchNeedsReview.update(n => Math.max(0, n - 1));
  }

  toggleReview(idx: number) {
    this.expandedReviewIdx.update(cur => cur === idx ? null : idx);
  }

  // ── Templates tab ───────────────────────────────────────

  async deleteTemplate(id: string) {
    this.templateDeleteError.set('');
    try {
      const res = await this.api.deleteTemplate(id);
      if (!res.ok) { this.templateDeleteError.set('No se pudo eliminar la plantilla.'); return; }
      this.templatesResource.reload();
    } catch {
      this.templateDeleteError.set('Error al conectar con el servidor.');
    }
  }
}
