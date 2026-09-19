# Durable task graphs with two coding agents

Two coding agents build a small CSV expense-summary utility. Each takes a
different ready bead and implements a separate module. A third task integrates
their work only after both prerequisites are complete.

```text
implement records.py ─┐
                     ├─→ integrate summary.py ─→ executable check
implement totals.py ──┘
```

Beads stores the tasks, dependencies and completion state. Gas City runs two
coding workers against that graph. There is no permanent tester, critic,
reviser or verifier agent. The first worker also handles integration.

## What this demonstrates

`bd ready` finds open work without active blockers. Readiness is not assignment:
Gas City's `gc hook --claim --json` atomically claims eligible work routed to a
worker. The [formula](formulas/parallel-summary.toml) gives both implementation
tasks separate `coder` and `coder-b` targets, each allowing one active session.
These are two coding agents with separate file ownership, not different roles.
Separate targets avoid the tested release's same-target workflow affinity
binding both tasks to one worker.

After receiving eligible work, each coder explicitly marks that task
`in_progress` before coding. Gas City can reserve a later iteration without
starting it; the explicit status transition records when work actually begins.

The parallel tasks have explicit interfaces and separate output files:

- `records.py` parses and validates CSV structure.
- `totals.py` validates amounts and aggregates decimal totals.
- `summary.py` composes them after both implementation beads close.

The [brief](BRIEF.md) fixes their contracts before launch. Each implementation
has six fixed tests; integration runs those twelve plus the twelve public-API
tests. Gas City's executable check independently tests the integrated artifact,
with at most two integration attempts.

A formula is the reusable recipe. The beads are this run's durable tasks and
state. Reports remain ordinary files referenced by task descriptions.

## Verified result

The [September 19 recorded run](verified-runs/README.md) completed without manual
approvals, task reassignment, runtime restarts or edits after launch. Two coders'
implementation tasks overlapped; integration waited for both and passed on its
first attempt. All 24 tests passed, fixed files stayed unchanged, and the
supervisor exited successfully. No worker sessions or database were left running.

The generated code, reports and machine-readable evidence are included. Replay
the result without starting agents or consuming provider usage:

```sh
python3 scripts/verify_parallel.py verified-runs/run-1 verified-runs/run-1/evidence/beads.json
(cd verified-runs/run-1 && python3 -m unittest discover -s tests_parts -v && python3 -m unittest discover -s tests -v)
```

Or use the generated utility directly:

```sh
cd verified-runs/run-1
python3 -c 'from summary import summarize; print(summarize("category,amount\ncoffee,3.25\ncoffee,2.75\n"))'
```

## Requirements

