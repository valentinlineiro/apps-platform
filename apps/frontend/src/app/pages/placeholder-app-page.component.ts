import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-placeholder-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="layout">
      <a class="back" routerLink="/">← apps</a>
      <h1>attendance-checker</h1>
      <p class="subtitle">Esta app es un placeholder para futuras funcionalidades.</p>
      <section class="panel">
        <p>Próximamente podrás registrar asistencia por clase y exportar reportes.</p>
      </section>
    </main>
  `,
  styles: [`
    .layout { max-width: 860px; margin: 0 auto; padding: 24px; }
    .back { color: #999; text-decoration: none; font-size: 13px; }
    .subtitle { color: #888; }
    .panel { border: 1px solid #222; background: #141414; padding: 16px; margin-top: 16px; }
  `]
})
export class PlaceholderAppPageComponent {}
