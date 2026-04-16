import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppRegistryService } from '../services/app-registry.service';
import { UserService } from '../services/user.service';
import { ShellHeaderComponent } from '../components/shell-header.component';

@Component({
  selector: 'app-directory-page',
  standalone: true,
  imports: [RouterLink, ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-shell-header title="~/apps" />
    <main class="layout">
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
    .subtitle { color: var(--text-muted); margin: 0 0 20px; font-size: 14px; }
    .card {
      display: block;
      border: 1px solid var(--border);
      background: var(--bg-surface);
      padding: 16px;
      color: var(--text);
      text-decoration: none;
      max-width: 420px;
      margin-bottom: 12px;
    }
    .card:hover { border-color: var(--border-hover); background: #181818; }
    .card.wip { opacity: 0.65; }
    .card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .card h2 { margin: 0; font-size: 16px; }
    .card p { margin: 0; color: var(--text-muted); font-size: 14px; }
    .badge { font-size: 10px; font-weight: 600; letter-spacing: 0.05em; padding: 2px 6px; border-radius: 2px; text-transform: uppercase; }
    .badge-wip { background: var(--warn-bg); color: var(--warn); border: 1px solid var(--warn-border); }
  `]
})
export class DirectoryPageComponent {
  registry = inject(AppRegistryService);
  userSvc = inject(UserService);
}
