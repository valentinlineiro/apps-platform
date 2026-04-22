import { Routes } from '@angular/router';
import { AuditPageComponent } from './pages/audit-page.component';
import { DirectoryPageComponent } from './pages/directory-page.component';
import { DynamicAppShellComponent } from './pages/dynamic-app-shell.component';
import { ProfilePageComponent } from './pages/profile-page.component';
import { SettingsPageComponent } from './pages/settings-page.component';
import { AppManifest } from './services/app-registry.service';

export const STATIC_ROUTES: Routes = [
  { path: '', component: DirectoryPageComponent },
  { path: 'profile', component: ProfilePageComponent },
  { path: 'settings', component: SettingsPageComponent },
  { path: 'audit', component: AuditPageComponent },
];

export function buildDynamicRoutes(apps: AppManifest[]): Routes {
  const dynamicRoutes: Routes = apps
    .filter(app => app.scriptUrl && app.elementTag && app.route !== '')
    .map(app => ({
      path: app.route,
      component: DynamicAppShellComponent,
      data: { appId: app.id }
    }));

  return [
    ...STATIC_ROUTES,
    ...dynamicRoutes,
    { path: '**', redirectTo: '' }
  ];
}

// Default export for initial bootstrap, will be replaced dynamically
export const APP_ROUTES: Routes = [
  ...STATIC_ROUTES,
  { path: '**', redirectTo: '' }
];
