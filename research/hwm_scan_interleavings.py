#!/usr/bin/env python3
"""Deterministic adversarial schedule checks for the experimental scan-based HWM.

This is an abstract state-machine witness, NOT a native F Prime unit test.
It intentionally models scans / publication / consumption as separately interleavable
steps; a correct implementation must rule these schedules out by construction.
"""

def check_under_count():
    occupancy = [0]
    hwm = 0
    true_peak = 0
    # enqueue publishes; sender is preempted before HWM scan
    occupancy[0] += 1
    true_peak = max(true_peak, sum(occupancy))
    # independent consumer succeeds
    occupancy[0] -= 1
    # sender resumes after the consumed message is no longer visible
    hwm = max(hwm, sum(occupancy))
    assert true_peak == 1 and hwm == 0
    print("EXPECTED COUNTEREXAMPLE: undercount true_peak=1 observed_hwm=0")

def check_over_count():
    occupancy = [1, 0]
    true_peak = 1
    # An earlier send scans priority 0 before a concurrent receive.
    sample_0 = occupancy[0]
    occupancy[0] -= 1
    # The other producer publishes a priority-1 message.
    occupancy[1] += 1
    true_peak = max(true_peak, sum(occupancy))
    sample_1 = occupancy[1]
    reported_hwm = sample_0 + sample_1
    assert true_peak == 1 and reported_hwm == 2
    print("EXPECTED COUNTEREXAMPLE: overcount true_peak=1 observed_hwm=2")

if __name__ == "__main__":
    check_under_count()
    check_over_count()
