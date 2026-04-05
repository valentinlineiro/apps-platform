import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(),
    provideServiceWorker('ngsw-worker.js', {
      enabled: true,
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
}).catch((err) => console.error(err));
