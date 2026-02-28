# Vibe Coding Development Plan

## Delivery Style
- Short build loops with visible artifacts every cycle.
- Keep architecture modular, but optimize for shipping an executable MVP quickly.
- Validate each slice with tests or runnable smoke checks before moving on.

## Phase 0: Project Bootstrap
Goal: create runnable Python project skeleton.
- Deliverables:
  - `pyproject.toml`, `README.md`, `.env.example`
  - package layout under `src/`
  - test layout under `tests/`
- Exit criteria:
  - Project imports correctly.
  - Unit test runner executes.

## Phase 1: Config and Domain Model
Goal: establish typed config and event data contracts.
- Deliverables:
  - environment-driven config loader
  - dataclasses for candidate events and alert payload
  - validation for required runtime fields
- Exit criteria:
  - Missing critical config fails fast with clear errors.

## Phase 2: External Client Adapters
Goal: isolate API dependencies behind small, testable interfaces.
- Deliverables:
  - RPC adapter with failover
  - pricing adapter with caching
  - explorer adapter for wallet tx count
  - Telegram notifier adapter
- Exit criteria:
  - Adapters handle transient errors via retries/backoff.

## Phase 3: Detection and Rule Engine
Goal: convert raw chain data into actionable detections.
- Deliverables:
  - block polling loop
  - native and ERC-20 transfer extraction
  - USD conversion + threshold evaluation
  - new-wallet rule evaluation
- Exit criteria:
  - Deterministic decision path from candidate event to alert decision.

## Phase 4: Orchestration and Alerting
Goal: run end-to-end monitoring continuously.
- Deliverables:
  - monitor service orchestrator
  - dedup keys and timestamp enrichment
  - alert formatting and dispatch
- Exit criteria:
  - `python -m polymarkt_monitoring.main` can run in `--once` and loop mode.

## Phase 5: Testing and Hardening
Goal: lock in core behavior and basic reliability.
- Deliverables:
  - unit tests for evaluator boundaries
  - config parsing tests
  - smoke test instructions
- Exit criteria:
  - Tests pass locally.
  - README has setup, run, and troubleshooting guidance.

## Implementation Sequence for This Iteration
1. Complete Phases 0-2.
2. Implement Phase 3 and 4 MVP paths for native + ERC-20 transfers.
3. Add Phase 5 unit tests and docs.
4. Run tests and finalize.

## Definition of Done
- Strategy/design doc exists and matches implementation direction.
- Vibe plan doc exists and is actionable.
- MVP monitor is implemented and runnable.
- Core tests pass.
- Documentation is sufficient for another developer to run and extend the system.
