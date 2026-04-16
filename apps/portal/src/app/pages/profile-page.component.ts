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

interface TenantPreferences {
  default_home_app: string | null;
  notify_app_ids: string[];
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
  templateUrl: './profile-page.component.html',
  styleUrl: './profile-page.component.css',
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

  readonly tenantPrefs = signal<TenantPreferences>({
    default_home_app: null,
    notify_app_ids: [],
  });

  // Mutable drafts (bound by template event handlers)
  profileDraft: Partial<Profile> = {};
  prefsDraft: Partial<Preferences> = {};
  tenantPrefsDraft: Partial<TenantPreferences> = {};

  constructor() {
    this.loadProfile();
    this.loadPrefs();
    this.loadTenantPrefs();
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

  private async loadTenantPrefs() {
    try {
      const res = await fetch('/auth/me/tenant-preferences', { credentials: 'include' });
      if (res.ok) this.tenantPrefs.set(await res.json());
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

  async saveTenantPrefs() {
    this.saving.set(true);
    this.saveOk.set(false);
    this.saveError.set(null);
    try {
      const body = { ...this.tenantPrefs(), ...this.tenantPrefsDraft };
      const res = await fetch('/auth/me/tenant-preferences', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      this.tenantPrefs.set(await res.json());
      this.tenantPrefsDraft = {};
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
