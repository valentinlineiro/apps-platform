import { Component, CUSTOM_ELEMENTS_SCHEMA, inject, OnInit, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { UserService } from './services/user.service';
import { ToastContainerComponent } from './components/toast-container.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ToastContainerComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  private static readonly LOGIN_ATTEMPT_KEY = 'portal_login_attempted';
  private userService = inject(UserService);
  checkingAuth = signal(true);
  authenticated = signal(false);
  authError = signal('');

  async ngOnInit() {
    try {
      const res = await fetch('/auth/me', { credentials: 'include' });
      if (res.ok) {
        sessionStorage.removeItem(AppComponent.LOGIN_ATTEMPT_KEY);
        this.userService.load();
        this.authenticated.set(true);
      }
      if (res.status === 401) {
        if (sessionStorage.getItem(AppComponent.LOGIN_ATTEMPT_KEY)) {
          this.authError.set('Login failed. Please try again.');
        } else {
          this.redirectToLogin();
          return;
        }
      }
    } catch {
      // Leave the app usable if auth endpoint is temporarily unavailable.
    }
    this.checkingAuth.set(false);
  }

  loginHref(): string {
    const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    return `/auth/login?next=${encodeURIComponent(next || '/')}`;
  }

  private redirectToLogin() {
    if (window.location.pathname.startsWith('/auth/')) return;
    sessionStorage.setItem(AppComponent.LOGIN_ATTEMPT_KEY, '1');
    const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    const nextWithMarker = this.withLoginAttemptMarker(next || '/');
    window.location.assign(`/auth/login?next=${encodeURIComponent(nextWithMarker)}`);
  }

  private withLoginAttemptMarker(next: string): string {
    const [pathAndQuery, hash = ''] = next.split('#', 2);
    const [path, query = ''] = pathAndQuery.split('?', 2);
    const params = new URLSearchParams(query);
    params.set('login_attempted', '1');
    const queryString = params.toString();
    const hashPart = hash ? `#${hash}` : '';
    return `${path}${queryString ? `?${queryString}` : ''}${hashPart}`;
  }
}
