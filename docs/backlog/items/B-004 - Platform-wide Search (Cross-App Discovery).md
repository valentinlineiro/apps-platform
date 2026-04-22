---
id: B-004
title: Platform-wide Search (Cross-App Discovery)
audience: [human, ai]
last_updated: 2026-04-22
tags: [search, discovery, business, feature]
source_of_truth: true
related: [DOC-TMP-AI-001, T-014]
---

# Platform-wide Search (Cross-App Discovery)

## Purpose
Increase user productivity by providing a unified search interface in the Portal Shell that can discover data (students, exams, journals) across all installed applications.

## Context & Motivation
Currently, data is siloed within each application. A user searching for a "Student Name" has to manually go into `attendance-checker` and then `exam-corrector`. A platform-wide search index will allow the Portal to provide a "Google-like" experience where the user finds all relevant records from all apps in one place.

## Scope & Impact
- **Platform Shell**: Add a global search bar in the header.
- **Shared Libs**: Create a "Search Provider" interface in the SDK for apps to index their data.
- **Infrastructure**: Implement a lightweight search engine (e.g., Meilisearch or Elasticsearch).
- **Impact**: Dramatic improvement in user efficiency and better platform integration.

## Acceptance Criteria
- [ ] **Search Engine Setup**: Add Meilisearch or a similar engine to the platform infrastructure.
- [ ] **SDK Interface**: Define a `Searchable` interface in the SDK that apps implement to push data summaries.
- [ ] **Portal Search UI**: Implement a global search result view with "deep links" back to the specific app pages.
- [ ] **Security**: Ensure search results respect the user's RBAC permissions (T-012) - a user should not see search results for data they can't access.
- [ ] **Pilot**: Index data from `aneca-advisor` (journals) and `exam-corrector` (batches) and search them from the portal.

## Technical Constraints & References
- **Relevance**: Results must be ranked correctly and show which app they came from.
- **Latency**: Global search must respond in under 200ms.
- **Consistency**: Use the Event Bus (T-014) to keep the search index synchronized with the primary databases.

## Status
- **Current Status**: `Draft`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Event-Driven Architecture (T-014)](T-014%20-%20Schema%20Registry%20for%20Cross-App%20Communication.md)
- [Meilisearch Documentation](https://www.meilisearch.com/)

## Change log
- **2026-04-22**: Initial task creation.
