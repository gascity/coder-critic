# Verified two-coder run

On September 19, 2026, two coding agents implemented separate ready tasks, then
the first agent integrated their modules after both prerequisites closed. No
manual tool approvals, nudges, reassignments, runtime restarts or code edits were
made after launch. Initial account/folder trust was completed beforehand.

The [original run result](run-1/evidence/run.json) records workflow `p4-ymc`,
successful verification, supervisor exit code 0 and no cleanup errors. The
[graph proof](run-1/evidence/verification.json) records different coding workers,
overlapping tasks, correct dependency order, one integration attempt and 24
passing tests. Tests, scripts, brief and configuration stayed unchanged during
the run; their initial hashes are retained.

## What actually ran

All times below are UTC on September 19. The timestamps and full worker identities
come from the [final Beads records](run-1/evidence/beads.json).

| Task | Worker | Started | Closed |
| --- | --- | --- | --- |
| Parse CSV (`p4-bub`) | coder | 21:24:57 | 21:26:47 |
| Aggregate amounts (`p4-gij`) | coder-b | 21:24:54 | 21:27:25 |
| Integrate (`p4-a15`) | coder | 21:29:24 | 21:30:20 |

The implementation intervals overlap by 1 minute 50 seconds. Integration starts
after both end. These timings demonstrate concurrency and dependency order, not
a speedup benchmark. The full run took about 17 minutes 24 seconds including
startup, verification and cleanup on a shared macOS 26.6.2 arm64 machine.

The toolchain was GC 1.4.1, Beads 1.2.2, Dolt 2.3.1, Claude Code 2.1.278,
tmux 3.7c and Python 3.14.7. Exact CLI version output is in the run result.

## Inspect or replay

- [Generated utility](run-1/summary.py), [parser](run-1/records.py), [aggregation](run-1/totals.py).
- [Integration report](run-1/reports/integrate.md) and [independent controller test output](run-1/reports/controller-tests.json).
- [Compact state transitions](run-1/evidence/transitions.json), including ready-work IDs.
- [Independent database endpoint check](run-1/evidence/database-check.json).

From the repository root:

```sh
python3 scripts/verify_parallel.py verified-runs/run-1 verified-runs/run-1/evidence/beads.json
(cd verified-runs/run-1 && python3 -m unittest discover -s tests_parts -v && python3 -m unittest discover -s tests -v)
python3 -m unittest discover -s tests_runtime -v
```

## Verification note

GC removed its live database-state file during successful shutdown. A final
verification-only fix made the checker also read retained provider state instead
of accepting an empty endpoint list. The hardened check observed port 36191
closed for 15 seconds and made **zero** additional stop attempts; the export
includes another independent read-only port check. The original run record is
unchanged, and regression tests cover both retained state and missing endpoints.

Failed and incomplete attempts are not included here. The earlier five-role
experiment remains separately documented under `observed-run/`.
