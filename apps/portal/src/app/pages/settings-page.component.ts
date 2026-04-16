import {
  ChangeDetectionStrategy, Component, computed,
  inject, resource, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UserService } from '../services/user.service';
import { ShellHeaderComponent } from '../components/shell-header.component';

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
  template: `
    <app-shell-header [showSettings]="false" />
    <main class="layout">
      <h1>Configuración del espacio</h1>

      @if (tenant()) {
        <p class="tenant-id">{{ tenant()!.name }} <span class="muted">· {{ tenant()!.id }}</span></p>
      }

      <!-- ── Members ─────────────────────────────────────── -->
      <section class="section">
        <h2>Miembros</h2>

        @if (membersResource.isLoading()) {
          <p class="muted">Cargando...</p>
        } @else if (members().length === 0) {
          <p class="muted">Sin miembros.</p>
        } @else {
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Rol</th>
                @if (isAdmin()) { <th></th> }
              </tr>
            </thead>
            <tbody>
              @for (m of members(); track m.id) {
                <tr>
                  <td>{{ m.name }}</td>
                  <td class="muted">{{ m.email }}</td>
                  <td>
                    @if (isAdmin() && m.id !== currentUserId()) {
                      <select [ngModel]="m.role" (ngModelChange)="changeRole(m, $event)">
                        <option value="owner">owner</option>
                        <option value="admin">admin</option>
                        <option value="member">member</option>
                        <option value="viewer">viewer</option>
                      </select>
                    } @else {
                      <span class="role-badge role-{{ m.role }}">{{ m.role }}</span>
                    }
                  </td>
                  @if (isAdmin()) {
                    <td>
                      @if (m.id !== currentUserId()) {
                        <button class="btn-danger" type="button" (click)="removeMember(m)">Eliminar</button>
                      }
                    </td>
                  }
                </tr>
              }
            </tbody>
          </table>
        }

        @if (isAdmin()) {
          <form class="inline-form" (submit)="addMember($event)">
            <input type="email" [(ngModel)]="newEmail" name="email" placeholder="email@ejemplo.com" required />
            <select [(ngModel)]="newRole" name="role">
              <option value="member">member</option>
              <option value="viewer">viewer</option>
              <option value="admin">admin</option>
              <option value="owner">owner</option>
            </select>
            <button type="submit">Añadir</button>
          </form>
          @if (memberError()) { <p class="error">{{ memberError() }}</p> }
        }
      </section>

      <!-- ── Installed plugins ───────────────────────────── -->
      <section class="section">
        <h2>Aplicaciones instaladas</h2>

        @if (installsResource.isLoading()) {
          <p class="muted">Cargando...</p>
        } @else if (installs().length === 0) {
          <p class="muted">No hay aplicaciones instaladas.</p>
        } @else {
          <table>
            <thead>
              <tr>
                <th>Aplicación</th>
                <th>Estado</th>
                <th>Backend</th>
                @if (isAdmin()) { <th></th> }
              </tr>
            </thead>
            <tbody>
              @for (inst of installs(); track inst.plugin_id) {
                <tr>
                  <td>
                    {{ inst.manifest.icon ?? '📦' }} {{ inst.manifest.name ?? inst.plugin_id }}
                    <span class="muted small">{{ inst.plugin_id }}</span>
                  </td>
                  <td>
                    <span class="status-badge status-{{ inst.status }}">{{ inst.status }}</span>
                  </td>
                  <td>
                    @if (inst.alive) {
                      <span class="alive">● activo</span>
                    } @else {
                      <span class="dead">● inactivo</span>
                    }
                  </td>
                  @if (isAdmin()) {
                    <td class="actions">
                      @if (inst.status === 'active') {
                        <button class="btn-warn" type="button" (click)="setInstallStatus(inst, 'suspended')">Suspender</button>
                      } @else if (inst.status === 'suspended') {
                        <button class="btn-ok" type="button" (click)="setInstallStatus(inst, 'active')">Activar</button>
                      }
                      <button class="btn-danger" type="button" (click)="uninstall(inst)">Desinstalar</button>
                    </td>
                  }
                </tr>
              }
            </tbody>
          </table>
        }
        @if (installError()) { <p class="error">{{ installError() }}</p> }
      </section>

      <!-- ── Catalog ─────────────────────────────────────── -->
      @if (isAdmin()) {
        <section class="section">
          <h2>Catálogo de aplicaciones</h2>

          @if (catalogResource.isLoading()) {
            <p class="muted">Cargando...</p>
          } @else if (catalogEntries().length === 0) {
            <p class="muted">Todas las aplicaciones disponibles ya están instaladas.</p>
          } @else {
            <table>
              <thead>
                <tr>
                  <th>Aplicación</th>
                  <th>Descripción</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (entry of catalogEntries(); track entry.plugin_id) {
                  <tr>
                    <td>
                      {{ entry.icon }} {{ entry.name }}
                      <span class="muted small">v{{ entry.version }}</span>
                    </td>
                    <td class="muted">{{ entry.description }}</td>
                    <td>
                      <button class="btn-ok" type="button" (click)="installFromCatalog(entry)">Instalar</button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
          @if (catalogError()) { <p class="error">{{ catalogError() }}</p> }
        </section>
      }

    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 28px; }
    h1 { margin: 0 0 4px; font-size: 20px; }
    .tenant-id { margin: 0 0 24px; font-size: 14px; color: var(--text-nav); }
    .muted { color: var(--text-dim); }
    .small { display: block; font-size: 11px; margin-top: 2px; }
    .section { border: 1px solid var(--border); background: var(--bg-surface); padding: 20px; margin-bottom: 16px; }
    h2 { margin: 0 0 16px; font-size: 15px; font-weight: 600; color: var(--text-nav); }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--border); padding: 8px 10px; text-align: left; font-size: 13px; }
    th { color: var(--text-muted); font-weight: 500; }
    select { background: var(--bg-input); color: var(--text); border: 1px solid var(--border); padding: 4px 6px; font-size: 12px; }
    .role-badge { font-size: 11px; padding: 2px 6px; border-radius: 2px; }
    .role-owner  { background: var(--info-bg);   color: var(--info);   border: 1px solid var(--info-border); }
    .role-admin  { background: var(--ok-bg);     color: var(--ok);     border: 1px solid var(--ok-border); }
    .role-member { background: var(--bg-surface); color: var(--text-muted); border: 1px solid var(--border); }
    .role-viewer { background: var(--bg-surface); color: var(--text-dim);   border: 1px solid var(--border); }
    .status-badge { font-size: 11px; padding: 2px 6px; border-radius: 2px; }
    .status-active    { background: var(--ok-bg);   color: var(--ok);   border: 1px solid var(--ok-border); }
    .status-suspended { background: var(--warn-bg); color: var(--warn); border: 1px solid var(--warn-border); }
    .status-trial     { background: var(--info-bg); color: var(--info); border: 1px solid var(--info-border); }
    .alive { color: var(--ok);      font-size: 12px; }
    .dead  { color: var(--text-dim); font-size: 12px; }
    .actions { display: flex; gap: 6px; }
    .inline-form { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
    .inline-form input { flex: 1; min-width: 200px; padding: 8px; background: var(--bg-input); color: var(--text); border: 1px solid var(--border); font-size: 13px; }
    button { padding: 7px 12px; background: var(--bg-input); color: var(--text); border: 1px solid var(--border); cursor: pointer; font-size: 12px; }
    button:hover { border-color: var(--border-hover); }
    .btn-danger { border-color: var(--danger-border); color: var(--danger); }
    .btn-danger:hover { background: var(--danger-bg); }
    .btn-warn { border-color: var(--warn-border); color: var(--warn); }
    .btn-warn:hover { background: var(--warn-bg); }
    .btn-ok { border-color: var(--ok-border); color: var(--ok); }
    .btn-ok:hover { background: var(--ok-bg); }
    .error { color: var(--danger); font-size: 13px; margin-top: 8px; }
  `]
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

  members = computed(() => this.membersResource.value() ?? []);
  installs = computed(() => this.installsResource.value() ?? []);
  catalogEntries = computed(() => (this.catalogResource.value() ?? []).filter(e => !e.installed));

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
}
