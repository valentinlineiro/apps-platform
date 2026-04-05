import { Routes } from '@angular/router';
import { DirectoryPageComponent } from './pages/directory-page.component';
import { ExamCorrectorPageComponent } from './pages/exam-corrector-page.component';
import { PlaceholderAppPageComponent } from './pages/placeholder-app-page.component';

export const APP_ROUTES: Routes = [
  { path: '', component: DirectoryPageComponent },
  { path: 'exam-corrector', component: ExamCorrectorPageComponent },
  { path: 'attendance-checker', component: PlaceholderAppPageComponent },
  { path: '**', redirectTo: '' }
];
