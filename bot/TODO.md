# Product Features Backlog

## Features

### 1.No-show prevention flow

- [x] Add `commit_by` deadline field per event.
- [x] Add attendee status: `invited -> interested -> committed -> confirmed`.
- [ ] Add automatic DM reminders before commitment deadline.
- [ ] Add escalation reminders for users with low reliability.
- [ ] Add organizer view for “at-risk” attendees.
- [ ] Add optional auto-drop for non-committed attendees after deadline.
- [ ] Add waitlist queue and automatic fill-in when someone drops.
- [ ] Add no-show scoring signal to reliability model.

### 2.One-tap planning UX

- [x] Replace free-text inputs with inline options where feasible.
- [x] Add quick-select time windows (morning/afternoon/evening/night).
- [x] Add quick-select date presets (today/tomorrow/weekend/next week).
- [x] Add location type presets (home/outdoor/cafe/office/gym).
- [x] Add budget presets (free/low/medium/high).
- [x] Add transport mode presets (walk/public transit/drive/any).
- [x] Add “edit previous choice” buttons in each stage.
- [x] Add mobile-friendly compact keyboards for long option sets.

### 3.Smart group matching

- [ ] Add scoring model combining availability, reliability, and threshold fit.
- [ ] Add travel burden input and scoring (distance/time estimates).
- [ ] Add preference weighting per attendee (time/location/activity).
- [ ] Add ranked recommendations with confidence and rationale.
- [ ] Add “why this suggestion?” explanation panel.
- [ ] Add fairness rule so same users are not always optimized against.
- [ ] Add fallback mode when required data is missing.

### 4.Recurring-event automation

- [ ] Add recurring templates (`weekly`, `biweekly`, `monthly`).
- [ ] Add template cloning from successful past events.
- [ ] Add rule to reuse prior constraints/availability patterns.
- [ ] Add automatic next-event proposal after event completion.
- [ ] Add skip/pause recurrence controls for organizer.
- [ ] Add holiday/conflict-aware recurrence exceptions.
- [ ] Add recurrence analytics (retention, attendance trend).

### 5.Private preference profiles

- [ ] Add private user preference profile (time, activity, budget, location style).
- [ ] Add sensitivity controls: what is private vs shareable aggregate.
- [ ] Add private preference onboarding via DM wizard.
- [ ] Add aggregate-only recommendation outputs for group chats.
- [ ] Add preference confidence decay/refresh logic.
- [ ] Add “prefer not to share” mode for selected attributes.

### 6.Trust + accountability features

- [ ] Add reliability trend chart per user.
- [ ] Add transparent attendance history summary (per event type).
- [ ] Add organizer moderation actions (warn, mute recommendations, block from event).
- [ ] Add explainable reputation updates after each event.
- [ ] Add dispute/review workflow for contested moderation actions.
- [ ] Add anti-bias checks in trust/reputation updates.
- [ ] Add minimum evidence rule before severe trust penalties.

### 7.Post-event engagement loop

- [ ] Auto-post event summary (who joined, completion status, highlights).
- [ ] Add one-tap lightweight feedback in group/DM.
- [ ] Add “schedule next one?” prompt with reusable defaults.
- [ ] Add attendee follow-up suggestions (time/place improvements).
- [ ] Add streaks/badges for reliable participation.
- [ ] Add weekly digest for active groups.
- [ ] Add reactivation nudges for inactive groups.

### 8.Real-world integrations

- [ ] Add Google Calendar integration for create/update/cancel.
- [ ] Add ICS export for non-Google users.
- [ ] Add Maps integration for travel-time and meeting-point suggestions.
- [ ] Add optional ticket/deposit/payment links for commitment.
- [ ] Add payment verification callbacks and state sync.
- [ ] Add external meeting links (Zoom/Meet) generation support.
- [ ] Add integration health checks and fallback behavior.

## Production Hardening Backlog

## 0. Program Setup and Delivery Plan

