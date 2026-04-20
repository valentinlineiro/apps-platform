import { createApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { createCustomElement } from '@angular/elements';
import { DecimalPipe } from '@angular/common';
import { AnecaAdvisorAppComponent } from './aneca-advisor-app.component';

createApplication({
  providers: [
    provideZonelessChangeDetection(),
    provideHttpClient(),
    DecimalPipe,
  ],
}).then(app => {
  customElements.define(
    'aneca-advisor-app',
    createCustomElement(AnecaAdvisorAppComponent, { injector: app.injector }),
  );
}).catch(console.error);
