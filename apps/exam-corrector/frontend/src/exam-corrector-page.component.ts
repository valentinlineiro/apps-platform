import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ExamCorrectorApiService } from './services/exam-corrector-api.service';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const BATCH_POLL_TIMEOUT_MS = 60 * 60 * 1000;
const POLL_INTERVAL_MS = 1500;

@Component({
  selector: 'app-exam-corrector-page',
  standalone: true,
  imports: [FormsModule],
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

        <label>Plantilla guardada</label>
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
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            @for (item of batchItems(); track item.filename) {
              <tr [class.row-error]="item.status === 'error'" [class.row-done]="item.status === 'done'">
                <td>{{ item.filename }}</td>
                <td>{{ item.nombre ?? '' }}</td>
                <td>{{ item.status === 'done' ? (item.total_puntos + '/' + item.max_puntos) : '' }}</td>
                <td>{{ item.status === 'done' ? (item.porcentaje_puntos + '%') : '' }}</td>
                <td>
                  @if (item.status === 'done') { ok }
                  @else if (item.status === 'error') { <span class="warn" [title]="item.error ?? ''">error</span> }
                  @else if (item.status === 'processing') { <span class="processing">...</span> }
                  @else { pendiente }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }

      <section class="panel">
        <h2 class="section-title">Ajustes</h2>

        <label>Gemini API Key</label>
        @if (settingsResource.isLoading()) {
          <p class="status">Cargando...</p>
        } @else {
          @if (settingsResource.value()?.source !== 'none') {
            <p class="key-status">
              Clave activa
              @if (settingsResource.value()?.source === 'env') {
                (variable de entorno)
              }
              : <code>{{ settingsResource.value()?.masked }}</code>
            </p>
          } @else {
            <p class="key-status warn">Sin API key configurada.</p>
          }
          <input
            type="password"
            [ngModel]="newApiKey()"
            (ngModelChange)="newApiKey.set($event)"
            name="gemini_key"
            placeholder="AIza..."
            autocomplete="off"
          />
          <div class="key-actions">
            <button type="button" (click)="saveKey()" [disabled]="!newApiKey()">Guardar clave</button>
            @if (settingsResource.value()?.source === 'custom') {
              <button type="button" class="danger" (click)="clearKey()">Eliminar clave guardada</button>
            }
          </div>
          @if (settingsError()) {
            <p class="warn">{{ settingsError() }}</p>
          }
        }
      </section>
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
    .key-status { font-size: 13px; color: #aaa; margin: 0; }
    code { font-family: monospace; color: #ccc; }
    .key-actions { display: flex; gap: 8px; }
    button.danger { border-color: #5a2a2a; color: #f88; }
    .current-item { font-size: 13px; color: #aaa; margin-top: 8px; }
    .batch-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    .batch-table th, .batch-table td { border-bottom: 1px solid #333; text-align: left; padding: 8px; font-size: 13px; }
    .row-done td:first-child { color: #e8e8e8; }
    .row-error { opacity: 0.7; }
    .processing { color: #9a9; }
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
  batchItems = signal<Array<{
    filename: string;
    status: string;
    nombre?: string;
    total_puntos?: number;
    max_puntos?: number;
    porcentaje_puntos?: number;
    error?: string;
  }>>([]);

  templatesResource = resource({
    loader: () => this.api.listTemplates().then(r => r.templates ?? [])
  });

  settingsResource = resource({
    loader: () => this.api.getSettings()
  });

  newApiKey = signal('');
  settingsError = signal('');

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

  async saveKey() {
    this.settingsError.set('');
    try {
      const res = await this.api.setGeminiKey(this.newApiKey());
      if (!res.ok) { this.settingsError.set(res.error || 'Error al guardar.'); return; }
      this.newApiKey.set('');
      this.settingsResource.reload();
    } catch {
      this.settingsError.set('Error al guardar la clave.');
    }
  }

  async clearKey() {
    this.settingsError.set('');
    try {
      await this.api.clearGeminiKey();
      this.settingsResource.reload();
    } catch {
      this.settingsError.set('Error al eliminar la clave.');
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
      if (s.finished) {
        this.batchLoading.set(false);
        this.batchFinished.set(true);
        this.batchStatus.set(`Lote completado: ${s.done} correctos, ${s.failed} errores.`);
        return;
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
  }
}
