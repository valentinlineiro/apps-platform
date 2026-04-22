import {
  ChangeDetectionStrategy, Component, computed,
  inject, resource, signal,
} from '@angular/core';
import { UserService } from '../services/user.service';
import { ShellHeaderComponent } from '../components/shell-header.component';

interface AuditEntry {
  id: number;
  user_id: string | null;
  user_email: string | null;
  user_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: number;
}

@Component({
  selector: 'app-audit-page',
  standalone: true,
  imports: [ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './audit-page.component.html',
  styleUrl: './audit-page.component.css',
})
export class AuditPageComponent {
  private userSvc = inject(UserService);

  isAdmin = computed(() => this.userSvc.isAdminOrOwner());
  limit = signal(50);

  auditResource = resource<AuditEntry[], { limit: number; isAdmin: boolean }>({
    params: () => ({ limit: this.limit(), isAdmin: this.isAdmin() }),
    loader: ({ params }) => {
      if (!params.isAdmin) return Promise.resolve([]);
      return fetch(`/api/admin/audit?limit=${params.limit}`, { credentials: 'include' })
        .then(r => r.ok ? r.json() as Promise<AuditEntry[]> : Promise.resolve([]));
    },
  });

  entries = computed(() => this.auditResource.value() ?? []);
  loading = computed(() => this.auditResource.isLoading());

  formatDate(ts: number): string {
    return new Date(ts * 1000).toLocaleString('es-ES', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  }

  loadMore() {
    this.limit.update(n => n + 50);
  }
}
