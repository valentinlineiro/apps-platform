import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../services/api.service';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const POLL_INTERVAL_MS = 1500;

type SavedTemplate = { id: string; name: string };

@Component({
  selector: 'app-exam-corrector-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="layout">
      <a class="back" routerLink="/">← apps</a>
      <h1>exam-corrector</h1>

      <form (submit)="onSubmit($event)" class="panel">
        <label>Plantilla guardada</label>
        <select [(ngModel)]="selectedTemplateId" name="template_id" (change)="syncTemplateMode()">
          <option value="__upload__">Subir nueva plantilla...</option>
          <option *ngFor="let t of templates" [value]="t.id">{{ t.name }}</option>
        </select>

        <ng-container *ngIf="selectedTemplateId === '__upload__'">
          <label>Nueva plantilla</label>
          <input type="file" (change)="onTemplateFile($event)" accept="image/*" />
          <input type="text" [(ngModel)]="templateName" name="template_name" placeholder="Nombre plantilla (opcional)" />
          <label class="check">
            <input type="checkbox" [(ngModel)]="saveTemplate" name="save_template" />
            Guardar plantilla para uso futuro
          </label>
        </ng-container>

        <label>Examen</label>
        <input type="file" (change)="onExamFile($event)" accept="image/*" required />

        <button type="submit" [disabled]="loading">Corregir</button>
      </form>

      <p class="status">{{ status }}</p>
      <div class="progress-track" *ngIf="loading">
        <div class="progress-fill" [style.width.%]="progressValue"></div>
      </div>

      <section *ngIf="result" class="panel">
        <h2>{{ result.total_puntos }}/{{ result.max_puntos }}</h2>
        <p>{{ result.porcentaje_puntos || 0 }}% según regla aplicada</p>
        <p *ngIf="result.nombre">Alumno: {{ result.nombre }}</p>
        <p *ngIf="result.warning" class="warn">{{ result.warning }}</p>
        <table *ngIf="result.feedback?.length">
          <thead>
            <tr>
              <th>Pregunta</th>
              <th>Dada</th>
              <th>Correcta</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let row of result.feedback">
              <td>{{ row.pregunta_label }}</td>
              <td>{{ row.respuesta_dada }}</td>
              <td>{{ row.respuesta_correcta }}</td>
              <td>{{ row.estado }}</td>
            </tr>
          </tbody>
        </table>
      </section>
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
export class ExamCorrectorPageComponent implements OnInit {
  templates: SavedTemplate[] = [];
  selectedTemplateId = '__upload__';
  templateName = '';
  saveTemplate = true;
  templateFile: File | null = null;
  examFile: File | null = null;
  loading = false;
  status = '';
  progressValue = 0;
  result: any = null;

  constructor(private api: ApiService) {}

  async ngOnInit() {
    try {
      const response = await this.api.listTemplates();
      this.templates = response.templates || [];
    } catch {
      this.status = 'No se pudo cargar la lista de plantillas.';
    }
  }

  syncTemplateMode() {
    if (this.selectedTemplateId !== '__upload__') {
      this.templateFile = null;
    }
  }

  onTemplateFile(ev: Event) {
    this.templateFile = (ev.target as HTMLInputElement).files?.[0] || null;
  }

  onExamFile(ev: Event) {
    this.examFile = (ev.target as HTMLInputElement).files?.[0] || null;
  }

  async onSubmit(ev: Event) {
    ev.preventDefault();
    if (!this.examFile) {
      this.status = 'Selecciona un examen.';
      return;
    }
    if (this.selectedTemplateId === '__upload__' && !this.templateFile) {
      this.status = 'Selecciona una plantilla o usa una guardada.';
      return;
    }

    this.loading = true;
    this.result = null;
    this.progressValue = 0;
    this.status = 'Subiendo archivos...';

    const fd = new FormData();
    fd.append('examen', this.examFile);
    fd.append('template_id', this.selectedTemplateId);
    fd.append('template_name', this.templateName);
    fd.append('save_template', this.saveTemplate ? '1' : '0');
    if (this.templateFile) {
      fd.append('plantilla', this.templateFile);
    }

    try {
      const start = await this.api.startCorrection(fd);
      if (!start.ok || !start.job_id) {
        throw new Error(start.error || 'No se pudo iniciar la corrección.');
      }
      await this.pollJob(start.job_id);
    } catch (e: any) {
      this.status = `Error: ${e.message || e}`;
      this.loading = false;
    }
  }

  async pollJob(jobId: string) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (true) {
      if (Date.now() > deadline) {
        this.status = 'La corrección tardó demasiado. Por favor inténtalo de nuevo.';
        this.loading = false;
        return;
      }
      const status = await this.api.getStatus(jobId);
      if (!status.ok && status.error) {
        throw new Error(status.error);
      }
      if (status.status === 'done') {
        const res = await this.api.getResult(jobId);
        if (!res.ok) {
          throw new Error(res.error || 'No se pudo obtener el resultado.');
        }
        this.result = res.result;
        this.progressValue = 100;
        this.status = 'Corrección completada.';
        this.loading = false;
        await this.reloadTemplates();
        return;
      }
      if (status.status === 'error') {
        throw new Error(status.error || 'Error en procesamiento.');
      }
      this.progressValue = status.progress ?? 0;
      this.status = `${this.progressValue}% · ${status.message || 'Procesando...'}`;
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  async reloadTemplates() {
    try {
      const response = await this.api.listTemplates();
      this.templates = response.templates || [];
    } catch {}
  }
}
