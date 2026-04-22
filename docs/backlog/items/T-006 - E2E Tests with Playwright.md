---
id: T-006
title: E2E Tests with Playwright
audience: [human, ai]
last_updated: 2026-04-22
tags: [backlog, testing, e2e, playwright, quality]
source_of_truth: true
related: [T-002, T-005]
---

# T-006 - E2E Tests with Playwright

## Purpose
Add end-to-end tests covering the golden paths of the platform, running against the live `docker compose up` stack. Unit tests verify individual components; these tests verify the full chain: browser → Caddy → nginx → Flask backends → Postgres + Keycloak.

## When to use
Run before any release or after changes to auth, routing, or cross-service flows. Required to catch the class of bugs found during T-003/T-005 (auth misconfigurations, port errors, session mismatches).

## Content

### 🏗 Context & Motivation
Auth and routing bugs between services are invisible to unit tests. Today's issues (wrong port in `static_apps.json`, missing `PORTAL_SESSION_SECRET` in compose, `last_heartbeat NOT NULL`) would all have been caught immediately by a login + navigate + use-feature test.

### 🗺 Scope & Impact
- **New project**: `apps/portal-e2e/` (Nx Playwright project)
- **Config**: `playwright.config.ts` at repo root
- **CI**: New job in `.github/workflows/ci.yml`
- **Shared setup**: `apps/portal-e2e/src/global-setup.ts` (Keycloak login → `storageState`)

### ✅ Acceptance Criteria

#### Setup
- [x] `@nx/playwright` configured in `apps/portal-e2e/`
- [x] `playwright.config.ts` targets `https://localhost`, uses `caddy-root.crt` for TLS, and loads saved auth state
- [x] `global-setup.ts` logs in via Keycloak once and saves session to `.auth/user.json`
- [x] `.auth/` added to `.gitignore`
- [x] `nx e2e portal-e2e` runs all tests against the live stack

#### Test coverage
- [x] **auth.spec.ts** — unauthenticated `/` redirects to Keycloak; valid login lands on portal directory
- [x] **directory.spec.ts** — directory page shows exam-corrector and aneca-advisor cards; disabled apps are hidden
- [x] **exam-corrector.spec.ts** — navigate to exam-corrector; page loads the web component; upload form is visible
- [x] **aneca-advisor.spec.ts** — navigate to aneca-advisor; fields endpoint loads; submit an evaluation and get a verdict
- [x] **profile.spec.ts** — open profile page; change theme preference; reload and verify persisted

#### CI
- [ ] `e2e` job in CI spins up the stack with `docker compose up -d --wait`, runs `nx e2e portal-e2e`, tears down
- [ ] E2e job is gated: only runs on `main` push or manual trigger (not on every PR to keep CI fast)

### 🛠 Technical Constraints & References
- **Auth state**: Use Playwright's `storageState` — log in once in `global-setup.ts`, not in each test. The session cookie is shared across portal and aneca-advisor (same secret key).
- **TLS**: Pass `PLAYWRIGHT_IGNORE_HTTPS_ERRORS=true` OR configure `use: { ignoreHTTPSErrors: true }` in `playwright.config.ts` for the local dev target. Do not commit `caddy-root.crt` to the repo.
- **Keycloak test user**: Use the existing default admin credentials (`admin`/`admin`) or create a dedicated `test@platform.local` user in the realm JSON so CI has stable credentials.
- **Nx integration**: Add `e2e` target to `apps/portal-e2e/project.json` with `dependsOn: []` (stack must be up separately).
- **Timeouts**: Set `navigationTimeout: 15000` and `actionTimeout: 10000` — Keycloak login is slow on first cold start.
- **No test DB seeding needed** for the first iteration — the `_init_static_apps()` boot-time seed is sufficient to have apps available.

---

### 🚦 Status
- **Current Status**: `Done`
- **Priority**: `Medium`
- **Assignee**: —

## References
- [Playwright docs](https://playwright.dev/docs/intro)
- [`@nx/playwright` generator](https://nx.dev/nx-api/playwright)
- `apps/portal/nginx.conf` — routing reference for test URL paths
- `apps/portal/backend/static_apps.json` — expected apps in directory

## Change log
- **2026-04-22**: All test-coverage and setup criteria done (16/16 passing). CI job remains open.
- **2026-04-21**: Created. Covers login, directory, exam-corrector, aneca-advisor, profile.