- [ ] Define production SLOs: availability, command success rate, callback latency, error budget.
- [ ] Define expected scale targets: groups/day, active users/day, peak updates/sec.
- [ ] Create architecture decision records (ADRs) for webhook, queue, DB refactor, and idempotency model.
- [ ] Split roadmap into phases: Foundation, Reliability, Operability, Security, Scale.
- [ ] Assign owners and deadlines for each epic.
- [ ] Add release train cadence and rollback policy.

### 1. Runtime Architecture: Polling -> Webhook + Worker Queue

- [ ] Replace `run_polling()` with webhook receiver endpoint.
- [ ] Add dedicated ingress service for Telegram updates.
- [ ] Validate Telegram signature/token at ingress.
- [ ] Add durable queue between ingress and workers (Redis Streams/RabbitMQ/SQS/Kafka).
- [ ] Define update envelope schema (update_id, chat_id, user_id, payload, received_at).
- [ ] Add dead-letter queue (DLQ) for poison messages.
- [ ] Add retry policy with backoff and max-attempts for failed jobs.
- [ ] Add worker autoscaling policy based on queue depth and processing lag.
- [ ] Add graceful shutdown hooks to avoid in-flight job loss.
- [ ] Add back-pressure behavior for traffic spikes.

### 2. Message Processing Model and Concurrency Safety

- [ ] Enforce per-chat or per-event ordering guarantees in workers.
- [ ] Introduce event-level locking strategy for mutable event operations.
- [ ] Use DB transactions around state-changing command handlers.
- [ ] Add optimistic concurrency control fields (version/updated_at) on mutable entities.
- [ ] Detect and reject stale writes (compare-and-set pattern).
- [ ] Ensure LLM-inferred actions execute through same transaction-safe command layer.
- [ ] Add concurrency tests for conflicting actions (`join/confirm/modify/lock` race cases).

### 3. Data Model Refactor: JSON Attendance -> Normalized Tables

- [ ] Create `event_participants` table with unique `(event_id, telegram_user_id)`.
- [ ] Add participant state column (`joined`, `confirmed`, `cancelled`) with strict enum.
- [ ] Add participant timestamps (`joined_at`, `confirmed_at`, `cancelled_at`).
- [ ] Add participant role column (`organizer`, `invitee`, `observer`) if needed.
- [ ] Add participant source metadata (slash, callback, mention, DM).
- [ ] Migrate existing `attendance_list` JSON into normalized rows.
- [ ] Keep temporary compatibility read path until migration completes.
- [ ] Remove `attendance_list` writes after migration.
- [ ] Remove `attendance_list` field once all code paths are migrated.
- [ ] Add indexes for `event_id`, `telegram_user_id`, and participant state.

### 4. Strict State Machine and Transition Governance

- [ ] Create dedicated event-state transition service (single write path).
- [ ] Define allowed transitions in DB and code (`proposed -> interested -> confirmed -> locked -> completed`).
- [ ] Store transition reason and actor in transition log table.
- [ ] Reject invalid transitions with explicit error codes.
- [ ] Add transition preconditions (e.g., lock requires confirmed attendance).
- [ ] Add post-transition hooks (notifications, reconfirmation reset, analytics).
- [ ] Add integration tests for all allowed and denied transitions.

### 5. Idempotent Command Execution

- [ ] Define idempotency key format for slash commands and callbacks.
- [ ] Persist command execution registry table (`idempotency_key`, status, response hash).
- [ ] Make handlers return same result for duplicate requests.
- [ ] Make side effects (DB writes, notifications) exactly-once or effectively-once.
- [ ] Implement dedup for repeated Telegram updates (`update_id` tracking).
- [ ] Add timeout recovery for stuck idempotency records.
- [ ] Add chaos tests for duplicate delivery scenarios.

### 6. Retry-Safe Callback Handling

- [ ] Add callback action tokens with expiry and replay protection.
- [ ] Validate callback ownership and authorization on every click.
- [ ] Reject stale callbacks with deterministic message.
- [ ] Ensure callbacks are safe when action already completed.
- [ ] Store callback processing state transitions (`pending`, `accepted`, `expired`, `replayed`).
- [ ] Add callback signature format and parser hardening.
- [ ] Add tests for rapid double-click and delayed callback replay.

