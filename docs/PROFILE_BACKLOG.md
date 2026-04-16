# Profile & Settings Split — Plan

Two scopes, two pages, one clean rule:
> If it follows the person everywhere → store on the user.
> If it depends on the workspace → store per tenant.

---

## Schema

### New tables

```sql
-- User-global UI preferences and notification settings
user_preferences (
  user_id    TEXT PRIMARY KEY REFERENCES users(id),
  theme               TEXT    DEFAULT 'dark',       -- dark | light | system
  language            TEXT    DEFAULT 'es',
  timezone            TEXT    DEFAULT 'UTC',
  reduced_motion      BOOLEAN DEFAULT false,
  font_scale          REAL    DEFAULT 1.0,           -- 0.8 | 1.0 | 1.2 | 1.5
  notification_email  BOOLEAN DEFAULT true,
  notification_digest TEXT    DEFAULT 'weekly'       -- none | daily | weekly
)

-- Public-facing profile fields + privacy controls
user_profiles (
  user_id       TEXT PRIMARY KEY REFERENCES users(id),
  avatar_url    TEXT,
  bio           TEXT,
  display_name  TEXT,         -- overrides users.name for display
  show_activity BOOLEAN DEFAULT true,   -- visible to other members
  show_email    BOOLEAN DEFAULT false
)

-- Workspace-scoped preferences (per user per tenant)
user_tenant_preferences (
  user_id          TEXT REFERENCES users(id),
  tenant_id        TEXT REFERENCES tenants(id),
  default_home_app TEXT,                -- app route to land on after login
  notify_app_ids   TEXT DEFAULT '[]',  -- JSON array of plugin_ids to notify from
  PRIMARY KEY (user_id, tenant_id)
)
```

### Extend `tenants` table
Add columns (ALTER TABLE … ADD COLUMN IF NOT EXISTS):
```sql
default_language     TEXT    DEFAULT 'es',
member_default_role  TEXT    DEFAULT 'member',
allowed_apps         TEXT    DEFAULT NULL,   -- JSON array of plugin_ids, NULL = all
notification_defaults TEXT   DEFAULT '{}'    -- JSON blob for tenant-wide notification policy
```

---

## API contracts

### Personal profile

```
GET /auth/me/profile
  Auth: require_auth
  Response: {
    avatar_url, bio, display_name,
    show_activity, show_email
  }

PATCH /auth/me/profile
  Auth: require_auth
  Body (all optional): {
    avatar_url, bio, display_name,
    show_activity, show_email
  }
  Response: updated profile fields

GET /auth/me/preferences
  Auth: require_auth
  Response: {
    theme, language, timezone,
    reduced_motion, font_scale,
    notification_email, notification_digest
  }

PATCH /auth/me/preferences
  Auth: require_auth
  Body (all optional): any subset of preferences fields
  Validation: theme ∈ {dark, light, system}; font_scale ∈ {0.8,1.0,1.2,1.5};
              notification_digest ∈ {none, daily, weekly}
  Response: updated preferences

GET /auth/me/tenant-preferences
  Auth: require_auth
  Response: { default_home_app, notify_app_ids }
  (scoped to caller's primary tenant)

PATCH /auth/me/tenant-preferences
  Auth: require_auth
  Body (all optional): { default_home_app, notify_app_ids }
  Response: updated tenant preferences
```

### Tenant settings

```
GET /api/tenants/:id/settings
  Auth: require_auth + must be member of tenant
  Response: {
    name,
    default_language,
    member_default_role,
    allowed_apps,       -- null = unrestricted
    notification_defaults
  }
  Visibility: all members (read-only for non-admins)

PATCH /api/tenants/:id/settings
  Auth: require_auth + role must be owner or admin
  Body (all optional): {
    name,
    default_language,
    member_default_role,
    allowed_apps,
    notification_defaults
  }
  Response: updated settings fields
```

---

## Routing split

| Route | Component | Access |
|---|---|---|
| `/profile` | `ProfilePageComponent` (new) | All logged-in users |
| `/settings` | `SettingsPageComponent` (renamed to Workspace) | All members (admin features gated inline) |

Regular members visiting `/settings` see tenant info and their own membership role, but not member management or install controls.

---

## UX changes

### Shell header
- Add avatar/initials button on the right side of `ShellHeaderComponent`
- Clicking opens a small dropdown: "Mi perfil" → `/profile`, "Cerrar sesión"
- Replaces the bare "Logout" button (logout moves into the dropdown)

### `/profile` page — `ProfilePageComponent`
Sections:
1. **Identity** — avatar upload, display name, bio
2. **Preferencias** — theme toggle, language, timezone, font scale, reduced motion
3. **Notificaciones** — email frequency, per-app notification toggles
4. **Privacidad** — show_activity, show_email toggles
5. **Sesiones activas** — list of recent sessions (requires session tracking, deferred)
6. **Actividad reciente** — last N audit_logs entries for this user (read from existing audit_logs)

### `/settings` page — rename & restructure
- Rename heading from "Configuración del espacio" → "Espacio de trabajo"
- Keep existing member management and app installs sections (admin-only)
- Add new **Workspace defaults** section (admin-only): default language, member default role, allowed apps
- Add **Facturación** section placeholder (links to B-011 when billing is built)
- Non-admins: show read-only tenant name, member list without edit controls

---

## Implementation order

1. **P-001** `[BE]` Schema — add `user_preferences`, `user_profiles`, `user_tenant_preferences`; extend `tenants`
2. **P-002** `[BE]` Profile + preferences endpoints — 5 endpoints above
3. **P-003** `[BE]` Tenant settings endpoints — GET + PATCH `/api/tenants/:id/settings`
4. **P-004** `[FE]` Shell header — avatar/initials + dropdown (logout moves here)
5. **P-005** `[FE]` `/profile` page — identity, preferences, privacy, activity feed
6. **P-006** `[FE]` `/settings` restructure — rename, add workspace defaults section, gate admin features properly for non-admins

---

## Deferred (not in initial scope)
- Avatar file upload (use URL input for now)
- Active sessions list (requires session table)
- Per-app notification granularity (add after billing + app installs stabilize)
- Tenant-scoped theme override (workspace branding — Phase 4+)
