---
id: DOC-AI-GL-001
title: Platform Glossary
audience: [human, ai]
last_updated: 2026-04-17
tags: [glossary, terminology, definitions]
source_of_truth: true
related: [DOC-CON-001]
---

# Platform Glossary

## Purpose
Define domain-specific terminology used throughout the platform to ensure consistent communication between humans and AI agents.

## When to use
Consult this glossary when encountering unfamiliar terms in the codebase or documentation.

## Content

### Technical Terms
- **Heartbeat**: A periodic POST request sent by app backends to the portal to maintain their "Active" status in the registry.
- **Registry**: The central database/service in the Portal that tracks active micro-frontend manifests.
- **Portal**: The shell application (Angular) and core API (Flask) that orchestrates the platform.
- **Micro-frontend (MFE)**: An independent application bundled as an Angular Element (Web Component) and loaded dynamically by the Portal.
- **Auth-Gating**: The process of using Nginx `auth_request` to verify a user's session with the Portal before proxying requests to an app backend.
- **Tenant**: A logically isolated workspace or organization within the platform.

## References
- [System Architecture](../concepts/architecture.md)

## Change log
- **2026-04-17**: Initial version of the Platform Glossary.
