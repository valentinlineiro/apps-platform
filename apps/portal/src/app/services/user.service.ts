import { Injectable, signal } from '@angular/core';

export interface TenantContext {
  id: string;
  name: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
}

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  provider: string;
  roles: string[];
  tenant: TenantContext | null;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private _user = signal<CurrentUser | null>(null);
  readonly user = this._user.asReadonly();

  async load(): Promise<CurrentUser | null> {
    try {
      const res = await fetch('/auth/me', { credentials: 'include' });
      if (!res.ok) return null;
      const data: CurrentUser = await res.json();
      this._user.set(data);
      return data;
    } catch {
      return null;
    }
  }

  isAdminOrOwner(): boolean {
    const role = this._user()?.tenant?.role;
    return role === 'owner' || role === 'admin';
  }
}
