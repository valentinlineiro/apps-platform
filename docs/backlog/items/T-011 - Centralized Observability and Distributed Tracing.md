---
id: T-011
title: Centralized Observability and Distributed Tracing
audience: [human, ai]
last_updated: 2026-04-22
tags: [observability, opentelemetry, infrastructure, monitoring]
source_of_truth: true
related: [DOC-TMP-AI-001, T-008]
---

# Centralized Observability and Distributed Tracing

## Purpose
Enable end-to-end visibility of requests as they flow through the platform by implementing distributed tracing and centralized logging using OpenTelemetry.

## Context & Motivation
As the platform moves towards a micro-frontend and micro-services architecture, a single user action can trigger multiple network calls across different services (Portal UI -> Portal Backend -> App Backend). Currently, debugging these interactions is difficult because logs are siloed and there is no way to correlate requests. Distributed tracing will provide a unified view of request lifecycles, making it easier to identify performance bottlenecks and the root causes of failures.

## Scope & Impact
- **Platform SDK**: Implement OpenTelemetry instrumentations for Flask and common database drivers.
- **UI Library**: Implement OpenTelemetry instrumentation for frontend fetch/XHR calls.
- **Infrastructure**: Configure a centralized collector (e.g., Jaeger or Tempo) and a logging aggregator (e.g., Loki).
- **Impact**: Improved MTTR (Mean Time To Resolution) for production incidents and better performance insights.

## Acceptance Criteria
- [ ] **SDK Instrumentation**: Add an `observability.tracing` module to the SDK that automatically wraps Flask requests with a Trace ID.
- [ ] **Frontend Propagation**: Update the UI library to inject `traceparent` headers into outgoing API calls.
- [ ] **Log Correlation**: Update the SDK logger to include the current `trace_id` in every log line.
- [ ] **Infrastructure Setup**: Add an OpenTelemetry Collector and a tracing backend (e.g., Jaeger) to the `docker-compose.yml`.
- [ ] **Validation**: Verify that a request from the Portal UI can be traced through the Backend and into the `aneca-advisor` service in a single UI view.

## Technical Constraints & References
- **Performance**: Instrumentation must have negligible overhead on request latency.
- **Standards**: Must strictly follow the OpenTelemetry specification.
- **Privacy**: Ensure sensitive data (e.g., passwords, PII) is not captured in traces or logs.

## Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [Observability Guide](../../concepts/infrastructure.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## Change log
- **2026-04-22**: Initial task creation.
