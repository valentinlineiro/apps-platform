import { Routes } from '@angular/router';
import { DirectoryPageComponent } from './pages/directory-page.component';
import { DynamicAppShellComponent } from './pages/dynamic-app-shell.component';
import { SettingsPageComponent } from './pages/settings-page.component';
import { AppManifest } from './services/app-registry.service';

export const STATIC_ROUTES: Routes = [
  { path: '', component: DirectoryPageComponent },
  { path: 'settings', component: SettingsPageComponent },
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
