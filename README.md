# Andrew Ng's coder–critic pattern, run with Beads and Gas City

Andrew describes coding, reflection, tests, and separate coder/critic roles in
[his original talk, 4:29–6:21](https://www.youtube.com/watch?v=sal78ACtGTc&t=269s).
This example applies that pattern to a small CSV expense-summary utility. The
CSV task, parallel review/test branches, separate reviser and verifier, fixed
test suite, and Gas City configuration are our adaptation.

```text
                         ┌─ critic ─┐
implement first version ─┤          ├─ revise ─ controller check ─ verify
                         └─ tester ─┘
```

Beads holds the work and dependencies. Reports and source files live in the
demo directory and are referenced from bead descriptions/comments. The formula
specifies the steps; Gas City applies it to the graph and dispatches work.
The revision check permits at most two attempts. A failed first-version test
report completes the reporting task; it does not mean the code passed.

## Requirements

This public repository is a frozen article companion, not a maintained recipe
for future tool releases. The recorded code, tests, formula and reports preserve
the supervised demonstration from September 15, 2026. Later tool
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

Clone this repository, then choose a new absolute run directory:

```sh
git clone https://github.com/gascity/coder-critic.git
cd coder-critic
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

You can inspect and verify the recorded result with Python alone, without
installing Gas City or making paid agent calls. From the repository root:

```sh
python3 scripts/verify_evidence.py observed-run observed-run/beads.json
python3 scripts/verify_review.py observed-run
(cd observed-run && python3 -m unittest discover -s tests -v)
```

These commands check the saved evidence and replay the tests, not a new live
agent workflow. A new run produces the following files in its isolated city:

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

## License

MIT; see [LICENSE](LICENSE).
