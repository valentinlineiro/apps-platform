import { Injectable, signal, inject, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class TranslationService {
  private http = inject(HttpClient);

  // Signals for state
  readonly currentLanguage = signal<string>(localStorage.getItem('preferred_language') || 'es');
  private readonly translations = signal<Record<string, any>>({});
  private readonly loadedNamespaces = new Set<string>();

  constructor() {
    // Listen for cross-MFE language changes
    window.addEventListener('PLATFORM_LANGUAGE_CHANGED', (event: any) => {
      const newLang = event.detail;
      if (newLang && newLang !== this.currentLanguage()) {
        this.setLanguage(newLang);
      }
    });
  }

  /**
   * Update the current language and notify the platform.
   */
  async setLanguage(lang: string) {
    if (lang === this.currentLanguage()) return;

    this.currentLanguage.set(lang);
    localStorage.setItem('preferred_language', lang);

    // Broadcast change to other MFEs
    window.dispatchEvent(
      new CustomEvent('PLATFORM_LANGUAGE_CHANGED', { detail: lang })
    );

    // Reload all currently registered namespaces for the new language
    for (const ns of this.loadedNamespaces) {
      this.loadTranslations(ns, lang);
    }
  }

  /**
   * Load a translation bundle (JSON) from a specific namespace/path.
   * e.g., loadTranslations('portal', 'en') -> fetches /i18n/portal/en.json
   */
  async loadTranslations(namespace: string, lang: string) {
    this.loadedNamespaces.add(namespace);
    const url = `/i18n/${namespace}/${lang}.json`;
    try {
      const data = await firstValueFrom(this.http.get<Record<string, any>>(url));
      this.translations.update((prev) => ({
        ...prev,
        ...data,
      }));
    } catch (error) {
      console.error(`Failed to load translations for ${namespace} in ${lang}:`, error);
    }
  }

  /**
   * Synchronously translate a key using the current signal state.
   * Supports dot notation: 'COMMON.SAVE'
   */
  translate(key: string, params?: Record<string, any>): string {
    const keys = key.split('.');
    let value = this.translations();

    for (const k of keys) {
      value = value?.[k];
    }

    if (typeof value !== 'string') {
      return key; // Return the key if not found
    }

    // Basic interpolation: "Hello {{name}}"
    if (params) {
      return Object.entries(params).reduce(
        (acc, [k, v]) => acc.replace(`{{${k}}}`, String(v)),
        value
      );
    }

    return value;
  }
}
