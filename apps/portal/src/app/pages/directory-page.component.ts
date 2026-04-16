import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppRegistryService } from '../services/app-registry.service';
import { UserService } from '../services/user.service';
import { ShellHeaderComponent } from '../components/shell-header.component';

@Component({
  selector: 'app-directory-page',
  standalone: true,
  imports: [RouterLink, ShellHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './directory-page.component.html',
  styleUrl: './directory-page.component.css',
})
export class DirectoryPageComponent {
  registry = inject(AppRegistryService);
  userSvc = inject(UserService);
}
