import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
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
  templateUrl: './shell-header.component.html',
  styleUrl: './shell-header.component.css',
})
export class ShellHeaderComponent {
  title = input('');
  showSettings = input(true);

  readonly userService = inject(UserService);
  readonly menuOpen = signal(false);
  readonly avatarUrl = signal<string | null>(null);
  readonly isAdmin = computed(() => this.userService.isAdminOrOwner());

  constructor() {
    // Load avatar URL once after auth is known. Non-blocking: failure is silent.
    fetch('/auth/me/profile', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(p => { if (p?.avatar_url) this.avatarUrl.set(p.avatar_url); })
      .catch(() => {});
  }

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
