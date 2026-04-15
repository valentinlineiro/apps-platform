import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ExamCorrectorApiService } from './services/exam-corrector-api.service';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const BATCH_POLL_TIMEOUT_MS = 60 * 60 * 1000;
const POLL_INTERVAL_MS = 1500;

@Component({
  selector: 'app-exam-corrector-page',
  standalone: true,
  imports: [FormsModule, DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="layout">
      <h1>exam-corrector</h1>

      <form (submit)="onSubmit($event)" class="panel">
        <label>Plantilla guardada</label>
        <select [ngModel]="selectedTemplateId()" (ngModelChange)="onTemplateChange($event)" name="template_id">
          <option value="__upload__">Subir nueva plantilla...</option>
          @for (t of templatesResource.value() ?? []; track t.id) {
            <option [value]="t.id">{{ t.name }}</option>
          }
        </select>

        @if (selectedTemplateId() === '__upload__') {
          <label>Nueva plantilla</label>
          <input type="file" (change)="onTemplateFile($event)" accept="image/*" />
          <input type="text" [ngModel]="templateName()" (ngModelChange)="templateName.set($event)" name="template_name" placeholder="Nombre plantilla (opcional)" />
          <label class="check">
            <input type="checkbox" [ngModel]="saveTemplate()" (ngModelChange)="saveTemplate.set($event)" name="save_template" />
            Guardar plantilla para uso futuro
          </label>
        }

        <label>Examen</label>
        <input type="file" (change)="onExamFile($event)" accept="image/*" required />

        <button type="submit" [disabled]="loading()">Corregir</button>
      </form>

      <p class="status">{{ status() }}</p>
      @if (loading()) {
        <div class="progress-track">
          <div class="progress-fill" [style.width.%]="progressValue()"></div>
        </div>
      }

      @if (result(); as r) {
        <section class="panel">
          <h2>{{ r.total_puntos }}/{{ r.max_puntos }}</h2>
          <p>{{ r.porcentaje_puntos || 0 }}% según regla aplicada</p>
          @if (r.nombre) {
            <p>Alumno: {{ r.nombre }}</p>
          }
          @if (r.warning) {
            <p class="warn">{{ r.warning }}</p>
          }
          @if (r.feedback?.length) {
            <table>
              <thead>
                <tr>
                  <th>Pregunta</th>
                  <th>Dada</th>
                  <th>Correcta</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                @for (row of r.feedback; track row.pregunta_label) {
                  <tr>
                    <td>{{ row.pregunta_label }}</td>
                    <td>{{ row.respuesta_dada }}</td>
                    <td>{{ row.respuesta_correcta }}</td>
                    <td>{{ row.estado }}</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </section>
      }

      <form (submit)="onBatchSubmit($event)" class="panel">
        <h2 class="section-title">Corrección en lote</h2>

        <label>Plantilla guardada (requerida)</label>
        <select [ngModel]="batchTemplateId()" (ngModelChange)="batchTemplateId.set($event)" name="batch_template_id">
          <option value="">Seleccionar plantilla...</option>
          @for (t of templatesResource.value() ?? []; track t.id) {
            <option [value]="t.id">{{ t.name }}</option>
          }
        </select>

        <label>Exámenes (PDF con una página por examen, o ZIP con imágenes JPG/PNG)</label>
        <input type="file" (change)="onBatchFile($event)" accept=".pdf,.zip" />

        <button type="submit" [disabled]="batchLoading()">Iniciar corrección en lote</button>
      </form>

      <p class="status">{{ batchStatus() }}</p>
      @if (batchLoading() || batchFinished()) {
        <div class="progress-track">
          <div class="progress-fill" [style.width.%]="batchProgress()"></div>
        </div>
      }
      @if (batchLoading() && batchCurrentItem()) {
        <p class="current-item">Corrigiendo: <strong>{{ batchCurrentItem() }}</strong></p>
      }
      @if (batchFinished()) {
        <a class="download-btn" [href]="batchResultUrl()" download>Descargar CSV</a>
      }
      @if (batchItems().length > 0) {
        <table class="batch-table">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Alumno</th>
              <th>Puntos</th>
              <th>%</th>
              <th>Confianza</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            @for (item of batchItems(); track item.filename) {
              <tr [class.row-error]="item.status === 'error'"
                  [class.row-done]="item.status === 'done' && !item.needs_review"
                  [class.row-review]="item.needs_review && !item.reviewed"
                  [class.row-reviewed]="item.needs_review && item.reviewed">
                <td>{{ item.filename }}</td>
                <td>{{ item.nombre ?? '' }}</td>
                <td>{{ item.status === 'done' ? (item.total_puntos + '/' + item.max_puntos) : '' }}</td>
                <td>{{ item.status === 'done' ? (item.porcentaje_puntos + '%') : '' }}</td>
                <td>{{ item.confidence != null ? (item.confidence * 100 | number:'1.0-0') + '%' : '' }}</td>
                <td>
                  @if (item.needs_review && !item.reviewed) { <span class="review-badge">revisar</span> }
                  @else if (item.needs_review && item.reviewed) { <span class="reviewed-badge">revisado</span> }
                  @else if (item.status === 'done') { ok }
                  @else if (item.status === 'error') { <span class="warn" [title]="item.error ?? ''">error</span> }
                  @else if (item.status === 'processing') { <span class="processing">...</span> }
                  @else { pendiente }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }

      @if (reviewItems().length > 0) {
        <section class="panel review-panel">
          <h2 class="section-title">
            Cola de revisión
            @if (batchNeedsReview() > 0) { <span class="review-count">{{ batchNeedsReview() }} pendientes</span> }
          </h2>
          @for (item of reviewItems(); track item.idx) {
            <div class="review-item" [class.review-item-done]="item.reviewed">
              <div class="review-header" (click)="toggleReview(item.idx)">
                <span class="review-filename">{{ item.filename }}</span>
                <span class="review-meta">{{ item.nombre }} · {{ item.total_puntos }}/{{ item.max_puntos }} · confianza {{ (item.confidence * 100 | number:'1.0-0') + '%' }}</span>
                @if (!item.reviewed) {
                  <button type="button" class="review-btn" (click)="$event.stopPropagation(); markReviewed(item.idx)">Marcar revisado</button>
                } @else {
                  <span class="reviewed-badge">revisado</span>
                }
              </div>
              @if (expandedReviewIdx() === item.idx) {
                <table class="review-answers">
                  <thead><tr><th>Pregunta</th><th>Dada</th><th>Correcta</th><th>Estado</th><th>Confianza</th></tr></thead>
                  <tbody>
                    @for (row of item.feedback; track row.pregunta_label) {
                      <tr [class.low-confidence]="row.confianza < 0.8">
                        <td>{{ row.pregunta_label }}</td>
                        <td>{{ row.respuesta_dada }}</td>
                        <td>{{ row.respuesta_correcta }}</td>
                        <td>{{ row.estado }}</td>
                        <td [class.warn]="row.confianza < 0.8">{{ (row.confianza * 100 | number:'1.0-0') + '%' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            </div>
          }
        </section>
      }

    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 24px; }
    .panel { border: 1px solid #222; background: #141414; padding: 16px; margin-top: 16px; display: grid; gap: 10px; }
    label { font-size: 12px; color: #999; }
    select, input, button { padding: 10px; background: #0f0f0f; color: #e8e8e8; border: 1px solid #2a2a2a; }
    button { cursor: pointer; }
    .check { display: flex; align-items: center; gap: 8px; }
    .status { min-height: 20px; color: #9a9a9a; }
    .progress-track { height: 4px; background: #222; margin-top: 4px; }
    .progress-fill { height: 100%; background: #5a9; transition: width 0.4s ease; }
    .warn { color: #ff9e9e; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #333; text-align: left; padding: 8px; font-size: 13px; }
    .section-title { margin: 0; font-size: 16px; font-weight: 600; }
    .download-btn { display: inline-block; margin-top: 12px; padding: 10px 16px; background: #1a3a2a; border: 1px solid #2a5a3a; color: #5a9; text-decoration: none; font-size: 13px; }
    .current-item { font-size: 13px; color: #aaa; margin-top: 8px; }
    .batch-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    .batch-table th, .batch-table td { border-bottom: 1px solid #333; text-align: left; padding: 8px; font-size: 13px; }
    .row-done td:first-child { color: #e8e8e8; }
    .row-error { opacity: 0.7; }
    .row-review { background: #2a1f00; }
    .row-reviewed { opacity: 0.6; }
    .processing { color: #9a9; }
    .review-badge { color: #f5a623; font-size: 12px; font-weight: 600; }
    .reviewed-badge { color: #5a9; font-size: 12px; }
    .review-panel { margin-top: 16px; }
    .review-count { font-size: 13px; font-weight: normal; color: #f5a623; margin-left: 8px; }
    .review-item { border: 1px solid #2a2000; margin-bottom: 8px; }
    .review-item-done { border-color: #1a2a1a; opacity: 0.7; }
    .review-header { display: flex; align-items: center; gap: 12px; padding: 10px; cursor: pointer; background: #1a1500; flex-wrap: wrap; }
    .review-header:hover { background: #221c00; }
    .review-filename { font-size: 13px; color: #ccc; flex-shrink: 0; }
    .review-meta { font-size: 12px; color: #888; flex: 1; }
    .review-btn { padding: 4px 10px; font-size: 12px; background: #2a1f00; border: 1px solid #f5a623; color: #f5a623; cursor: pointer; flex-shrink: 0; }
    .review-answers { width: 100%; border-collapse: collapse; }
    .review-answers th, .review-answers td { border-bottom: 1px solid #2a2a2a; padding: 6px 10px; font-size: 12px; text-align: left; }
    .low-confidence { background: #1f1500; }
    .low-confidence .warn { font-weight: 600; }
  `]
})
export class ExamCorrectorPageComponent {
  private api = inject(ExamCorrectorApiService);

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

  templatesResource = resource({
    loader: () => this.api.listTemplates().then(r => r.templates ?? [])
  });

  batchResultUrl(): string {
    return this.api.batchResultUrl(this.batchId());
  }

  onTemplateChange(id: string) {
    this.selectedTemplateId.set(id);
    if (id !== '__upload__') this.templateFile.set(null);
  }

  onTemplateFile(ev: Event) {
    this.templateFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
  }

  onExamFile(ev: Event) {
    this.examFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
  }

  onBatchFile(ev: Event) {
    this.batchFile.set((ev.target as HTMLInputElement).files?.[0] ?? null);
  }

  async onSubmit(ev: Event) {
    ev.preventDefault();
    if (!this.examFile()) {
      this.status.set('Selecciona un examen.');
      return;
    }
    if (this.selectedTemplateId() === '__upload__' && !this.templateFile()) {
      this.status.set('Selecciona una plantilla o usa una guardada.');
      return;
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
      const status = await this.api.getStatus(jobId);
      if (!status.ok && status.error) throw new Error(status.error);
      if (status.status === 'done') {
        const res = await this.api.getResult(jobId);
        if (!res.ok) throw new Error(res.error || 'No se pudo obtener el resultado.');
        this.result.set(res.result);
        this.progressValue.set(100);
        this.status.set('Corrección completada.');
        this.loading.set(false);
        this.templatesResource.reload();
        return;
      }
      if (status.status === 'error') throw new Error(status.error || 'Error en procesamiento.');
      this.progressValue.set(status.progress ?? 0);
      this.status.set(`${status.progress ?? 0}% · ${status.message || 'Procesando...'}`);
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  async onBatchSubmit(ev: Event) {
    ev.preventDefault();
    if (!this.batchTemplateId()) {
      this.batchStatus.set('Selecciona una plantilla guardada.');
      return;
    }
    if (!this.batchFile()) {
      this.batchStatus.set('Selecciona un archivo PDF o ZIP.');
      return;
    }

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

  async markReviewed(idx: number) {
    await this.api.markReviewed(this.batchId(), idx);
    this.reviewItems.update(items => items.map(i => i.idx === idx ? { ...i, reviewed: true } : i));
    this.batchNeedsReview.update(n => Math.max(0, n - 1));
  }

  toggleReview(idx: number) {
    this.expandedReviewIdx.update(cur => cur === idx ? null : idx);
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
        this.batchStatus.set(`Lote completado: ${s.done} correctos, ${s.failed} errores${reviewNote}.`);
        if (s.needs_review) {
          const rev = await this.api.getReviewItems(batchId);
          if (rev.ok) this.reviewItems.set(rev.items);
        }
        return;
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
  }
}
