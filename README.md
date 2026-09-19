# Durable work graphs with Beads and Gas City

This is the public companion to the draft article **Graph engineering:
Programming the work, not just the worker**. It uses a coder–critic workflow to
build a small CSV expense-summary utility. The programming task is deliberately
small; the point is to inspect how dependencies, work state and evidence let
separate agents coordinate.

You can inspect the [recorded run](observed-run/README.md) and verify it with
Python alone. Running a new workflow additionally requires the tools and provider
account described below. The recorded run was supervised, not unattended.

## From the ideas to the example

In his [2025 LLM Year in Review](https://karpathy.bearblog.dev/year-in-review-2025/),
Andrej Karpathy describes applications connecting LLM calls into directed acyclic
graphs. Andrew Ng's [API-discovery course introduction, 00:50–01:57](https://learn.deeplearning.ai/courses/knowledge-graphs-for-ai-agent-api-discovery/lesson/i1ahou/introduction)
explains why agents need process prerequisites as well as relevant APIs: a
purchase order may require a request and IT approval first.

Knowing a prerequisite exists is different from recording whether a particular
task has satisfied it. This example makes that second part concrete. It adapts
Andrew's [coding, reflection and separate coder/critic roles, 4:29–6:21](https://www.youtube.com/watch?v=sal78ACtGTc&t=269s).
The CSV task, parallel review/test branches, separate reviser and verifier, fixed
test suite and Gas City configuration are ours. Neither speaker endorses this
example or these projects.

## What the graph represents

Tasks are nodes; dependencies are edges. A flat list of implementation, review,
testing and revision doesn't specify which tasks can proceed independently or
when their results must come together. These relationships do:

```text
                         ┌─→ review code ─┐
implement first version ─┤                ├─→ revise ─→ verify
                         └─→ run tests ───┘
```

Review and testing both wait for implementation, but neither waits for the other.
Revision waits for both reports. Gas City checks each revision attempt against
the fixed tests, permitting at most two attempts before failure. Final
verification follows a passing revision. The diagram shows worker tasks; the
[full formula](formulas/coder-critic.toml) also specifies that executable check.

Beads persists task identity, state and dependencies outside any worker's context.
Gas City applies the formula against that work graph and dispatches eligible
tasks. The formula describes the reusable workflow; the graph records a particular
run. Reports and source files live in the demo directory, with their locations
given in task descriptions. Their hashes identify which code was examined.

The graph records when work could advance; the reports establish what was reviewed
and tested. Completing a failed-test report still completes the reporting task:
the failure is input to revision, not a reason to prevent revision from starting.
Passing tests is required at the revision check and final verification.

## Inspect the recorded run first

From a clone of this repository:

```sh
python3 scripts/verify_evidence.py observed-run observed-run/beads.json
python3 scripts/verify_review.py observed-run
(cd observed-run && python3 -m unittest discover -s tests -v)
```

These commands inspect saved work state, check artifact hashes and ordering,
replay the critic's CSV finding, and run the twelve tests. They do not launch
agents or consume provider usage. The record shows overlapping review/testing
and revision after both completed. All twelve tests passed on the initial and
final implementations; review found an additional error-handling case.

The [run record](observed-run/README.md) includes the results and interventions.
It took about 52 minutes, including setup and approval waits. Work and artifacts
remained when worker terminals disappeared, but workers needed to be recreated.
This is evidence of inspectable coordination, not speed or unattended recovery.

## Requirements

The tested implementation and evidence are preserved at
[commit 16c6221](https://github.com/gascity/coder-critic/tree/16c62210d8277b0af6f163aefe761d015feed7e2).
The README may evolve to explain the article; the recorded code, tests, formula
and reports preserve the supervised demonstration from September 15, 2026.
This is not a maintained compatibility recipe for future tool releases. Later tool
versions need their own compatibility checks; the recorded run's versions and
reports remain historical evidence. Expect supervised setup and operation,
not unattended reliability.

The demonstration targets installed Gas City 1.4.1 and Beads 1.2.2, plus Dolt,
tmux, Python 3, and an authenticated Claude Code CLI. Agent calls use your
existing provider account and may consume paid usage. No GPU or Python packages
are required. Start with the official [Gas City installation guide](https://docs.gascity.com/getting-started/installation)
and [Beads repository](https://github.com/gastownhall/beads) if these tools are
not installed. The pack commits are pinned in pack.toml and packs.lock.

## Prepare and run

Clone this repository and select the tested snapshot, then choose a new absolute
run directory. The checkout pins the example, not your installed tool versions:

```sh
git clone https://github.com/gascity/coder-critic.git
cd coder-critic
git checkout --detach 16c62210d8277b0af6f163aefe761d015feed7e2
sh prepare.sh /tmp/coder-critic-demo
export GC_HOME=/tmp/coder-critic-demo/home
cd /tmp/coder-critic-demo/city
```

Preparation assigns a path-derived city name, isolating its tmux socket as well
as its supervisor home. It refuses to overwrite an existing run directory.

On a fresh folder, run `claude --permission-mode acceptEdits` once, accept trust
for this demo folder, and exit without submitting a task. Claude Code 2.1.269
defaults this dialog to No; Gas City 1.4.1's automatic dialog handler assumes
Yes. The city configuration also maps Gas City's `auto-edit` option explicitly
to Claude's current `acceptEdits` flag. It allows the demo's listed task and
test commands, without enabling permission bypass. Other commands can still
request approval; inspect an agent with `gc session peek` if progress stops.

```sh
gc start --no-auto-restart
gc sling coder coder-critic --formula --json
```

Copy `workflow_id` from that output. Observe the run (the observer only reads):

```sh
python3 -u scripts/observe.py "$PWD" WORKFLOW_ID --output evidence --minutes 20
```

The observer has a deadline; it does not cancel running agents on timeout.
Inspect with `gc status`, `gc session list`, `gc session peek SESSION_ID`, and
`gc bd show WORKFLOW_ID`. After collecting results, stop this demo:

```sh
gc stop
gc supervisor stop
```

Keep GC_HOME set to this demo's isolated home for every command, including
cleanup. Its registry contains only this city. Stop the demo explicitly if
an agent waits for input or the observer times out.

## What to inspect

A new run produces the following files in its isolated city:

- `reports/first-summary.py`: the coder's preserved first implementation.
- `reports/review.md`: the critic's independent findings and code hash.
- `reports/first-tests.json`: fixed tests against the initial code hash.
- `reports/revision.md`: the reviser's decisions and revised code hash.
- `reports/controller-check.json`: the orchestrator's executable check.
- `reports/final-tests.json` and `reports/final.md`: final verification.
- `evidence/beads.json` and `evidence/timeline.jsonl`: work state and observations.

Tests and checking scripts are fixed before agents run. No defect is seeded.
The initial implementation may pass every test. A single run demonstrates
coordination and artifact provenance; it is not a benchmark of model quality.
Every report should distinguish completed review/testing work from code quality.
Memory Beads is not required for this example.

The [recorded run](observed-run/README.md) includes the first and final code,
reports, and work-state evidence. It also records the manual setup and runtime
interventions. This is a supervised demonstration, not an unattended reliability
benchmark or a hardened CSV library.

After the workflow closes, verify ordering and artifact hashes:

```sh
python3 scripts/verify_evidence.py "$PWD" evidence/beads.json
```

## Adapt it to your work

Keep the handoff structure, but change the brief, acceptance tests and formula's
task descriptions together. The verifier's twelve-test expectation and file
hashes intentionally identify this exact demonstration; a different task needs
its own acceptance criteria and evidence check. Preserve `observed-run/` as the
record of this run, rather than editing its reports to match a new experiment.

## Where knowledge fits

The revision report contains input-policy decisions that future workers may
need. Karpathy's [LLM Wiki proposal](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
describes maintaining persistent, linked knowledge rather than losing each
useful synthesis in chat history. That is a knowledge graph, distinct from the
execution dependencies above.

The proposed [Memory Beads](https://github.com/gastownhall/beads/issues/5877)
would let a task reference durable, versioned knowledge without making that
knowledge a prerequisite to complete. For this example, an approved input policy
could reference the work that produced it, and a later parser change could refer
to that policy. This is a possible extension, not implemented here. As checked
September 19, 2026, the [implementation tracker](https://github.com/gastownhall/beads/issues/6535)
is open with all seven phases unchecked. Keep this proposal separate from the
runnable work-graph example.

## License

MIT; see [LICENSE](LICENSE).
