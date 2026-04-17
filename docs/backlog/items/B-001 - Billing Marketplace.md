---
id: B-001
title: Billing & Marketplace Implementation
audience: [human, ai]
last_updated: 2026-04-17
tags: [backlog, billing, stripe, marketplace, business]
source_of_truth: true
related: [DOC-APP-POR-001, DOC-REF-ENV-001]
---

# B-001 - Billing & Marketplace Implementation

## Purpose
Implement a single-vendor, Stripe-first paid app platform within the portal.

## When to use
This is an active implementation track. Use this as the master plan for all billing-related tasks.

## Content

### 🏗 Context & Motivation
We need to monetize applications in the marketplace. The system uses a unified installation flow for both free and paid apps via `POST /api/tenants/:id/installs`. All Stripe logic is centralized in the portal backend.

### 🗺 Scope & Impact
- **Backend**: `apps/portal/backend/app.py`, new billing modules.
- **Frontend**: New marketplace and billing settings components in `apps/portal/src/app/`.
- **Infrastructure**: Stripe API integration and environment variables.

### ✅ Acceptance Criteria
- [ ] Schema: 6 new tables added to `_init_db()` (billing_customers, products, prices, subscriptions, payment_events, entitlements).
- [ ] Stripe Integration: `stripe` library working in backend with correct environment keys.
- [ ] Checkout: `POST /api/billing/checkout-session` returns a valid Stripe URL.
- [ ] Webhooks: `POST /api/billing/webhooks/stripe` handles subscription lifecycle events.
- [ ] Entitlements: Installation gated by active entitlements for paid apps.
- [ ] UI: Marketplace page and billing settings tab functional.

### 🛠 Technical Constraints & References
- **Coupling**: B-003 and B-007 must be deployed together to avoid breaking the install flow.
- **Stripe**: logic must be idempotent using `payment_events` table as a log.
- **Angular**: Standard component separation (HTML/CSS/TS) required.

---

### 🚦 Status
- **Current Status**: `Active`
- **Priority**: `High`
- **Assignee**: Gemini CLI

## References
- [Portal Deep Dive](../../apps/portal/index.md)
- [Stripe Documentation](https://stripe.com/docs)

## Change log
- **2026-04-17**: Reformatted to match the standardized AI-Ready Task Template.
