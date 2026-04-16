import {
  ChangeDetectionStrategy, Component, computed,
  inject, resource, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UserService } from '../services/user.service';
import { ShellHeaderComponent } from '../components/shell-header.component';

interface WorkspaceSettings {
  name: string;
  default_language: string;
  member_default_role: string;
  allowed_apps: string[] | null;
  notification_defaults: Record<string, unknown>;
}

interface Member {
  id: string;
  email: string;
  name: string;
  role: string;
  joined_at: number;
}

interface Install {
  plugin_id: string;
  status: 'active' | 'suspended' | 'trial';
  installed_at: number;
  installed_by: string | null;
  alive: boolean;
  manifest: { name?: string; icon?: string; description?: string };
}

interface CatalogEntry {
  plugin_id: string;
  name: string;
  description: string;
  icon: string;
  version: string;
  installed: boolean;
  install_status: string | null;
}

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [FormsModule, ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './settings-page.component.html',
  styleUrl: './settings-page.component.css',
})
export class SettingsPageComponent {
  private userSvc = inject(UserService);

  tenant = computed(() => this.userSvc.user()?.tenant ?? null);
  currentUserId = computed(() => this.userSvc.user()?.id ?? '');
  isAdmin = computed(() => this.userSvc.isAdminOrOwner());

  newEmail = signal('');
  newRole = signal('member');
  memberError = signal('');
  installError = signal('');
  catalogError = signal('');
  wsError = signal('');
  wsSaved = signal(false);
  wsSaving = signal(false);
  wsSettingsDraft: Partial<WorkspaceSettings> = {};

  membersResource = resource({
    params: () => this.tenant()?.id,
    loader: ({ params: tid }) =>
      tid ? fetch(`/api/tenants/${tid}/members`).then(r => r.json()) as Promise<Member[]> : Promise.resolve([]),
  });

  installsResource = resource({
    params: () => this.tenant()?.id,
    loader: ({ params: tid }) =>
      tid ? fetch(`/api/tenants/${tid}/installs`).then(r => r.json()) as Promise<Install[]> : Promise.resolve([]),
  });

  catalogResource = resource({
    params: () => this.tenant()?.id,
    loader: () => fetch('/api/catalog').then(r => r.json()) as Promise<CatalogEntry[]>,
  });

  wsSettingsResource = resource({
    params: () => this.tenant()?.id,
    loader: ({ params: tid }) =>
      tid
        ? fetch(`/api/tenants/${tid}/settings`, { credentials: 'include' }).then(r => r.json()) as Promise<WorkspaceSettings>
        : Promise.resolve({ name: '', default_language: 'es', member_default_role: 'member', allowed_apps: null, notification_defaults: {} }),
  });

  members = computed(() => this.membersResource.value() ?? []);
  installs = computed(() => this.installsResource.value() ?? []);
  catalogEntries = computed(() => (this.catalogResource.value() ?? []).filter(e => !e.installed));
  wsSettings = computed(() => this.wsSettingsResource.value() ?? { name: '', default_language: 'es', member_default_role: 'member', allowed_apps: null, notification_defaults: {} });

  allowedAppsDisplay = computed(() => {
    const apps = this.wsSettings().allowed_apps;
    return apps ? apps.join(', ') : '';
  });

  onAllowedAppsInput(value: string) {
    const trimmed = value.trim();
    this.wsSettingsDraft.allowed_apps = trimmed
      ? trimmed.split(',').map(s => s.trim()).filter(Boolean)
      : null;
  }

  async addMember(ev: Event) {
    ev.preventDefault();
    const tid = this.tenant()?.id;
    if (!tid) return;
    this.memberError.set('');
    const res = await fetch(`/api/tenants/${tid}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: this.newEmail(), role: this.newRole() }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      this.memberError.set(data.error ?? 'Error al añadir miembro.');
      return;
    }
    this.newEmail.set('');
    this.membersResource.reload();
  }

  async changeRole(member: Member, role: string) {
    const tid = this.tenant()?.id;
    if (!tid) return;
    const res = await fetch(`/api/tenants/${tid}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: member.email, role }),
    });
    if (res.ok) this.membersResource.reload();
  }

  async removeMember(member: Member) {
    const tid = this.tenant()?.id;
    if (!tid) return;
    const res = await fetch(`/api/tenants/${tid}/members/${member.id}`, { method: 'DELETE' });
    if (res.ok) this.membersResource.reload();
  }

  async setInstallStatus(inst: Install, status: string) {
    const tid = this.tenant()?.id;
    if (!tid) return;
    this.installError.set('');
    const res = await fetch(`/api/tenants/${tid}/installs/${inst.plugin_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      this.installError.set('Error al actualizar el estado.');
      return;
    }
    this.installsResource.reload();
  }

  async uninstall(inst: Install) {
    const tid = this.tenant()?.id;
    if (!tid) return;
    this.installError.set('');
    const res = await fetch(`/api/tenants/${tid}/installs/${inst.plugin_id}`, { method: 'DELETE' });
    if (!res.ok) {
      this.installError.set('Error al desinstalar.');
      return;
    }
    this.installsResource.reload();
  }

  async installFromCatalog(entry: CatalogEntry) {
    const tid = this.tenant()?.id;
    if (!tid) return;
    this.catalogError.set('');
    const res = await fetch(`/api/tenants/${tid}/installs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plugin_id: entry.plugin_id }),
    });
    if (!res.ok) {
      this.catalogError.set('Error al instalar la aplicación.');
      return;
    }
    this.installsResource.reload();
    this.catalogResource.reload();
  }

  async saveWsSettings() {
    const tid = this.tenant()?.id;
    if (!tid) return;
    this.wsError.set('');
    this.wsSaved.set(false);
    this.wsSaving.set(true);
    try {
      const body = { ...this.wsSettings(), ...this.wsSettingsDraft };
      const res = await fetch(`/api/tenants/${tid}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error ?? 'Error al guardar');
      this.wsSettingsDraft = {};
      this.wsSettingsResource.reload();
      this.wsSaved.set(true);
      setTimeout(() => this.wsSaved.set(false), 3000);
    } catch (err: unknown) {
      this.wsError.set(err instanceof Error ? err.message : 'Error al guardar');
    }
    this.wsSaving.set(false);
  }
}
