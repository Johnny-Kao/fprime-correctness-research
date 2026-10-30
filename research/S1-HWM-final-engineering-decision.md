# S1 exact HWM — engineering decision (2026-10-30)

Status: **NO-GO for current scan implementation. Do not open a correctness PR from this branch.**

## Required contract

`getMessageHighWaterMark()` promises the highest simultaneous number of queued messages across all configured priorities. The existing queue primitive is bounded, lock-free MPMC; ISR-safe behavior is platform dependent. No new unbounded wait, mutex, dynamic allocation during operations, or incompatible C++ features may be introduced.

## Structural impossibility of the current patch

The implementation samples `AtomicQueue::getSize()` *after* `enqueue()` succeeds. A consumer can dequeue before that sample and erase the true peak. Even with sequentially consistent atomic counter updates after `enqueue()`, the same scheduling counterexample persists. Scanning multiple priorities can also combine samples from mutually exclusive moments and inflate the result.

In `AtomicQueue::enqueueInternal()`, the producer claims a slot by advancing `m_enqueuePos` and later publishes it with `slot->sequence.store(pos + 1, release)`. In `dequeue()`, the consumer advances `m_dequeuePos`, copies data, then publishes slot availability. Neither transition is atomic with a separate global HWM counter. Moving the counter update immediately before or after either transition does not solve delayed/preempted update order. This is a protocol-level change, not a local arithmetic fix.

## Decision choices for upstream

1. **Exact HWM with a new shared linearization protocol.** Design and review a single coherent admission/removal accounting mechanism integrated with the queue's claim/publish transitions, including producer failure/rollback and incomplete operations. Explicitly prove lock-free/bounded progress and ISR behavior. More invasive than the current patch.
2. **Well-defined conservative capacity statistic.** Change the documented API contract to a bound/estimate and report a monotonically conservative value, not the exact historical occupancy. Requires upstream agreement because the existing getter promises exact peak.
3. **Exact metrics with serialization.** Serialize queue mutations and HWM state transitions. Straightforward proof, but incompatible with the existing lock-free/ISR constraints without explicit upstream architectural approval.

Do **not** present a post-send `fetch_add` / post-receive `fetch_sub` as a fix; an interrupted sender or receiver can reorder accounting relative to real occupancy. TSan success does not prove this invariant.

## Testing decision

Existing 7/7 Framework CI passed for the experimental scan. It establishes build, regression, and race-detector results for covered schedules, **not** linearizable exact aggregate HWM. Running that CI again without a new algorithm has no value.

**Release gate:** A candidate must first state and defend its linearization point for both successful enqueue and dequeue, show safety under arbitrary preemption, and preserve queue progress semantics. Only then run a single full upstream-equivalent CI matrix plus bounded adversarial schedule and performance checks.

The scan patch and tests remain on this research branch for review and reproduction; no upstream PR is created.
