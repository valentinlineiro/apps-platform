import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ToastService } from '../services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="toast-container">
      @for (t of toastSvc.toasts(); track t.id) {
        <div class="toast toast-{{ t.type }}">
          <span class="toast-msg">{{ t.message }}</span>
          <button type="button" class="toast-close" (click)="toastSvc.dismiss(t.id)">×</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 1000;
      pointer-events: none;
    }
    .toast {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 14px;
      border: 1px solid var(--border);
      background: var(--bg-elevated);
      font-size: 13px;
      min-width: 280px;
      max-width: 420px;
      pointer-events: all;
    }
    .toast-ok    { border-color: var(--ok-border);     color: var(--ok); }
    .toast-warn  { border-color: var(--warn-border);   color: var(--warn); }
    .toast-error { border-color: var(--danger-border); color: var(--danger); }
    .toast-msg { flex: 1; line-height: 1.4; }
    .toast-close {
      background: none;
      border: none;
      cursor: pointer;
      color: inherit;
      font-size: 18px;
      line-height: 1;
      padding: 0;
      opacity: 0.7;
      flex-shrink: 0;
    }
    .toast-close:hover { opacity: 1; }
  `],
})
export class ToastContainerComponent {
  toastSvc = inject(ToastService);
}
