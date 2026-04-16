import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  inject,
  input,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { UserService } from '../services/user.service';

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
        <div class="avatar-wrap">
          <button
            class="avatar-btn"
            type="button"
            [attr.aria-label]="'Menú de usuario'"
            (click)="toggleMenu($event)"
          >{{ initials() }}</button>
          @if (menuOpen()) {
            <div class="dropdown">
              @if (userService.user(); as u) {
                <div class="dropdown-user">
                  <span class="dropdown-name">{{ u.name }}</span>
                  <span class="dropdown-email">{{ u.email }}</span>
                </div>
                <div class="dropdown-divider"></div>
              }
              <a class="dropdown-item" routerLink="/profile" (click)="menuOpen.set(false)">
                Mi perfil
              </a>
              <button class="dropdown-item dropdown-item--danger" type="button" (click)="logout()">
                Cerrar sesión
              </button>
            </div>
          }
        </div>
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

    /* Avatar button */
    .avatar-wrap { position: relative; }
    .avatar-btn {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 1px solid var(--border);
      background: var(--bg-elevated);
      color: var(--text);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .avatar-btn:hover { border-color: var(--border-hover); }

    /* Dropdown */
    .dropdown {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      min-width: 200px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 6px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
      z-index: 200;
      overflow: hidden;
    }
    .dropdown-user {
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .dropdown-name { font-size: 13px; font-weight: 600; color: var(--text); }
    .dropdown-email { font-size: 11px; color: var(--text-muted); }
    .dropdown-divider { height: 1px; background: var(--border); }
    .dropdown-item {
      display: block;
      width: 100%;
      padding: 10px 16px;
      font-size: 13px;
      color: var(--text-nav);
      text-decoration: none;
      background: none;
      border: none;
      text-align: left;
      cursor: pointer;
      box-sizing: border-box;
    }
    .dropdown-item:hover { background: var(--bg-surface); color: var(--text); }
    .dropdown-item--danger { color: var(--danger); }
    .dropdown-item--danger:hover { background: var(--bg-surface); color: var(--danger); }
  `],
})
export class ShellHeaderComponent {
  title = input('');
  showSettings = input(true);

  readonly userService = inject(UserService);
  readonly menuOpen = signal(false);

  initials() {
    const name = this.userService.user()?.name ?? '';
    if (!name) return '?';
    return name
      .split(/\s+/)
      .slice(0, 2)
      .map(w => w[0])
      .join('');
  }

  toggleMenu(event: MouseEvent) {
    event.stopPropagation();
    this.menuOpen.update(v => !v);
  }

  @HostListener('document:click')
  onDocumentClick() {
    this.menuOpen.set(false);
  }

  logout() {
    sessionStorage.removeItem('portal_login_attempted');
    window.location.assign('/auth/logout?next=%2F');
  }
}
