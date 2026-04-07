import { Injectable, resource, signal } from '@angular/core';

export interface AppManifest {
  id: string;
  name: string;
  description: string;
  route: string;
  icon: string;
  status: 'stable' | 'wip' | 'disabled';
  backend: { pathPrefix: string } | null;
  scriptUrl?: string;
  elementTag?: string;
}

@Injectable({ providedIn: 'root' })
export class AppRegistryService {
  private _apps = signal<AppManifest[]>([]);
  readonly apps = this._apps.asReadonly();

  async loadRegistry(): Promise<AppManifest[]> {
    try {
      const response = await fetch('/api/registry');
      if (!response.ok) return [];
      const data = await response.json();
      this._apps.set(data);
      return data;
    } catch (e) {
      console.error('Failed to load registry', e);
      return [];
    }
  }
}
