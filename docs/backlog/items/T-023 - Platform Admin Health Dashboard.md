---
id: T-023
title: Platform Admin Health Dashboard
audience: [human, ai]
last_updated: 2026-04-22
tags: [frontend, ops, health, monitoring]
source_of_truth: true
---

# T-023 - Platform Admin Health Dashboard

## 🏗 Context & Motivation
As the number of services and MFEs grows, platform administrators need a single pane of glass to monitor system health, view audit logs, and manage registered applications.

## 🗺 Scope & Impact
- **Frontend Components**: New admin view in `apps/portal/src/app/...`
- **Backend Endpoints**: Health aggregation endpoints in `apps/portal/backend/app.py`.
- **Infrastructure**: Integration with observability data (T-011).

## ✅ Acceptance Criteria
- [ ] Create a dedicated "Platform Admin" route in the Portal (restricted to `admin` role).
- [ ] Implement a dashboard showing the status of all registered app manifests.
- [ ] Display real-time health check results for backend services.
- [ ] Integrate a summary view of recent audit logs (T-016).
- [ ] Visualize basic platform metrics (e.g., active tenants, request rates).

## 🛠 Technical Constraints & References
- **Security**: Strict RBAC is required; only users with the `admin` role should see this dashboard.
- **Observability**: Should consume data from the Centralized Observability system (T-011).
- **Latency**: The dashboard should be performant and not negatively impact the main Portal experience.

## 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [B-006 - Platform Hardening and Developer Experience](B-006%20-%20Platform%20Hardening%20and%20Developer%20Experience.md)
- [T-011 - Centralized Observability and Distributed Tracing](T-011%20-%20Centralized%20Observability%20and%20Distributed%20Tracing.md)
- [T-016 - Centralized Audit Logging Specification](T-016%20-%20Centralized%20Audit%20Logging%20Specification.md)
