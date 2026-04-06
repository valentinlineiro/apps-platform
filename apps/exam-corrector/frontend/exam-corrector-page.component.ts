import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ExamCorrectorApiService } from './services/exam-corrector-api.service';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const POLL_INTERVAL_MS = 1500;

@Component({
  selector: 'app-exam-corrector-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="layout">
      <a class="back" routerLink="/">← apps</a>
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
    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 24px; }
    .back { color: #999; text-decoration: none; font-size: 13px; }
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
  `]
})
export class ExamCorrectorPageComponent {
  private api = inject(ExamCorrectorApiService);

  selectedTemplateId = signal('__upload__');
  templateName = signal('');
  saveTemplate = signal(true);
  templateFile = signal<File | null>(null);
  examFile = signal<File | null>(null);
  loading = signal(false);
  status = signal('');
  progressValue = signal(0);
  result = signal<any>(null);

  templatesResource = resource({
    loader: () => this.api.listTemplates().then(r => r.templates ?? [])
  });

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
}
