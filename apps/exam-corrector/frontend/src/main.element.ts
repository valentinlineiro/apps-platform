import { createApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { createCustomElement } from '@angular/elements';
import { ExamCorrectorPageComponent } from './exam-corrector-page.component';

createApplication({
  providers: [
    provideZonelessChangeDetection(),
    provideHttpClient(),
  ]
}).then(app => {
  customElements.define(
    'exam-corrector-app',
    createCustomElement(ExamCorrectorPageComponent, { injector: app.injector })
  );
}).catch(console.error);
