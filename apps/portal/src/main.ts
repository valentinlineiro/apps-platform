import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { provideRouter, Router } from '@angular/router';
import { provideZonelessChangeDetection, APP_INITIALIZER, inject } from '@angular/core';
import { AppComponent } from './app/app.component';
import { buildDynamicRoutes, STATIC_ROUTES } from './app/app.routes';
import { AppRegistryService } from './app/services/app-registry.service';

const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);

async function initializeApp(registry: AppRegistryService, router: Router) {
  const apps = await registry.loadRegistry();
  const dynamicRoutes = buildDynamicRoutes(apps);
  router.resetConfig(dynamicRoutes);
}

bootstrapApplication(AppComponent, {
  providers: [
    provideZonelessChangeDetection(),
    provideHttpClient(),
    provideRouter(STATIC_ROUTES),
    {
      provide: APP_INITIALIZER,
      useFactory: (registry: AppRegistryService, router: Router) => () => initializeApp(registry, router),
      deps: [AppRegistryService, Router],
      multi: true
    },
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isLocalhost,
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
}).catch((err) => console.error(err));