### 7. Unified Domain Service Layer

- [ ] Extract command business logic into domain services (event, participation, constraints, feedback).
- [ ] Keep Telegram adapters thin (parse input -> call service -> render output).
- [ ] Ensure mention-driven AI actions call the same domain services as slash commands.
- [ ] Standardize domain exceptions and error mapping.
- [ ] Add service-level unit tests independent of Telegram objects.
- [ ] Add command contract tests to guarantee UX compatibility.

### 8. Observability: Structured Logs

- [ ] Adopt structured JSON logging across app.
- [ ] Add correlation IDs (`request_id`, `update_id`, `event_id`, `chat_id`, `user_id`).
- [ ] Redact sensitive fields (tokens, secrets, private note text).
- [ ] Standardize log levels and event names.
- [ ] Add log sampling for high-volume debug events.
- [ ] Centralize logs into searchable backend (ELK/OpenSearch/Loki).
- [ ] Add log retention and archival policy.

### 9. Observability: Metrics

- [ ] Add Prometheus/OpenTelemetry metrics export.
- [ ] Track command success/failure rates by command type.
- [ ] Track callback latency and error rates.
- [ ] Track queue depth, retry counts, DLQ rate, worker lag.
- [ ] Track DB query latency and transaction conflict rates.
- [ ] Track LLM latency, timeout rate, parse-failure rate, fallback rate.
- [ ] Build SLO dashboard and burn-rate alerts.

### 10. Observability: Tracing

- [ ] Add distributed tracing from webhook ingress -> queue -> worker -> DB/LLM.
- [ ] Propagate trace context in queued jobs.
- [ ] Annotate spans with event IDs and action types.
- [ ] Add tracing for external API calls (Telegram, LLM).
- [ ] Add trace-based performance profiling for hot paths.

### 11. Alerting and Incident Response

- [ ] Add alert rules for high error rate, queue backlog, DLQ spikes, DB failures, LLM outage.
- [ ] Add paging policy and escalation matrix.
- [ ] Add runbooks for common incidents (DB lock contention, callback storms, queue outage).
- [ ] Add status endpoints and synthetic probes.
- [ ] Add postmortem template and review process.

### 12. RBAC and Operational Authorization

- [ ] Define role matrix: attendee, organizer, group admin, system admin.
- [ ] Enforce organizer-only actions (`modify_event`, lock-sensitive operations).
- [ ] Enforce admin-only operational commands.
- [ ] Add permission checks in service layer, not only handlers.
- [ ] Add permission-denied audit events.
- [ ] Add tests for every protected action and role.

### 13. Rate Limiting and Abuse Controls

- [ ] Add per-user and per-group command rate limits.
- [ ] Add separate limit buckets for expensive actions (LLM, suggestion, bulk notify).
- [ ] Add cooldown windows for repeated conflicting operations.
- [ ] Add anti-spam protections for mention-triggered AI mode.
- [ ] Add global circuit breaker during overload.
- [ ] Add abuse telemetry and temporary throttling policy.

### 14. Audit Trail and Compliance Readiness

- [ ] Expand immutable audit table for all state changes and admin actions.
- [ ] Record old_value/new_value diffs for critical entities.
- [ ] Record actor identity and source channel for each action.
- [ ] Add audit query interface for incident investigations.
- [ ] Add retention policies by data class.
- [ ] Add GDPR/privacy workflows for export/delete requests (if applicable).

### 15. Secret Management and Configuration Safety

- [ ] Remove plaintext secrets from local scripts and docs.
- [ ] Integrate secret manager (Vault/AWS Secrets Manager/GCP Secret Manager).
- [ ] Rotate bot token and DB credentials regularly.
- [ ] Add runtime config validation at startup.
- [ ] Separate env configs for dev/staging/prod.
- [ ] Add config drift detection and alerts.

### 16. CI/CD with Migration Gates

