import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Unified top bar used by every portal page and app shell.
 *
 * Usage:
 *   Directory  — <app-shell-header title="~/apps" />
 *   Settings   — <app-shell-header [showSettings]="false" />
 *   App shell  — <app-shell-header />
 */
@Component({
  selector: 'app-shell-header',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <div class="left">
        @if (title()) {
          <span class="title">{{ title() }}</span>
        } @else {
          <a class="back" routerLink="/">← Apps</a>
        }
      </div>
      <nav class="nav">
        @if (showSettings()) {
          <a class="nav-link" routerLink="/settings">Configuración</a>
        }
        <button class="logout" type="button" (click)="logout()">Logout</button>
      </nav>
    </header>
  `,
  styles: [`
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--bg-root);
    }
    .left { display: flex; align-items: center; }
    .title { font-size: 16px; font-weight: 600; color: var(--text); }
    .back {
      color: var(--text-nav);
      text-decoration: none;
      font-size: 14px;
    }
    .back:hover { color: var(--text); }
    .nav { display: flex; align-items: center; gap: 16px; }
    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
    }
    .nav-link:hover { color: var(--text-nav); }
    .logout {
      border: 1px solid var(--border);
      background: var(--bg-elevated);
      color: var(--text-nav);
      padding: 6px 12px;
      cursor: pointer;
      font-size: 12px;
    }
    .logout:hover { border-color: var(--border-hover); color: var(--text); }
  `],
})
export class ShellHeaderComponent {
  title = input('');
  showSettings = input(true);

  logout() {
    sessionStorage.removeItem('portal_login_attempted');
    window.location.assign('/auth/logout?next=%2F');
  }
}
