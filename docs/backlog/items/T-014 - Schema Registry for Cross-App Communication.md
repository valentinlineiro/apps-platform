---
id: T-014
title: Schema Registry for Cross-App Communication
audience: [human, ai]
last_updated: 2026-04-22
tags: [architecture, events, event-driven, communication]
source_of_truth: true
related: [DOC-TMP-AI-001, T-009]
---

# Schema Registry for Cross-App Communication

## Purpose
Enable loose coupling between applications by implementing a shared Event Bus and Schema Registry for asynchronous communication.

## Context & Motivation
Currently, when one app needs data or a reaction from another, it typically relies on direct REST calls or shared database knowledge. This tight coupling makes the system fragile and difficult to evolve. By adopting an event-driven architecture, apps can publish "Business Events" (e.g., `ExamCorrected`, `UserRegistered`) that other services can consume without knowing who the publisher is. A schema registry ensures that the event structure is strictly versioned and predictable.

## Scope & Impact
- **Platform SDK**: Implement a message bus abstraction (using Redis or RabbitMQ) and a schema validation layer.
- **Infrastructure**: Add a message broker to the `docker-compose.yml`.
- **Applications**: Transition inter-app interactions to event-based where appropriate.
- **Impact**: Improved system scalability, resilience, and decoupling of domain logic.

## Acceptance Criteria
- [ ] **Message Bus**: Add a standard `EventPublisher` and `EventSubscriber` to the SDK.
- [ ] **Schema Validation**: Implement automatic event payload validation against a centralized registry (e.g., using JSON Schema or Avro).
- [ ] **Broker Setup**: Add a Redis or RabbitMQ container to the infrastructure for local development.
- [ ] **Dead Letter Queues**: Implement basic error handling and DLQ support in the SDK.
- [ ] **Pilot**: Implement an event in `exam-corrector` that notifies the Portal whenever a new batch is processed.

## Technical Constraints & References
- **At-Least-Once Delivery**: The system must handle duplicate events gracefully (idempotency).
- **Versioning**: All events must include a version (e.g., `v1`, `v2`) to prevent breaking changes in consumers.
- **Monitoring**: Integrate with the observability stack (T-011) to trace event flows across services.

## Status
- **Current Status**: `Planned`
- **Priority**: `Low`
- **Assignee**: [AI Agent]

## References
- [Event-Driven Architecture Guide](https://martinfowler.com/articles/201701-event-driven.html)
- [Centralized Observability (T-011)](T-011%20-%20Centralized%20Observability%20and%20Distributed%20Tracing.md)

## Change log
- **2026-04-22**: Downgraded to Low — premature until T-008 (SDK) and T-011 (observability) are complete.
- **2026-04-22**: Initial task creation.
