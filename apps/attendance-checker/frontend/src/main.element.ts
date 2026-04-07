import { createApplication } from '@angular/platform-browser';
import { provideZonelessChangeDetection } from '@angular/core';
import { createCustomElement } from '@angular/elements';
import { AttendanceCheckerPageComponent } from '../attendance-checker-page.component';

createApplication({
  providers: [provideZonelessChangeDetection()]
}).then(app => {
  customElements.define(
    'attendance-checker-app',
    createCustomElement(AttendanceCheckerPageComponent, { injector: app.injector })
  );
}).catch(console.error);