Use [Gas City 1.4.1](https://github.com/gastownhall/gascity/releases/tag/v1.4.1),
[Beads 1.2.2](https://github.com/gastownhall/beads/releases/tag/v1.2.2),
[Dolt 2.3.1](https://github.com/dolthub/dolt/releases/tag/v2.3.1), tmux, Python 3.11+ and an
authenticated Claude Code CLI. Preparation rejects other GC/Beads/Dolt versions.
The runner preserves resolved binary paths so workers use the same toolchain.
Pack imports are pinned in [pack.toml](pack.toml) and [packs.lock](packs.lock).
Live validation uses Claude Code 2.1.278 with auto permission mode available;
the exact versions are recorded with each run.

This is deliberately versioned, not an instruction to substitute whichever
release is newest. Fresh setup with GC 1.4.2 / Beads 1.3.0 failed during schema
initialization in our compatibility checks. The sample does not migrate existing
databases or offer a migration-bypass workaround.

Agent calls use your provider account and consume its normal usage. Claude Code's
auto permission classifier stays enabled. The demo preauthorizes its workflow
commands, Python execution, and basic file-listing/output commands. Run only a
copy you trust; Python execution is not a security sandbox.

## Prepare and run

From this checkout, select the required binaries on your PATH, then:

```sh
sh prepare.sh /absolute/path/to/new-demo
```

Preparation refuses an existing directory. It creates a separate city, database,
GC_HOME, tmux identity and loopback supervisor API port. It removes inherited
GC/Beads endpoint settings rather than attaching to another city.
Preparation and launch explicitly verify Claude authentication with a 30-second
budget. Preparation replaces GC 1.4.1's shorter five-second readiness probe;
sign-out, invalid output or a timeout still stops the sample before workers start.

It initializes the new Beads schema in embedded mode, then copies that closed
database into Gas City's managed-server data directory. This avoids the pinned
release's time-limited schema preflight. It never repairs or migrates an existing
user database. The supervisor uses its own new registry; the bundled LLM database
maintenance worker is suspended so the demo starts only two coding agents.

Complete the one-time account/folder-trust setup before launching work:

```sh
cd /absolute/path/to/new-demo/city
DISABLE_AUTOUPDATER=1 claude --permission-mode auto
# Confirm trust for this demo folder, then exit Claude without submitting work.
```

Run the workflow from the repository checkout:

```sh
python3 -u scripts/run_parallel.py /absolute/path/to/new-demo --minutes 20
```

The runner checks folder trust, starts its own foreground supervisor, launches
the workflow, and prints task state every observation. It does not install a
launchd service, approve prompts, nudge stuck workers, close tasks on their
behalf or recreate a failed runtime. A timeout or runtime failure fails the run.
It stops its own city and supervisor afterward, including on failure.
Run directories are single-use. Prepare a new directory for another attempt;
the previous run's files and evidence remain available for inspection.

The deadline applies to the workflow; city startup has a separate five-minute
limit. Cleanup allows two minutes for Gas City's shutdown phases, verifies that
no worker sessions remain, then allows two minutes for scoped database cleanup.
That final phase uses GC's ownership/lock-checked stop operation and requires
15 seconds with no database listener, catching a late restart after worker exit.
A nonzero supervisor exit, forced process kill or incomplete cleanup fails the
run. Choose limits before the run, not after it
gets stuck. Ordinary account login and folder trust happen before launch;
approval prompts during coding are failures, not a supervision requirement.

## Read the evidence

Each run writes these files under its isolated city:

- `reports/parse.md`, `aggregate.md`, `integrate.md`: worker decisions/results.
- `reports/parse-tests.json`, `aggregate-tests.json`: module checks.
- `reports/controller-tests.json`: Gas City's independent final check.
- `reports/all-tests.json`: the final replay against the same source hashes.
- `evidence/timeline.jsonl`: read-only API snapshots of bead state, ready work,
  sessions and runtime health; raw bd timestamps are read once after completion.
- `evidence/beads.json`: final work graph.
- `evidence/fixed-files.json`: hashes captured before workers launch.
- `evidence/verification.json`: overlap, different workers, dependency order and hashes.
- `evidence/run.json`: actual outcome, versions, errors and cleanup result.

The verifier rejects sequential implementation, both tasks claimed by one worker,
integration starting too early, failed checks, or source changed since testing:

```sh
python3 scripts/verify_parallel.py /absolute/path/to/new-demo/city \
  /absolute/path/to/new-demo/city/evidence/beads.json
python3 -m unittest discover -s tests_runtime -v
```

The offline tests exercise the verifier and configuration. They are not a
substitute for running real agents. The live run also rejects changes to the fixed
tests, scripts, formula and brief.

## Earlier coder–critic experiment

The repository name reflects the original five-role experiment. Its
[September 15 run](observed-run/README.md) remains intact, including its manual
interventions and runtime failures. It is historical evidence, not a claim that
the five-role setup ran unattended. The verified result above uses the revised
two-coder workflow.

You can replay that original evidence without agents or provider usage:

```sh
python3 scripts/verify_evidence.py observed-run observed-run/beads.json
python3 scripts/verify_review.py observed-run
(cd observed-run && python3 -m unittest discover -s tests -v)
```

## Connection to the article

Karpathy's [2025 review](https://karpathy.bearblog.dev/year-in-review-2025/)
describes applications connecting LLM calls into directed acyclic graphs.
Andrew Ng's [API-discovery introduction](https://learn.deeplearning.ai/courses/knowledge-graphs-for-ai-agent-api-discovery/lesson/i1ahou/introduction)
explains process prerequisites: finding a purchase-order API isn't enough when
a purchase first needs a request and approval. Steve Yegge's
[work-graph discussion](https://yegge.ai/essays/the-shape-of-things-to-come/)
connects task relationships and accumulated findings to Beads.

The concrete split, interfaces, acceptance tests and orchestration here are ours.
The useful property is visible: independent coding work proceeds together;
dependent work waits for its inputs.

**Memory Beads is being built** to add first-class, versioned knowledge and
references alongside task dependencies. It is not required by this sample.
See the [proposal](https://github.com/gastownhall/beads/issues/5877) and
[implementation tracker](https://github.com/gastownhall/beads/issues/6535).
For this utility, an input-policy decision could become knowledge referenced by
future parser work, without turning the knowledge itself into a blocking task.

## License

MIT; see [LICENSE](LICENSE).
