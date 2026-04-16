# Billing & Marketplace — Implementation Backlog

Single-vendor, Stripe-first paid app platform. Free apps use `price = 0` — entitlement is granted at install time, not automatically.
**All installs go through the same explicit flow** — free and paid are unified at `POST /api/tenants/:id/installs`.
All Stripe logic lives in the **portal backend** (Flask + Postgres).

Legend: `[BE]` backend · `[FE]` frontend · `[INF]` infrastructure

---

## Implementation order within Week 1–2

B-003 and B-007 are coupled — B-003 removes auto-install, B-007 adds entitlement gating. Deploy them together or you get a window where no installs work.

Safe order:
1. B-001 — additive schema, nothing breaks
2. B-002 — additive dependency, nothing breaks
3. B-006 — additive helpers, nothing breaks
4. **B-003 + B-007 together** — the breaking change
5. B-004, B-005 — Stripe checkout and webhooks, depend on schema and helpers being in place

---

## Week 1 — Schema + Stripe wiring

### B-001 `[BE]` Add billing schema
Add 6 tables to `_init_db()` in `apps/portal/backend/app.py`:

```sql
billing_customers (
  tenant_id TEXT PK → tenants.id,
  provider TEXT DEFAULT 'stripe',
  provider_customer_id TEXT NOT NULL UNIQUE
)

products (
  id TEXT PK,           -- same as plugin_id
  plugin_id TEXT → plugins.id,
  display_name TEXT NOT NULL,
  listing_status TEXT DEFAULT 'unlisted'  -- unlisted | listed | archived
)

prices (
  id TEXT PK,           -- Stripe price id, or generated uuid for free
  product_id TEXT → products.id,
  provider_price_id TEXT,   -- null for amount=0
  billing_period TEXT,      -- month | year | one_time | null for free
  amount INTEGER NOT NULL DEFAULT 0,  -- cents
  currency TEXT DEFAULT 'eur',
  trial_days INTEGER DEFAULT 0,
  active BOOLEAN DEFAULT true
)

subscriptions (
  id TEXT PK,           -- Stripe subscription id
  tenant_id TEXT → tenants.id,
  plugin_id TEXT,
  price_id TEXT → prices.id,
  status TEXT NOT NULL, -- active | trialing | past_due | canceled | unpaid
  current_period_end FLOAT,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at FLOAT NOT NULL,
  updated_at FLOAT NOT NULL
)

payment_events (
  id TEXT PK,           -- Stripe event id (idempotency key)
  type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  processed_at FLOAT NOT NULL
)

entitlements (
  id SERIAL PK,
  tenant_id TEXT → tenants.id,
  plugin_id TEXT,
  status TEXT NOT NULL,  -- active | trialing | expired | canceled
  source_subscription_id TEXT,  -- null for free/manual grants
  expires_at FLOAT,      -- null = no expiry (free)
  created_at FLOAT NOT NULL,
  updated_at FLOAT NOT NULL,
  UNIQUE(tenant_id, plugin_id)
)
```

**Acceptance criteria:**
- All 6 tables created idempotently via `IF NOT EXISTS`
- Existing tests still pass

---

