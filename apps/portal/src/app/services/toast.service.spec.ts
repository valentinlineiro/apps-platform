import { TestBed } from '@angular/core/testing';
import { ToastService } from './toast.service';

describe('ToastService', () => {
  let svc: ToastService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    svc = TestBed.inject(ToastService);
  });

  it('should start with empty toasts', () => {
    expect(svc.toasts()).toEqual([]);
  });

  it('should add a toast', () => {
    svc.show('hello', 'ok', 60000);
    expect(svc.toasts().length).toBe(1);
    expect(svc.toasts()[0].message).toBe('hello');
  });

  it('should dismiss a toast by id', () => {
    svc.show('bye', 'ok', 60000);
    const id = svc.toasts()[0].id;
    svc.dismiss(id);
    expect(svc.toasts()).toEqual([]);
  });
});
