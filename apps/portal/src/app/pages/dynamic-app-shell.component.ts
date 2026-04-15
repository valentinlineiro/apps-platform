import {
  ChangeDetectionStrategy, Component,
  HostListener, inject
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AppRegistryService } from '../services/app-registry.service';
import { MicroFrontendLoaderComponent } from '../components/mfe-loader.component';

@Component({
  selector: 'app-dynamic-shell',
  standalone: true,
  imports: [MicroFrontendLoaderComponent, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <a class="link" href="/" (click)="navigateHome($event)">← Apps</a>
      <nav class="nav">
        <a class="link" routerLink="/settings">Configuración</a>
        <button class="logout" type="button" (click)="logout()">Logout</button>
      </nav>
    </header>
    
    @if (manifest()) {
      <app-mfe-loader
        [scriptUrl]="manifest()!.scriptUrl!"
        [elementTag]="manifest()!.elementTag!"
        [appName]="manifest()!.name" />
    } @else {
      <p class="error">App not found or not configured for frontend.</p>
    }
  `,
  styles: [`
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 24px 0;
    }
    .nav { display: flex; align-items: center; gap: 12px; }
    .link { color: #bbb; text-decoration: none; font-size: 14px; }
    .link:hover { color: #e8e8e8; }
    .logout {
      border: 1px solid #333;
      background: #191919;
      color: #ddd;
      padding: 8px 12px;
      cursor: pointer;
    }
    .error { padding: 24px; color: #f88; }
  `]
})
export class DynamicAppShellComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private registry = inject(AppRegistryService);

  manifest = () => {
    const appId = this.route.snapshot.data['appId'];
    return this.registry.apps().find(a => a.id === appId);
  };

  @HostListener('app-navigate', ['$event'])
  onNavigate(e: Event) {
    this.router.navigate([(e as CustomEvent).detail]);
  }

  navigateHome(e: Event) {
    e.preventDefault();
    this.router.navigate(['/']);
  }

  async logout() {
    sessionStorage.removeItem('portal_login_attempted');
    window.location.assign('/auth/logout?next=%2F');
  }
}