### B-002 `[BE]` `[INF]` Add Stripe dependency + env config
- Add `stripe` to `apps/portal/backend/requirements.txt` (or install inline in Dockerfile)
- Add env vars to `docker-compose.yml` for portal-backend:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_PUBLISHABLE_KEY` (forwarded to frontend via `/auth/me` or a `/api/config` endpoint)
- Add to `CLAUDE.md` env section

**Acceptance criteria:**
- `import stripe` works inside the portal container
- Missing keys log a warning but don't crash startup

---

### B-003 `[BE]` Seed free product + price for existing plugins
On `_init_static_apps()` and `register()`, after syncing to `plugins`, upsert a `products` row and a `prices` row with `amount=0` if none exists yet.

Add helper `_ensure_free_product(conn, plugin_id, name)`.

**Do NOT auto-grant entitlements here.** Entitlements are only granted when a tenant explicitly installs the app (free apps) or when a Stripe webhook fires (paid apps). Also **remove** the existing `_install_plugin()` auto-install calls from `register()` and `_init_static_apps()` — no more silent installs.

**Acceptance criteria:**
- After boot, existing apps have a `products` row + a free `prices` row
- No entitlements or installs are created automatically
- Existing `plugin_installs` rows from before this migration are left untouched (don't delete them)
- `GET /api/registry` still works for tenants that already have installs

---

## Week 2 — Checkout, webhooks, entitlement gating

### B-004 `[BE]` `POST /api/billing/checkout-session`
```
Body: { plugin_id, price_id, success_url, cancel_url }
Auth: require_auth
```

- Look up or create a `billing_customers` row (Stripe `customers.create` if new)
- Create `stripe.checkout.Session` with `mode='subscription'` (or `'payment'` for one-time)
- For `trial_days > 0`, set `subscription_data.trial_period_days`
- Return `{ url }` — frontend redirects the browser there

**Acceptance criteria:**
- Returns 400 if price not found or not active
- Returns 403 if caller not tenant admin/owner
- Creates Stripe customer idempotently (stored in `billing_customers`)

---

### B-005 `[BE]` `POST /api/billing/webhooks/stripe`
No auth (Stripe signs the payload). Verify with `stripe.Webhook.construct_event`.

Idempotency: insert event id into `payment_events`; skip if already present (`ON CONFLICT DO NOTHING`, check rowcount).

Handle events:
| Event | Action |
|---|---|
| `checkout.session.completed` | Upsert subscription row; grant entitlement |
| `customer.subscription.created` | Upsert subscription row |
| `customer.subscription.updated` | Update status, period_end, cancel_at_period_end; sync entitlement |
| `customer.subscription.deleted` | Set status=canceled; expire entitlement |
| `invoice.paid` | Update subscription `current_period_end`; ensure entitlement active |
| `invoice.payment_failed` | Set subscription status=past_due; set entitlement status=past_due |

All event handling delegated to `_process_stripe_event(conn, event)`.

**Acceptance criteria:**
- Replaying the same event id is a no-op (200, skipped)
- Invalid signature → 400
- Missing secret → 500 with log

---

### B-006 `[BE]` Entitlement helper functions
```python
_ensure_entitlement(conn, tenant_id, plugin_id, status, source_subscription_id, expires_at)
_revoke_entitlement(conn, tenant_id, plugin_id)
_get_entitlement(conn, tenant_id, plugin_id) → dict | None
```

`_ensure_entitlement` does an upsert: insert or update status/expires_at/updated_at.

**Acceptance criteria:**
- Free apps auto-get `status='active'`, `expires_at=None`
- `_revoke_entitlement` sets `status='canceled'`, does not delete row (audit trail)

---

### B-007 `[BE]` Gate installs on entitlement (unified free + paid flow)
Change `POST /api/tenants/:id/installs`:
1. Look up `entitlements` for `(tenant_id, plugin_id)`
2. If no entitlement **and** a free price (`amount=0`) exists for the plugin → call `_ensure_entitlement(conn, tenant_id, plugin_id, status='active', source=None, expires_at=None)` → proceed
3. If no entitlement and no free price → 402 `{"error": "no_entitlement"}`
4. If entitlement exists but status not in `('active', 'trialing')` → 402 `{"error": "entitlement_inactive", "status": <status>}`
5. If entitlement valid → proceed with existing install logic

Also update `_active()` to join on `entitlements` (status active/trialing) instead of `plugin_installs.status`.

**Acceptance criteria:**
- Free app, no prior entitlement → entitlement auto-granted, install succeeds (200)
- Free app, second install attempt → idempotent (200)
- Paid app with active entitlement → 200
- Paid app without entitlement → 402
- Entitlement `past_due` or `canceled` → 402 with specific status in response body

---

## Week 3 — Marketplace UI + billing settings

### B-008 `[BE]` Marketplace API
```
GET /api/marketplace/apps
  → [{ plugin_id, name, description, icon, listing_status, prices: [{ id, amount, currency, billing_period, trial_days }] }]
  No auth required (public)

GET /api/marketplace/apps/:id
  → same shape for one app + full description
```

**Acceptance criteria:**
- Only returns `listing_status = 'listed'` products
- `prices` array only contains `active = true` prices
- No auth required

---

### B-009 `[FE]` Public marketplace page (`/marketplace`)
New route in `app.routes.ts`. New component `marketplace-page.component.ts`.

Shows app cards with:
- Icon, name, description
- Price (or "Gratis") + billing period
- Trial badge if `trial_days > 0`
- "Ver detalles" button → `/marketplace/:id`

**Acceptance criteria:**
- Accessible without login
- "Gratis" label for `amount = 0`

---

### B-010 `[FE]` App detail page (`/marketplace/:id`)
New component `marketplace-detail-page.component.ts`.

Shows:
- Full description
- All active prices with a "Suscribirse" / "Instalar gratis" button
- Calls `POST /api/billing/checkout-session` then redirects to Stripe

**Acceptance criteria:**
- Unauthenticated → redirect to login before checkout
- After successful Stripe redirect → show success state / redirect to settings

---

### B-011 `[FE]` Billing tab in settings
Add a "Facturación" tab (or section) to `settings-page.component.ts`.

Shows:
- Active subscriptions: app name, plan, status badge, next renewal date, cancel button
- `past_due` state → amber banner "Pago pendiente — actualiza tu método de pago" + link to customer portal
- `trialing` state → "Prueba hasta [date]"
- "Gestionar facturación" → calls `POST /api/billing/customer-portal` and redirects

Subscription state badge classes should reuse existing `--ok / --warn / --danger` CSS variables.

**Acceptance criteria:**
- Trial badge shows days remaining
- Past-due banner blocks app usage and shows portal link

---

### B-012 `[BE]` `POST /api/billing/customer-portal`
```
Auth: require_auth
```
- Look up `billing_customers` for caller's tenant
- Create `stripe.billing_portal.Session` with `return_url`
- Return `{ url }`

**Acceptance criteria:**
- 404 if tenant has no Stripe customer yet
- 403 if caller not admin/owner

---

### B-013 `[BE]` Admin pricing + listing endpoints
```
POST /api/admin/apps/:plugin_id/prices
  Body: { billing_period, amount, currency, trial_days }
  Creates price in Stripe + inserts into prices table

