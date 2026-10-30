# S1: aggregate HWM concurrency correctness gate

## Observed implementation

Branch: `research/hwm-regression` (experimental scan-based candidate).
Every successful `PriorityMemQueue::send` scans all configured `AtomicQueue::getSize()` and atomically maximizes slot 0 of the HWM array.

## Why existing CI success is insufficient

`AtomicQueue::getSize()` reads `m_enqueuePos` and `m_dequeuePos` separately, both relaxed, then clamps the difference to the configured capacity. These are not a linearizable cross-queue snapshot.

**Undercount counterexample (one priority suffices).**

1. Initially empty. Producer P publishes one message successfully in `AtomicQueue::enqueueInternal`.
2. P is preempted *before* the scan in `PriorityMemQueue::send`.
3. Consumer C successfully removes the message in `PriorityMemQueue::receive`.
4. P resumes, scans zero, and records HWM zero.

Actual occupancy reached one. Recorded HWM remains zero. All atomic accesses can be data-race-free, so TSan does not detect this.

**Overcount counterexample (two priorities).**

1. Priority A contains one message, B is empty.
2. P samples A as one during an aggregate scan.
3. C removes the A message.
4. Another P adds one B message.
5. The first producer samples B as one and records aggregate two.

At no instant was the total occupancy two. (The scan might be reordered or delayed; mutual exclusion between separate queue snapshots is absent.)

## Requirements for an acceptable repair

- Explicitly define occupancy linearization relative to `AtomicQueue` slot reservation/publish and dequeue claim/release. A simple post-operation atomic increment/decrement is also subject to delayed-update reorder.
- HWM must equal the peak of a coherent aggregate occupancy history; must not exceed total configured capacity.
- Preserve ISR safety, bounded progress, no runtime allocation, C++14 and existing blocking semantics.
- Validate Linux/macOS framework unit suites, TSan, and a controlled producer-consumer schedule, plus benchmark impact.
- Do not represent experimental scan-based approach as ready for upstream.

## Decision

Current candidate **NOT READY** for a flight-software correctness PR. Existing regression coverage proves sequential aggregation and producer-only quiescent final occupancy, not exact concurrent HWM. Architectural decision required: either define/implement a coherent counting linearization inside the queue primitive or explicitly relax the HWM API contract to an estimate (not recommended without upstream agreement).
