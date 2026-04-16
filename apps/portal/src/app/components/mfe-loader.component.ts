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
  templateUrl: './mfe-loader.component.html',
  styleUrl: './mfe-loader.component.css',
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
