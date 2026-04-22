---
id: T-015
title: Frontend Performance and Asset Prefetching
audience: [human, ai]
last_updated: 2026-04-22
tags: [performance, frontend, web-performance, micro-frontends]
source_of_truth: true
related: [DOC-TMP-AI-001, T-010]
---

# Frontend Performance and Asset Prefetching

## Purpose
Optimize the platform's initial load and navigation speed by implementing intelligent asset prefetching and performance optimizations for micro-frontend applications.

## Context & Motivation
As the platform grows and more micro-frontends (MFEs) are added, the time required to fetch and mount different applications may increase. Currently, an MFE is only fetched when the user navigates to it. This can lead to a "loading gap" and a sluggish feel. Intelligent prefetching—where the Portal Shell background-loads assets based on user intent (e.g., hovering over a card)—can make navigation feel instantaneous.

## Scope & Impact
- **Portal Shell**: Implement a prefetching engine in the Angular shell.
- **UI Library**: Add performance monitoring utilities (Core Web Vitals) for MFEs.
- **Impact**: Significant reduction in "Time to Interactive" (TTI) for all platform applications and improved overall perceived performance.

## Acceptance Criteria
- [ ] **Prefetching Engine**: Implement a background loader in the Portal that fetches MFE `scriptUrl` assets when a user hovers over an app card.
- [ ] **Asset Caching**: Configure aggressive caching strategies in Nginx for static assets.
- [ ] **Performance Monitoring**: Integrate with the observability stack (T-011) to report Core Web Vitals (LCP, FID, CLS) from MFEs.
- [ ] **Critical Path Optimization**: Audit the Portal Shell and reduce its initial bundle size by lazy-loading non-critical modules.
- [ ] **Benchmark**: Document the before-and-after performance improvements for app transitions.

## Technical Constraints & References
- **Network Awareness**: The prefetching engine must respect the `navigator.connection.saveData` preference and avoid prefetching on slow connections.
- **Memory Management**: Ensure that prefetching doesn't lead to excessive memory consumption in the browser.
- **Standards**: Use standard `<link rel="prefetch">` or service worker strategies where possible.

## Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Google Web Vitals](https://web.dev/vitals/)
- [Angular Lazy Loading](https://angular.io/guide/lazy-loading-ngmodules)
- [Clean Architecture (T-010)](T-010%20-%20Implement%20Frontend%20Clean%20Architecture%20in%20UI%20Library.md)

## Change log
- **2026-04-22**: Initial task creation.
