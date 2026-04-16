import {
  ChangeDetectionStrategy, Component,
  HostListener, inject
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AppRegistryService } from '../services/app-registry.service';
import { MicroFrontendLoaderComponent } from '../components/mfe-loader.component';
import { ShellHeaderComponent } from '../components/shell-header.component';

@Component({
  selector: 'app-dynamic-shell',
  standalone: true,
  imports: [MicroFrontendLoaderComponent, ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-shell-header />

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
    .error { padding: 24px; color: var(--danger); }
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
}