- [ ] Add CI pipeline stages: lint, unit tests, integration tests, security scan, build.
- [ ] Add migration diff checks and rollback verification.
- [ ] Add pre-deploy DB backup/checkpoint step.
- [ ] Add deployment gates requiring successful migrations in staging.
- [ ] Add canary deploy strategy for workers and webhook service.
- [ ] Add auto-rollback on SLO regression.
- [ ] Add release notes generation from merged PR labels.

### 17. Database Reliability and Performance

- [ ] Add connection pool tuning for async workload.
- [ ] Add query plans and index review for high-frequency paths.
- [ ] Add migration lock timeout and long-running transaction safeguards.
- [ ] Add read/write timeout settings and retry strategy.
- [ ] Add backup/restore drills and RPO/RTO targets.
- [ ] Add partition/archival strategy for high-volume logs/audit tables.

### 18. LLM Reliability Controls

- [ ] Add strict JSON schema validation for all LLM outputs.
- [ ] Add safe parser with deterministic fallback action map.
- [ ] Add prompt/version registry for reproducibility.
- [ ] Add model timeout budget and fallback path guarantees.
- [ ] Add content safety and toxicity filters for generated text.
- [ ] Add offline test suite for prompt regressions.
- [ ] Add feature flag to disable mention-AI mode during incidents.

### 19. Notification Reliability

- [ ] Make DM and group notifications retry-safe and deduplicated.
- [ ] Add delivery outcome tracking (`sent`, `failed`, `blocked`, `rate_limited`).
- [ ] Add notification queue and batching policy.
- [ ] Add fallback messaging when DM delivery fails.
- [ ] Add user notification preferences and quiet hours.

### 20. Testing Strategy for Production Confidence

- [ ] Add full unit coverage for state transitions and permission checks.
- [ ] Add integration tests for webhook->queue->worker end-to-end flow.
- [ ] Add race-condition test suite for concurrent participation actions.
- [ ] Add load tests with realistic group traffic patterns.
- [ ] Add failure injection tests (LLM outage, DB latency, queue downtime).
- [ ] Add replay tests for duplicate updates and callback retries.
- [ ] Add migration tests with snapshot fixtures of production-like data.

### 21. Security Hardening

- [ ] Add dependency vulnerability scanning (SCA) in CI.
- [ ] Add static analysis and secret scanning in CI.
- [ ] Add strict input validation and escaping across all user-originated text.
- [ ] Add webhook endpoint hardening (IP allowlist or token path secret).
- [ ] Add principle-of-least-privilege DB user roles.
- [ ] Add encryption at rest and TLS in transit for all services.

### 22. Deployment Topology and Environments

- [ ] Define environment parity strategy (dev/staging/prod).
- [ ] Containerize webhook and worker as separate scalable units.
- [ ] Add infra-as-code definitions for repeatable deployment.
- [ ] Add health checks, readiness checks, and startup checks.
- [ ] Add blue/green or canary routing for safe rollout.
- [ ] Add multi-region or failover strategy if required.

### 23. Data Migration Execution Plan

- [ ] Draft migration scripts from JSON attendance to normalized participant rows.
- [ ] Add dual-write phase while validating parity.
- [ ] Add parity checker job and discrepancy report.
- [ ] Cut reads to normalized tables after parity target reached.
- [ ] Remove legacy fields and compatibility code after freeze window.
- [ ] Document rollback strategy for each migration step.

### 24. Product Safety and UX Compatibility

- [ ] Keep existing slash command UX unchanged during backend hardening.
- [ ] Keep callback labels and behavior stable for users.
- [ ] Add transparent user messages for retry/duplicate/stale callback cases.
- [ ] Add progressive rollout via feature flags to avoid broad regressions.
- [ ] Add opt-in beta groups before global rollout.

### 25. Definition of Done for Production Readiness

- [ ] 99.9% monthly availability target met for 30 consecutive days.
- [ ] No critical race-condition bugs in concurrency test suite.
- [ ] Duplicate updates/callback replays produce zero inconsistent state.
- [ ] Migration to normalized participation model fully complete.
- [ ] Observability dashboards and alerts operational with tested runbooks.
- [ ] Security baseline checks enforced in CI and release gating.
- [ ] Incident response and rollback procedures tested in staging.