PATCH /api/admin/apps/:plugin_id/listing
  Body: { listing_status }   -- unlisted | listed | archived
  Updates products.listing_status

GET /api/admin/apps
  Returns all products with prices + install/subscription counts
```

Auth: `require_auth` + role must be `owner`.

**Acceptance criteria:**
- Creating a price with `amount=0` skips Stripe and sets `provider_price_id=null`
- Archiving a product does not cancel existing subscriptions

---

## Week 4 — Hardening + visibility

### B-014 `[BE]` Webhook idempotency + retry safety
- `payment_events` insert uses `ON CONFLICT(id) DO NOTHING`; check `rowcount == 0` to detect replay
- Wrap each event handler in a try/except; log errors but return 200 to Stripe (to prevent infinite retries on our bugs)
- Add `processed_ok BOOLEAN` column to `payment_events` so failed events are visible

**Acceptance criteria:**
- Replaying any event 10× produces identical final state
- Handler exception does not return 4xx/5xx to Stripe

---

### B-015 `[BE]` Billing state transition tests
New `tests/test_billing.py` covering:
- Free app → auto-entitlement granted at boot
- Paid app install without entitlement → 402
- Webhook `checkout.session.completed` → entitlement created, install succeeds
- Webhook `invoice.payment_failed` → entitlement past_due, install blocked
- Webhook `customer.subscription.deleted` → entitlement canceled
- Webhook replay → idempotent (state unchanged)

---

### B-016 `[BE]` `GET /api/tenants/:id/subscriptions`
```
Auth: require_auth + must be member of tenant
Returns: [{ plugin_id, name, icon, status, current_period_end, cancel_at_period_end, price }]
```

Joins `subscriptions` + `plugins` + `prices`.

---

### B-017 `[BE]` `[FE]` Admin operational views
Backend: `GET /api/admin/subscriptions?status=past_due` — list of tenants with billing issues.

Frontend: minimal admin page at `/admin` (owner-only route) showing:
- Total active subscriptions per app
- Past-due subscriptions with tenant name + email
- Failed payment events (from `payment_events` where `processed_ok=false`)

---

## Weeks 5–8 — Polish & production

### B-018 `[BE]` Email notifications
Trigger from webhook handler (or a queued job):
- Subscription activated → confirmation email
- `invoice.payment_failed` → "Update your payment method" email
- Trial ending in 3 days → reminder email

Use a simple SMTP helper (`SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` env vars). No external email service required for MVP.

---

### B-019 `[BE]` Analytics endpoint
`GET /api/admin/analytics`
- Installs per app (last 30 days)
- New subscriptions per week
- Churn (canceled this month)
- MRR estimate (sum of active subscription amounts)

---

### B-020 `[FE]` Legal pages
Static routes: `/terms`, `/privacy`. Rendered from markdown files in `apps/portal/src/assets/`.

---

### B-021 Security review checklist
- [ ] Stripe webhook signature verified on every call
- [ ] No entitlement granted from frontend success redirect alone
- [ ] Admin endpoints gated on `owner` role
- [ ] Stripe secret key never exposed to frontend
- [ ] `payment_events.payload_json` scrubbed of card data before storage
- [ ] Rate-limit `/api/billing/checkout-session` per tenant

---

### B-022 `[INF]` Production Stripe config
- Switch `STRIPE_SECRET_KEY` to live key in production env
- Set `STRIPE_WEBHOOK_SECRET` from Stripe dashboard webhook endpoint
- Add `STRIPE_PUBLISHABLE_KEY` to portal frontend config endpoint
- Verify webhook endpoint URL is publicly reachable (not behind VPN)

---

## Not in MVP (deferred)

| Item | Reason |
|---|---|
| Seller self-serve onboarding | Adds KYC, payout, and compliance complexity |
| Revenue sharing / payouts | Requires Stripe Connect |
| Usage-based billing | Metering API + significant backend work |
| Tax automation | Add Stripe Tax later if needed |
| Refund management UI | Handle manually via Stripe dashboard initially |
| Multi-currency pricing | Start with EUR only |
