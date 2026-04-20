import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { AnecaApiService, Article, EvaluationResult } from './services/aneca-api.service';

const CREDIT_ROLES = ['Investigación', 'Metodología', 'Redacción', 'Software'];
const DOCENTIA_LEVELS = ['No tengo', 'Aprobado', 'Notable', 'Excelente'];
const FIGURAS = ['Titular de Universidad (TU)', 'Catedrático (CU)'];
const TABS = [
  { id: 'investigacion', label: '🔍 Investigación' },
  { id: 'docencia',      label: '👨‍🏫 Docencia' },
  { id: 'transferencia', label: '🚀 Transferencia' },
  { id: 'idoneidad',     label: '⚖️ Idoneidad' },
  { id: 'horizonte',     label: '🧭 Horizonte' },
];

@Component({
  selector: 'app-aneca-advisor',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './aneca-advisor-app.component.html',
  styleUrl: './aneca-advisor-app.component.css',
})
export class AnecaAdvisorAppComponent implements OnInit {
  private api = inject(AnecaApiService);

  // ── Config ──────────────────────────────────────────────────────────────
  figura    = signal<string>(FIGURAS[0]);
  fieldKey  = signal<string>('general');
  sexenios  = signal<number>(0);

  // ── Docencia ─────────────────────────────────────────────────────────────
  horas    = signal<number>(240);
  docentia = signal<string>('Notable');

  // ── Transferencia ────────────────────────────────────────────────────────
  sexenioTransferencia = signal<boolean>(false);
  patentes             = signal<number>(0);
  spinOffs             = signal<number>(0);
  contratosArt83       = signal<number>(0);
  divulgacion          = signal<boolean>(false);

  // ── Articles & state ─────────────────────────────────────────────────────
  articles  = signal<Article[]>([]);
  fields    = signal<Record<string, string>>({});
  result    = signal<EvaluationResult | null>(null);
  orcidId   = signal<string>('');
  activeTab = signal<string>('investigacion');
  syncing   = signal<boolean>(false);
  saving    = signal<boolean>(false);
  evaluating = signal<boolean>(false);
  error     = signal<string | null>(null);

  // ── Derived ──────────────────────────────────────────────────────────────
  readonly tabs = TABS;
  readonly docEntiaLevels = DOCENTIA_LEVELS;
  readonly figuras = FIGURAS;
  readonly creditRoles = CREDIT_ROLES;

  fieldEntries = computed(() => Object.entries(this.fields()));
  fastTrack    = computed(() => {
    const minSexenios = this.figura().includes('CU') ? 3 : 2;
    return this.sexenios() >= minSexenios;
  });
  articlesOnly = computed(() => this.articles().filter(a => a.tipo === 'Articulo'));

  async ngOnInit() {
    const [fields, articles] = await Promise.all([
      firstValueFrom(this.api.getFields()),
      firstValueFrom(this.api.getArticles()),
    ]);
    this.fields.set(fields);
    this.articles.set(articles);
  }

  // ── Article actions ───────────────────────────────────────────────────────
  toggleRole(index: number, role: string, checked: boolean) {
    this.articles.update(arts => arts.map((art, i) => {
      if (i !== index) return art;
      const roles = checked
        ? [...new Set([...art.roles, role])]
        : art.roles.filter(r => r !== role);
      return { ...art, roles };
    }));
  }

  hasRole(article: Article, role: string): boolean {
    return article.roles.includes(role);
  }

  async syncOrcid() {
    const id = this.orcidId().trim();
    if (!id) return;
    this.syncing.set(true);
    this.error.set(null);
    try {
      const articles = await firstValueFrom(this.api.syncOrcid(id));
      this.articles.set(articles);
    } catch {
      this.error.set('Error al sincronizar ORCID. Verifica el ID e inténtalo de nuevo.');
    } finally {
      this.syncing.set(false);
    }
  }

  async saveArticles() {
    this.saving.set(true);
    try {
      const saved = await firstValueFrom(this.api.putArticles(this.articles()));
      this.articles.set(saved);
    } finally {
      this.saving.set(false);
    }
  }

  // ── Evaluation ────────────────────────────────────────────────────────────
  async evaluate() {
    this.evaluating.set(true);
    this.error.set(null);
    try {
      const result = await firstValueFrom(this.api.evaluate({
        field_key: this.fieldKey(),
        figura: this.figura(),
        sexenios: this.sexenios(),
        horas: this.horas(),
        docentia: this.docentia(),
        expediente: this.articles(),
        sexenio_transferencia: this.sexenioTransferencia(),
        patentes: this.patentes(),
        spin_offs: this.spinOffs(),
        contratos_art83: this.contratosArt83(),
        divulgacion: this.divulgacion(),
      }));
      this.result.set(result);
    } catch {
      this.error.set('Error al evaluar. Inténtalo de nuevo.');
    } finally {
      this.evaluating.set(false);
    }
  }

  priorityClass(priority: string): string {
    return ({ Alta: 'priority-alta', Media: 'priority-media', Info: 'priority-info' })[priority] ?? '';
  }

  metricClass(ok: boolean): string {
    return ok ? 'metric-ok' : 'metric-fail';
  }
}
