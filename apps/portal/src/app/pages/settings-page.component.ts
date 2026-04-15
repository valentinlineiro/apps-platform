import {
  ChangeDetectionStrategy, Component, computed,
  inject, resource, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { UserService } from '../services/user.service';

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

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [RouterLink, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="layout">
      <header class="topbar">
        <a class="back" routerLink="/">← Apps</a>
        <button class="logout" type="button" (click)="logout()">Logout</button>
      </header>

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

    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 28px; }
    .topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
    .back { color: #bbb; text-decoration: none; font-size: 14px; }
    .back:hover { color: #e8e8e8; }
    h1 { margin: 0 0 4px; font-size: 20px; }
    .tenant-id { margin: 0 0 24px; font-size: 14px; color: #aaa; }
    .muted { color: #666; }
    .small { display: block; font-size: 11px; margin-top: 2px; }
    .section { border: 1px solid #222; background: #141414; padding: 20px; margin-bottom: 16px; }
    h2 { margin: 0 0 16px; font-size: 15px; font-weight: 600; color: #ccc; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #2a2a2a; padding: 8px 10px; text-align: left; font-size: 13px; }
    th { color: #777; font-weight: 500; }
    select { background: #0f0f0f; color: #e8e8e8; border: 1px solid #2a2a2a; padding: 4px 6px; font-size: 12px; }
    .role-badge { font-size: 11px; padding: 2px 6px; border-radius: 2px; }
    .role-owner  { background: #1a1f2a; color: #7ab; border: 1px solid #2a3a4a; }
    .role-admin  { background: #1a2a1a; color: #5a9; border: 1px solid #2a4a2a; }
    .role-member { background: #1a1a1a; color: #999; border: 1px solid #333; }
    .role-viewer { background: #1a1a1a; color: #666; border: 1px solid #2a2a2a; }
    .status-badge { font-size: 11px; padding: 2px 6px; border-radius: 2px; }
    .status-active    { background: #1a2a1a; color: #5a9; border: 1px solid #2a4a2a; }
    .status-suspended { background: #2a1f00; color: #f5a623; border: 1px solid #3a2d00; }
    .status-trial     { background: #1a1f2a; color: #7ab; border: 1px solid #2a3a4a; }
    .alive { color: #5a9; font-size: 12px; }
    .dead  { color: #666; font-size: 12px; }
    .actions { display: flex; gap: 6px; }
    .inline-form { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
    .inline-form input { flex: 1; min-width: 200px; padding: 8px; background: #0f0f0f; color: #e8e8e8; border: 1px solid #2a2a2a; font-size: 13px; }
    button { padding: 7px 12px; background: #0f0f0f; color: #e8e8e8; border: 1px solid #2a2a2a; cursor: pointer; font-size: 12px; }
    button:hover { border-color: #444; }
    .btn-danger { border-color: #4a1a1a; color: #f88; }
    .btn-danger:hover { background: #1a0f0f; }
    .btn-warn { border-color: #3a2d00; color: #f5a623; }
    .btn-warn:hover { background: #1a1500; }
    .btn-ok { border-color: #2a4a2a; color: #5a9; }
    .btn-ok:hover { background: #1a2a1a; }
    .error { color: #f88; font-size: 13px; margin-top: 8px; }
    .logout { border: 1px solid #333; background: #191919; color: #ddd; padding: 8px 12px; cursor: pointer; }
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

  members = computed(() => this.membersResource.value() ?? []);
  installs = computed(() => this.installsResource.value() ?? []);

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

  logout() {
    sessionStorage.removeItem('portal_login_attempted');
    window.location.assign('/auth/logout?next=%2F');
  }
}
