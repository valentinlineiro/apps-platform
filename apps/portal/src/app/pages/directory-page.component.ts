import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppRegistryService } from '../services/app-registry.service';
import { UserService } from '../services/user.service';

@Component({
  selector: 'app-directory-page',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="layout">
      <header class="topbar">
        <h1>~/apps</h1>
        <nav class="nav">
          <a class="nav-link" routerLink="/settings">Configuración</a>
          <button class="logout" type="button" (click)="logout()">Logout</button>
        </nav>
      </header>
      <p class="subtitle">Herramientas internas disponibles para tu equipo</p>
      @for (app of registry.apps(); track app.id) {
        @if (app.status !== 'disabled' && app.route !== '') {
          <a class="card" [routerLink]="'/' + app.route" [class.wip]="app.status === 'wip'">
            <div class="card-header">
              <h2>{{ app.icon }} {{ app.name }}</h2>
              @if (app.status === 'wip') {
                <span class="badge badge-wip">piloto</span>
              }
            </div>
            <p>{{ app.description }}</p>
          </a>
        }
      }
    </main>
  `,
  styles: [`
    .layout { max-width: 900px; margin: 0 auto; padding: 28px; }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    h1 { font-size: 20px; margin: 0; }
    .subtitle { color: #888; margin: 8px 0 16px; font-size: 14px; }
    .card {
      display: block;
      border: 1px solid #2a2a2a;
      background: #141414;
      padding: 16px;
      color: #e8e8e8;
      text-decoration: none;
      max-width: 420px;
      margin-bottom: 12px;
    }
    .card:hover { border-color: #3a3a3a; background: #181818; }
    .card.wip { opacity: 0.65; }
    .card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .card h2 { margin: 0; font-size: 16px; }
    .card p { margin: 0; color: #999; font-size: 14px; }
    .badge { font-size: 10px; font-weight: 600; letter-spacing: 0.05em; padding: 2px 6px; border-radius: 2px; text-transform: uppercase; }
    .badge-wip { background: #2a1f00; color: #f5a623; border: 1px solid #3a2d00; }
    .nav { display: flex; align-items: center; gap: 12px; }
    .nav-link { color: #888; text-decoration: none; font-size: 13px; }
    .nav-link:hover { color: #ccc; }
    .logout {
      border: 1px solid #333;
      background: #191919;
      color: #ddd;
      padding: 8px 12px;
      cursor: pointer;
    }
  `]
})
export class DirectoryPageComponent {
  registry = inject(AppRegistryService);
  userSvc = inject(UserService);

  async logout() {
    sessionStorage.removeItem('portal_login_attempted');
    window.location.assign('/auth/logout?next=%2F');
  }
}
