import { Component, CUSTOM_ELEMENTS_SCHEMA, OnInit, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  template: `
    @if (checkingAuth()) {
      <p class="gate">Verificando sesión...</p>
    } @else if (!authenticated()) {
      <main class="gate-card">
        <h1 class="gate-title">~/apps</h1>
        <p class="gate-sub">Portal de herramientas internas. Necesitas una cuenta para continuar.</p>
        <a class="login-btn" [href]="loginHref()">Iniciar sesión</a>
      </main>
    } @else if (authError()) {
      <main class="gate-card">
        <h1 class="gate-title">~/apps</h1>
        <p class="gate-error">{{ authError() }}</p>
        <a class="login-btn" href="/auth/login?next=%2F">Volver a intentar</a>
      </main>
    } @else {
      <router-outlet></router-outlet>
    }
  `,
  styles: [`
    .gate {
      margin: 80px auto;
      max-width: 420px;
      color: #666;
      font-size: 14px;
      padding: 0 28px;
    }
    .gate-card {
      margin: 80px auto;
      max-width: 420px;
      padding: 32px;
      border: 1px solid #2a2a2a;
      background: #141414;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .gate-title { margin: 0; font-size: 20px; color: #e8e8e8; }
    .gate-sub { margin: 0; font-size: 14px; color: #888; }
    .gate-error { margin: 0; font-size: 14px; color: #ff9e9e; }
    .login-btn {
      display: inline-block;
      margin-top: 4px;
      padding: 10px 20px;
      background: #1a2a1a;
      border: 1px solid #2a5a2a;
      color: #5a9;
      text-decoration: none;
      font-size: 14px;
      align-self: flex-start;
    }
  `]
})
export class AppComponent implements OnInit {
  private static readonly LOGIN_ATTEMPT_KEY = 'portal_login_attempted';
  checkingAuth = signal(true);
  authenticated = signal(false);
  authError = signal('');

  async ngOnInit() {
    try {
      const res = await fetch('/auth/me', { credentials: 'include' });
      if (res.ok) {
        sessionStorage.removeItem(AppComponent.LOGIN_ATTEMPT_KEY);
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
