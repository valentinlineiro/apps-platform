import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { ShellHeaderComponent } from '../components/shell-header.component';
import { UserService } from '../services/user.service';

interface Profile {
  avatar_url: string | null;
  bio: string | null;
  display_name: string | null;
  show_activity: boolean;
  show_email: boolean;
}

interface Preferences {
  theme: string;
  language: string;
  timezone: string;
  reduced_motion: boolean;
  font_scale: number;
  notification_email: boolean;
  notification_digest: string;
}

interface AuditEntry {
  id: number;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  created_at: number;
}

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-shell-header [showSettings]="true" />
    <main class="layout">
      <div class="page-header">
        <h1 class="page-title">Mi perfil</h1>
        <p class="page-subtitle">Gestiona tu información personal y preferencias</p>
      </div>

      @if (saveOk()) {
        <div class="banner banner--ok">Cambios guardados correctamente.</div>
      }
      @if (saveError()) {
        <div class="banner banner--error">{{ saveError() }}</div>
      }

      <!-- Identity -->
      <section class="section">
        <h2 class="section-title">Identidad</h2>
        <div class="field-group">
          <div class="field">
            <label class="label">Nombre para mostrar</label>
            <input
              class="input"
              type="text"
              [value]="profile().display_name ?? user()?.name ?? ''"
              (input)="profileDraft.display_name = $any($event.target).value"
              placeholder="{{ user()?.name ?? '' }}"
            />
            <span class="hint">Si está vacío se usa tu nombre de cuenta.</span>
          </div>
          <div class="field">
            <label class="label">URL del avatar</label>
            <input
              class="input"
              type="url"
              [value]="profile().avatar_url ?? ''"
              (input)="profileDraft.avatar_url = $any($event.target).value"
              placeholder="https://…"
            />
          </div>
          <div class="field">
            <label class="label">Bio</label>
            <textarea
              class="input input--textarea"
              rows="3"
              [value]="profile().bio ?? ''"
              (input)="profileDraft.bio = $any($event.target).value"
              placeholder="Cuéntanos algo sobre ti…"
            ></textarea>
          </div>
        </div>
        <button class="btn" (click)="saveProfile()" [disabled]="saving()">Guardar identidad</button>
      </section>

      <!-- Preferencias -->
      <section class="section">
        <h2 class="section-title">Preferencias</h2>
        <div class="field-group">
          <div class="field field--row">
            <label class="label">Tema</label>
            <select class="select" [value]="prefs().theme" (change)="prefsDraft.theme = $any($event.target).value">
              <option value="dark">Oscuro</option>
              <option value="light">Claro</option>
              <option value="system">Sistema</option>
            </select>
          </div>
          <div class="field field--row">
            <label class="label">Idioma</label>
            <select class="select" [value]="prefs().language" (change)="prefsDraft.language = $any($event.target).value">
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </div>
          <div class="field field--row">
            <label class="label">Zona horaria</label>
            <input
              class="input"
              type="text"
              [value]="prefs().timezone"
              (input)="prefsDraft.timezone = $any($event.target).value"
              placeholder="UTC"
            />
          </div>
          <div class="field field--row">
            <label class="label">Tamaño de fuente</label>
            <select class="select" [value]="prefs().font_scale" (change)="prefsDraft.font_scale = +$any($event.target).value">
              <option value="0.8">Pequeño (0.8×)</option>
              <option value="1.0">Normal (1.0×)</option>
              <option value="1.2">Grande (1.2×)</option>
              <option value="1.5">Muy grande (1.5×)</option>
            </select>
          </div>
          <div class="field field--row">
            <label class="label">Reducir movimiento</label>
            <label class="toggle">
              <input
                type="checkbox"
                [checked]="prefs().reduced_motion"
                (change)="prefsDraft.reduced_motion = $any($event.target).checked"
              />
              <span class="toggle-track"></span>
            </label>
          </div>
        </div>
        <button class="btn" (click)="savePrefs()" [disabled]="saving()">Guardar preferencias</button>
      </section>

      <!-- Notificaciones -->
      <section class="section">
        <h2 class="section-title">Notificaciones</h2>
        <div class="field-group">
          <div class="field field--row">
            <label class="label">Notificaciones por email</label>
            <label class="toggle">
              <input
                type="checkbox"
                [checked]="prefs().notification_email"
                (change)="prefsDraft.notification_email = $any($event.target).checked"
              />
              <span class="toggle-track"></span>
            </label>
          </div>
          <div class="field field--row">
            <label class="label">Resumen de actividad</label>
            <select class="select" [value]="prefs().notification_digest" (change)="prefsDraft.notification_digest = $any($event.target).value">
              <option value="none">Nunca</option>
              <option value="daily">Diario</option>
              <option value="weekly">Semanal</option>
            </select>
          </div>
        </div>
        <button class="btn" (click)="savePrefs()" [disabled]="saving()">Guardar notificaciones</button>
      </section>

      <!-- Privacidad -->
      <section class="section">
        <h2 class="section-title">Privacidad</h2>
        <div class="field-group">
          <div class="field field--row">
            <div>
              <div class="label">Mostrar actividad a otros miembros</div>
              <div class="hint">Otros miembros pueden ver cuándo estuviste activo.</div>
            </div>
            <label class="toggle">
              <input
                type="checkbox"
                [checked]="profile().show_activity"
                (change)="profileDraft.show_activity = $any($event.target).checked"
              />
              <span class="toggle-track"></span>
            </label>
          </div>
          <div class="field field--row">
            <div>
              <div class="label">Mostrar email a otros miembros</div>
              <div class="hint">Tu dirección de email es visible en tu perfil.</div>
            </div>
            <label class="toggle">
              <input
                type="checkbox"
                [checked]="profile().show_email"
                (change)="profileDraft.show_email = $any($event.target).checked"
              />
              <span class="toggle-track"></span>
            </label>
          </div>
        </div>
        <button class="btn" (click)="saveProfile()" [disabled]="saving()">Guardar privacidad</button>
      </section>

      <!-- Actividad reciente -->
      <section class="section">
        <h2 class="section-title">Actividad reciente</h2>
        @if (auditLoading()) {
          <p class="muted">Cargando…</p>
        } @else if (auditEntries().length === 0) {
          <p class="muted">Sin actividad reciente.</p>
        } @else {
          <table class="audit-table">
            <thead>
              <tr>
                <th>Acción</th>
                <th>Recurso</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              @for (entry of auditEntries(); track entry.id) {
                <tr>
                  <td class="audit-action">{{ entry.action }}</td>
                  <td class="muted">{{ entry.resource_type }}{{ entry.resource_id ? ' · ' + entry.resource_id : '' }}</td>
                  <td class="muted">{{ formatDate(entry.created_at) }}</td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>
    </main>
  `,
  styles: [`
    .layout {
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 24px 64px;
    }
    .page-header { margin-bottom: 32px; }
    .page-title { font-size: 22px; font-weight: 700; color: var(--text); margin: 0 0 6px; }
    .page-subtitle { font-size: 14px; color: var(--text-muted); margin: 0; }

    .banner {
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 13px;
      margin-bottom: 24px;
    }
    .banner--ok { background: var(--ok-bg); border: 1px solid var(--ok); color: var(--ok); }
    .banner--error { background: var(--danger-bg); border: 1px solid var(--danger); color: var(--danger); }

    .section {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 24px;
    }
    .section-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      margin: 0 0 20px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .field-group { display: flex; flex-direction: column; gap: 16px; margin-bottom: 20px; }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field--row {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
    }

    .label { font-size: 13px; font-weight: 500; color: var(--text); }
    .hint { font-size: 11px; color: var(--text-muted); }
    .muted { color: var(--text-muted); font-size: 13px; }

    .input {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 10px;
      font-size: 13px;
      border-radius: 4px;
      width: 100%;
      box-sizing: border-box;
    }
    .input:focus { outline: none; border-color: var(--border-hover); }
    .input--textarea { resize: vertical; min-height: 72px; font-family: inherit; }

    .select {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 10px;
      font-size: 13px;
      border-radius: 4px;
      cursor: pointer;
    }
    .select:focus { outline: none; border-color: var(--border-hover); }

    /* Toggle */
    .toggle { position: relative; display: inline-block; width: 40px; height: 22px; flex-shrink: 0; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .toggle-track {
      position: absolute;
      inset: 0;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 22px;
      cursor: pointer;
      transition: background 0.2s, border-color 0.2s;
    }
    .toggle-track::after {
      content: '';
      position: absolute;
      left: 2px;
      top: 2px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--text-muted);
      transition: transform 0.2s, background 0.2s;
    }
    .toggle input:checked + .toggle-track { background: var(--ok-bg); border-color: var(--ok); }
    .toggle input:checked + .toggle-track::after { transform: translateX(18px); background: var(--ok); }

    .btn {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      color: var(--text-nav);
      padding: 8px 16px;
      font-size: 13px;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn:hover:not([disabled]) { border-color: var(--border-hover); color: var(--text); }
    .btn[disabled] { opacity: 0.5; cursor: not-allowed; }

    /* Audit table */
    .audit-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .audit-table th { color: var(--text-muted); font-weight: 500; text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
    .audit-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); }
    .audit-action { color: var(--text); }
  `],
})
export class ProfilePageComponent {
  private readonly userSvc = inject(UserService);
  readonly user = this.userSvc.user;

  readonly saving = signal(false);
  readonly saveOk = signal(false);
  readonly saveError = signal<string | null>(null);
  readonly auditLoading = signal(true);
  readonly auditEntries = signal<AuditEntry[]>([]);

  readonly profile = signal<Profile>({
    avatar_url: null,
    bio: null,
    display_name: null,
    show_activity: true,
    show_email: false,
  });

  readonly prefs = signal<Preferences>({
    theme: 'dark',
    language: 'es',
    timezone: 'UTC',
    reduced_motion: false,
    font_scale: 1.0,
    notification_email: true,
    notification_digest: 'weekly',
  });

  // Mutable drafts (bound by template event handlers)
  profileDraft: Partial<Profile> = {};
  prefsDraft: Partial<Preferences> = {};

  constructor() {
    this.loadProfile();
    this.loadPrefs();
    this.loadAudit();
  }

  private async loadProfile() {
    try {
      const res = await fetch('/auth/me/profile', { credentials: 'include' });
      if (res.ok) this.profile.set(await res.json());
    } catch { /* use defaults */ }
  }

  private async loadPrefs() {
    try {
      const res = await fetch('/auth/me/preferences', { credentials: 'include' });
      if (res.ok) this.prefs.set(await res.json());
    } catch { /* use defaults */ }
  }

  private async loadAudit() {
    this.auditLoading.set(true);
    try {
      const res = await fetch('/api/audit?limit=20', { credentials: 'include' });
      if (res.ok) this.auditEntries.set(await res.json());
    } catch { /* ignore */ }
    this.auditLoading.set(false);
  }

  async saveProfile() {
    this.saving.set(true);
    this.saveOk.set(false);
    this.saveError.set(null);
    try {
      const body = { ...this.profile(), ...this.profileDraft };
      const res = await fetch('/auth/me/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      this.profile.set(await res.json());
      this.profileDraft = {};
      this.saveOk.set(true);
      setTimeout(() => this.saveOk.set(false), 3000);
    } catch (err: unknown) {
      this.saveError.set(err instanceof Error ? err.message : 'Error al guardar');
    }
    this.saving.set(false);
  }

  async savePrefs() {
    this.saving.set(true);
    this.saveOk.set(false);
    this.saveError.set(null);
    try {
      const body = { ...this.prefs(), ...this.prefsDraft };
      const res = await fetch('/auth/me/preferences', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      this.prefs.set(await res.json());
      this.prefsDraft = {};
      this.saveOk.set(true);
      setTimeout(() => this.saveOk.set(false), 3000);
    } catch (err: unknown) {
      this.saveError.set(err instanceof Error ? err.message : 'Error al guardar');
    }
    this.saving.set(false);
  }

  formatDate(ts: number): string {
    return new Date(ts * 1000).toLocaleString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
