---
id: T-019
title: Secrets Management Strategy
audience: [human, ai]
last_updated: 2026-04-22
tags: [security, secrets, vault, devops, technical]
source_of_truth: true
related: [DOC-TMP-AI-001, T-012]
---

# Secrets Management Strategy

## Purpose
Implement a professional secrets management strategy that removes sensitive credentials from environment files and code, ensuring secure rotation and access control.

## Context & Motivation
We are currently using `.env` files and environment variables for database passwords and Keycloak secrets. As the number of services scales, this becomes a major security risk and a maintenance bottleneck (e.g., rotating a single password across 10 services). Adopting a secrets manager (like **HashiCorp Vault** or AWS Secrets Manager) will allow the SDK to fetch secrets securely at runtime.

## Scope & Impact
- **Platform SDK**: Add a `security.secrets` module to fetch values from a secrets manager instead of environment variables.
- **Infrastructure**: Add a secrets manager service (e.g., Vault) to the stack.
- **Impact**: Significant improvement in security posture, automated secret rotation, and centralized credential management.

## Acceptance Criteria
- [ ] **Vault Setup**: Add a Vault container to the local `docker-compose.yml` for testing.
- [ ] **SDK Integration**: Update the SDK to support fetching configuration values from the secrets manager with local environment fallbacks for dev.
- [ ] **Migration Plan**: Document the process for moving all existing `.env` secrets into the central manager.
- [ ] **Auth Strategy**: Implement a secure way for the applications themselves to authenticate with the secrets manager (e.g., AppRole or AWS IAM).
- [ ] **Rotation Pilot**: Successfully rotate the `PORTAL_SESSION_SECRET` without manual intervention.

## Technical Constraints & References
- **Resilience**: The SDK must handle the secrets manager being temporarily unavailable (e.g., using local caching).
- **Least Privilege**: Each service must only have access to the specific secrets it needs.
- **Auditing**: All secret accesses must be logged in the central audit stream (T-016).

## Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [Audit Logging (T-016)](T-016%20-%20Centralized%20Audit%20Logging%20Specification.md)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/)

## Change log
- **2026-04-22**: Initial task creation.
