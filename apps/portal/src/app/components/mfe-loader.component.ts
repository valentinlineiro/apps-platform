import {
  AfterViewInit, ChangeDetectionStrategy, Component,
  CUSTOM_ELEMENTS_SCHEMA, DestroyRef, ElementRef,
  inject, input, signal, ViewChild
} from '@angular/core';

@Component({
  selector: 'app-mfe-loader',
  standalone: true,
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loading()) {
      <p class="status">Cargando...</p>
    }
    @if (error()) {
      <div class="error-box">
        <p class="error-title">{{ appName() || 'La aplicación' }} no está disponible en este momento.</p>
        <p class="error-hint">Intenta recargar la página. Si el problema persiste, contacta con soporte.</p>
      </div>
    }
    <div #elementHost></div>
  `,
  styles: [`
    .status { padding: 24px; color: var(--text-dim); font-size: 14px; }
    .error-box { padding: 24px; border: 1px solid var(--danger-border); background: var(--danger-bg); max-width: 480px; margin: 24px; }
    .error-title { margin: 0 0 6px; font-size: 14px; color: var(--danger); }
    .error-hint { margin: 0; font-size: 13px; color: var(--text-muted); }
  `]
})
export class MicroFrontendLoaderComponent implements AfterViewInit {
  @ViewChild('elementHost') private hostRef!: ElementRef<HTMLElement>;

  scriptUrl = input.required<string>();
  elementTag = input.required<string>();
  appName = input<string>('');

  loading = signal(true);
  error = signal('');
  private destroyed = false;

  constructor() {
    inject(DestroyRef).onDestroy(() => { this.destroyed = true; });
  }

  async ngAfterViewInit() {
    try {
      await this.loadScript(this.scriptUrl());
      if (this.destroyed) return;
      const el = document.createElement(this.elementTag());
      this.hostRef.nativeElement.appendChild(el);
    } catch {
      if (!this.destroyed) this.error.set('load-failed');
    }
    if (!this.destroyed) this.loading.set(false);
  }

  private loadScript(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const script = document.createElement('script');
      script.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Cannot load ${src}`));
      document.head.appendChild(script);
    });
  }
}
