import { TestBed } from '@angular/core/testing';
import { UserService } from './user.service';

describe('UserService', () => {
  let svc: UserService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    svc = TestBed.inject(UserService);
  });

  it('should start with null user', () => {
    expect(svc.user()).toBeNull();
  });

  it('isAdminOrOwner returns false when no user', () => {
    expect(svc.isAdminOrOwner()).toBe(false);
  });
});
