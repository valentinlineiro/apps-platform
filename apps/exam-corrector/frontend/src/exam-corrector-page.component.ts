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
  template: `
    <main class="layout">
      <h1>exam-corrector</h1>
      <p class="subtitle">Corrección automática de exámenes tipo test mediante detección óptica de marcas.</p>

      <!-- ── Tab bar ────────────────────────────────── -->
      <nav class="tabs">
        <button type="button" [class.tab-active]="activeTab() === 'single'"    (click)="activeTab.set('single')">Individual</button>
        <button type="button" [class.tab-active]="activeTab() === 'batch'"     (click)="activeTab.set('batch')">Lote</button>
        <button type="button" [class.tab-active]="activeTab() === 'templates'" (click)="activeTab.set('templates')">Plantillas</button>
      </nav>

      <!-- ══════════════════════════════════════════════
           TAB: Individual
      ══════════════════════════════════════════════ -->
      @if (activeTab() === 'single') {

        <details class="help-panel">
          <summary>¿Cómo funciona?</summary>
          <ul>
            <li><strong>Plantilla:</strong> foto de la hoja de respuestas del profesor con las respuestas correctas ya marcadas. Se guarda para reutilizarla.</li>
            <li><strong>Calidad:</strong> imagen plana, bien iluminada, sin torsión ni sombras sobre las burbujas.</li>
            <li><strong>Confianza:</strong> indica la seguridad de detección por respuesta. Las filas marcadas con ⚠️ requieren revisión manual.</li>
          </ul>
        </details>

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
            <div class="drop-zone" [class.dz-active]="templateDrop()"
                 (click)="templateInput.click()"
                 (dragover)="$event.preventDefault(); templateDrop.set(true)"
                 (dragleave)="templateDrop.set(false)"
                 (drop)="onTemplateDrop($event)">
              <input #templateInput type="file" accept="image/*" (change)="onTemplateFile($event)" />
              <span>{{ templateFile()?.name ?? 'Arrastra aquí o haz clic' }}</span>
            </div>
            <input type="text" [ngModel]="templateName()" (ngModelChange)="templateName.set($event)"
                   name="template_name" placeholder="Nombre de la plantilla (opcional)" />
            <label class="check">
              <input type="checkbox" [ngModel]="saveTemplate()" (ngModelChange)="saveTemplate.set($event)" name="save_template" />
              Guardar plantilla para uso futuro
            </label>
          }

          <label>Examen del alumno</label>
          <div class="drop-zone" [class.dz-active]="examDrop()"
               (click)="examInput.click()"
               (dragover)="$event.preventDefault(); examDrop.set(true)"
               (dragleave)="examDrop.set(false)"
               (drop)="onExamDrop($event)">
            <input #examInput type="file" accept="image/*" (change)="onExamFile($event)" />
            <span>{{ examFile()?.name ?? 'Arrastra aquí o haz clic' }}</span>
          </div>

          <button type="submit" [disabled]="loading()">Corregir</button>
        </form>

        <p class="status">{{ status() }}</p>
        @if (loading()) {
          <div class="progress-track"><div class="progress-fill" [style.width.%]="progressValue()"></div></div>
        }

        @if (result(); as r) {
          <section class="panel result-panel">
            <div class="score-row">
              <span class="score">{{ r.total_puntos }}/{{ r.max_puntos }}</span>
              <span class="score-pct">{{ r.porcentaje_puntos || 0 }}%</span>
            </div>
            @if (r.nombre) { <p class="result-meta">Alumno: {{ r.nombre }}</p> }
            @if (r.warning) { <p class="result-warn">⚠️ {{ r.warning }}</p> }
            @if (r.feedback?.length) {
              <table>
                <thead>
                  <tr>
                    <th>Pregunta</th>
                    <th>Dada</th>
                    <th>Correcta</th>
                    <th>Estado</th>
                    <th>Confianza</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of r.feedback; track row.pregunta_label) {
                    <tr [class.low-conf]="row.confianza != null && row.confianza < 0.8">
                      <td>{{ row.pregunta_label }}</td>
                      <td>{{ row.respuesta_dada }}</td>
                      <td>{{ row.respuesta_correcta }}</td>
                      <td>
                        {{ row.estado }}
                        @if (row.confianza != null && row.confianza < 0.8) { <span class="conf-warn">⚠️</span> }
                      </td>
                      <td [class.conf-low]="row.confianza != null && row.confianza < 0.8">
                        {{ row.confianza != null ? ((row.confianza * 100 | number:'1.0-0') + '%') : '—' }}
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </section>
        }
      }

      <!-- ══════════════════════════════════════════════
           TAB: Lote
      ══════════════════════════════════════════════ -->
      @if (activeTab() === 'batch') {

        <details class="help-panel">
          <summary>¿Cómo funciona el modo lote?</summary>
          <ul>
            <li><strong>Formato:</strong> PDF con una página por examen, o ZIP con imágenes JPG/PNG.</li>
            <li><strong>Plantilla requerida:</strong> debe estar guardada. Si aún no tienes una, corrígela primero en la pestaña Individual.</li>
            <li><strong>Revisión:</strong> los exámenes con confianza baja (&lt;80%) se marcarn ⚠️ para revisión manual al finalizar.</li>
          </ul>
        </details>

        <form (submit)="onBatchSubmit($event)" class="panel">
          <label>Plantilla guardada (requerida)</label>
          <select [ngModel]="batchTemplateId()" (ngModelChange)="batchTemplateId.set($event)" name="batch_template_id">
            <option value="">Seleccionar plantilla...</option>
            @for (t of templatesResource.value() ?? []; track t.id) {
              <option [value]="t.id">{{ t.name }}</option>
            }
          </select>

          <label>Exámenes (PDF una página por examen, o ZIP de imágenes)</label>
          <div class="drop-zone" [class.dz-active]="batchDrop()"
               (click)="batchInput.click()"
               (dragover)="$event.preventDefault(); batchDrop.set(true)"
               (dragleave)="batchDrop.set(false)"
               (drop)="onBatchDrop($event)">
            <input #batchInput type="file" accept=".pdf,.zip" (change)="onBatchFile($event)" />
            <span>{{ batchFile()?.name ?? 'Arrastra aquí o haz clic' }}</span>
          </div>

          <button type="submit" [disabled]="batchLoading()">Iniciar corrección en lote</button>
        </form>

        <p class="status">{{ batchStatus() }}</p>
        @if (batchLoading() || batchFinished()) {
          <div class="progress-track"><div class="progress-fill" [style.width.%]="batchProgress()"></div></div>
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
                <th>Archivo</th><th>Alumno</th><th>Puntos</th><th>%</th><th>Confianza</th><th>Estado</th>
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
                  <td [class.conf-low]="item.confidence != null && item.confidence < 0.8">
                    {{ item.confidence != null ? ((item.confidence * 100 | number:'1.0-0') + '%') : '' }}
                  </td>
                  <td>
                    @if (item.needs_review && !item.reviewed) {
                      <span class="review-badge">⚠️ revisar</span>
                    } @else if (item.needs_review && item.reviewed) {
                      <span class="reviewed-badge">✓ revisado</span>
                    } @else if (item.status === 'done') {
                      <span class="ok-badge">✓</span>
                    } @else if (item.status === 'error') {
                      <span class="error-badge" [title]="item.error ?? ''">error</span>
                    } @else if (item.status === 'processing') {
                      <span class="processing">...</span>
                    } @else {
                      <span class="muted-text">pendiente</span>
                    }
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
              @if (batchNeedsReview() > 0) {
                <span class="review-count">{{ batchNeedsReview() }} pendientes</span>
              }
            </h2>
            @for (item of reviewItems(); track item.idx) {
              <div class="review-item" [class.review-item-done]="item.reviewed">
                <div class="review-header" (click)="toggleReview(item.idx)">
                  <span class="review-filename">{{ item.filename }}</span>
                  <span class="review-meta">
                    {{ item.nombre }} · {{ item.total_puntos }}/{{ item.max_puntos }} ·
                    confianza {{ (item.confidence * 100 | number:'1.0-0') + '%' }}
                  </span>
                  @if (!item.reviewed) {
                    <button type="button" class="review-btn" (click)="$event.stopPropagation(); markReviewed(item.idx)">
                      Marcar revisado
                    </button>
                  } @else {
                    <span class="reviewed-badge">✓ revisado</span>
                  }
                </div>
                @if (expandedReviewIdx() === item.idx) {
                  <table class="review-answers">
                    <thead>
                      <tr><th>Pregunta</th><th>Dada</th><th>Correcta</th><th>Estado</th><th>Confianza</th></tr>
                    </thead>
                    <tbody>
                      @for (row of item.feedback; track row.pregunta_label) {
                        <tr [class.low-conf]="row.confianza < 0.8">
                          <td>{{ row.pregunta_label }}</td>
                          <td>{{ row.respuesta_dada }}</td>
                          <td>{{ row.respuesta_correcta }}</td>
                          <td>
                            {{ row.estado }}
                            @if (row.confianza < 0.8) { <span class="conf-warn">⚠️</span> }
                          </td>
                          <td [class.conf-low]="row.confianza < 0.8">
                            {{ (row.confianza * 100 | number:'1.0-0') + '%' }}
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                }
              </div>
            }
          </section>
        }
      }

      <!-- ══════════════════════════════════════════════
           TAB: Plantillas
      ══════════════════════════════════════════════ -->
      @if (activeTab() === 'templates') {
        <section class="panel">
          @if (templatesResource.isLoading()) {
            <p class="muted-text">Cargando...</p>
          } @else if ((templatesResource.value() ?? []).length === 0) {
            <p class="muted-text">No hay plantillas guardadas. Corrígete un examen en la pestaña Individual con "Guardar plantilla" activado.</p>
          } @else {
            <table>
              <thead>
                <tr><th>Nombre</th><th>Guardada</th><th></th></tr>
              </thead>
              <tbody>
                @for (t of templatesResource.value() ?? []; track t.id) {
                  <tr>
                    <td>{{ t.name }}</td>
                    <td class="muted-text">{{ t.created_at * 1000 | date:'dd/MM/yyyy HH:mm' }}</td>
                    <td><button class="btn-danger" type="button" (click)="deleteTemplate(t.id)">Eliminar</button></td>
                  </tr>
                }
              </tbody>
            </table>
          }
          @if (templateDeleteError()) {
            <p class="error-text">{{ templateDeleteError() }}</p>
          }
        </section>
      }

    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 4px; font-size: 20px; }
    .subtitle { color: var(--text-muted); font-size: 14px; margin: 4px 0 16px; }

    /* ── Tabs ── */
    .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
    .tabs button {
      padding: 8px 20px;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      font-size: 13px;
      cursor: pointer;
      margin-bottom: -1px;
    }
    .tabs button:hover { color: var(--text-nav); }
    .tabs button.tab-active { color: var(--text); border-bottom-color: var(--ok); }

    /* ── Help panel ── */
    .help-panel { border: 1px solid var(--border); background: var(--bg-input); padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: var(--text-nav); }
    .help-panel summary { cursor: pointer; color: var(--text-muted); font-size: 13px; user-select: none; }
    .help-panel summary:hover { color: var(--text-nav); }
    .help-panel ul { margin: 10px 0 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
    .help-panel li { line-height: 1.5; }
    .help-panel strong { color: var(--text); }

    /* ── Form panel ── */
    .panel { border: 1px solid var(--border); background: var(--bg-surface); padding: 16px; margin-top: 16px; display: grid; gap: 10px; }
    label { font-size: 12px; color: var(--text-muted); }
    select, input[type="text"], input[type="email"] {
      padding: 10px; background: var(--bg-input); color: var(--text); border: 1px solid var(--border);
    }
    .check { display: flex; align-items: center; gap: 8px; }
    button[type="submit"], button[type="button"]:not(.review-btn):not(.btn-danger) {
      padding: 10px; background: var(--bg-input); color: var(--text); border: 1px solid var(--border); cursor: pointer;
    }
    button:hover { border-color: var(--border-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Drop zone ── */
    .drop-zone {
      border: 1px dashed var(--border);
      padding: 20px 16px;
      text-align: center;
      cursor: pointer;
      background: var(--bg-input);
      color: var(--text-muted);
      font-size: 13px;
      transition: border-color 0.15s, background 0.15s;
    }
    .drop-zone:hover, .drop-zone.dz-active {
      border-color: var(--ok);
      background: var(--ok-bg);
      color: var(--ok);
    }
    .drop-zone input { display: none; }

    /* ── Status / progress ── */
    .status { min-height: 20px; color: var(--text-muted); font-size: 13px; }
    .progress-track { height: 4px; background: var(--border); margin-top: 4px; }
    .progress-fill  { height: 100%; background: var(--ok); transition: width 0.4s ease; }
    .current-item { font-size: 13px; color: var(--text-nav); margin-top: 8px; }

    /* ── Result panel ── */
    .result-panel { margin-top: 16px; }
    .score-row { display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px; }
    .score { font-size: 28px; font-weight: 700; color: var(--text); }
    .score-pct { font-size: 16px; color: var(--text-muted); }
    .result-meta { margin: 0; font-size: 13px; color: var(--text-muted); }
    .result-warn { margin: 4px 0 0; font-size: 13px; color: var(--warn); }

    /* ── Tables ── */
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--border); text-align: left; padding: 8px; font-size: 13px; }
    th { color: var(--text-muted); font-weight: 500; }
    .low-conf { background: var(--warn-bg); }
    .conf-warn { margin-left: 4px; }
    .conf-low { color: var(--warn); font-weight: 600; }
    .section-title { margin: 0; font-size: 16px; font-weight: 600; }

    /* ── Batch table ── */
    .batch-table th, .batch-table td { border-bottom: 1px solid var(--border); text-align: left; padding: 8px; font-size: 13px; }
    .row-error { opacity: 0.7; }
    .row-review td { background: var(--warn-bg); }
    .row-reviewed { opacity: 0.6; }
    .processing { color: var(--ok); }
    .review-badge  { color: var(--warn);   font-size: 12px; font-weight: 600; }
    .reviewed-badge { color: var(--ok);    font-size: 12px; }
    .ok-badge      { color: var(--ok);    font-size: 12px; }
    .error-badge   { color: var(--danger); font-size: 12px; }
    .muted-text    { color: var(--text-muted); }
    .error-text    { color: var(--danger); font-size: 13px; margin-top: 8px; }

    /* ── Download button ── */
    .download-btn { display: inline-block; margin-top: 12px; padding: 10px 16px; background: var(--ok-bg); border: 1px solid var(--ok-border); color: var(--ok); text-decoration: none; font-size: 13px; }

    /* ── Review queue ── */
    .review-panel { margin-top: 16px; }
    .review-count { font-size: 13px; font-weight: normal; color: var(--warn); margin-left: 8px; }
    .review-item { border: 1px solid var(--warn-border); margin-bottom: 8px; }
    .review-item-done { border-color: var(--ok-border); opacity: 0.7; }
    .review-header { display: flex; align-items: center; gap: 12px; padding: 10px; cursor: pointer; background: var(--warn-bg); flex-wrap: wrap; }
    .review-header:hover { filter: brightness(1.2); }
    .review-filename { font-size: 13px; color: var(--text); flex-shrink: 0; }
    .review-meta { font-size: 12px; color: var(--text-muted); flex: 1; }
    .review-btn { padding: 4px 10px; font-size: 12px; background: var(--warn-bg); border: 1px solid var(--warn); color: var(--warn); cursor: pointer; flex-shrink: 0; }
    .review-answers { width: 100%; border-collapse: collapse; }
    .review-answers th, .review-answers td { border-bottom: 1px solid var(--border); padding: 6px 10px; font-size: 12px; text-align: left; }

    /* ── Buttons ── */
    .btn-danger { padding: 6px 10px; background: var(--bg-input); border: 1px solid var(--danger-border); color: var(--danger); cursor: pointer; font-size: 12px; }
    .btn-danger:hover { background: var(--danger-bg); }
  `],
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
