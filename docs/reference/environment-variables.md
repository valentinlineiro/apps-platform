---
id: DOC-REF-ENV-001
title: Environment Variables Reference
audience: [human, ai]
last_updated: 2026-04-17
tags: [reference, environment, configuration, secrets]
source_of_truth: true
related: [DOC-CON-002]
---

# Environment Variables Reference

## Purpose
This document provides a comprehensive list of environment variables required by the various services in the platform.

## When to use
Consult this reference when setting up new environments (Staging/Production) or debugging configuration issues.

## Content

### Portal Backend
- `PORTAL_SESSION_SECRET`: Flask session secret.
- `SESSION_COOKIE_SECURE`: Set `true` in production (HTTPS); default `true` in Docker.
- `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`: OIDC client credentials.
- `OAUTH_AUTHORIZE_URL`, `OAUTH_TOKEN_URL`, `OAUTH_USERINFO_URL`: OIDC endpoints.
- `OAUTH_REDIRECT_URI`: Callback URL (default in Docker: `https://localhost/auth/callback`).
- `OAUTH_PROVIDER`: Provider name (default: `oidc`; `keycloak` in Docker).
- `OAUTH_VERIFY_SSL`: Set `false` in Docker (self-signed cert from Caddy).
- `DATABASE_URL`: Postgres connection string.
- `HEARTBEAT_TTL`: Seconds before an app is considered stale (default: `60`).

### Exam Corrector Backend
- `PORTAL_BACKEND_URL`: Registry service URL (default: `http://portal-backend:5000`).
- `ALLOWED_ORIGINS`: CORS origins (default: `http://localhost:4200`).
- `UPLOAD_MAX_AGE_SECONDS`: Age before temp upload files are purged (default: `86400`).
- `GEMINI_API_KEY`: Required for AI-powered OMR.

## References
- [Infrastructure Overview](../concepts/infrastructure.md)
- `.env.example` in the root directory.

## Change log
- **2026-04-17**: Initial version moved to `reference/` and standardized.
