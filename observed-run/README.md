# Recorded supervised run

This directory preserves an actual run of the companion workflow, not a
hand-authored example of what its agents might produce. The host agent prepared
the task, fixed tests and configuration, supervised command approvals, observed
state, and independently checked the resulting evidence. Chris did not personally
execute these commands.

Run date: September 15, 2026 (America/Los_Angeles; recorded timestamps are UTC
on September 16). Workflow: `ci-2tg`.

## Environment and provenance

- Gas City 1.4.1, Beads 1.2.2 (Homebrew), Dolt 2.3.1, tmux 3.7c, Python 3.14.7.
- Claude Code was 2.1.269 at setup and auto-updated to 2.1.273 during the run.
  Roles used the provider's default model; this was not a model comparison.
- Pack imports pinned to `f895c0ff47d6ee9334ed282a416387eb5b084d24`.
- Formula SHA-256: `f4b57c430ea87d4b0574f5b19b4eb93ca8c7db2e207cdff33a71a6b4a76dd596`.
- Fixed test SHA-256: `6a92781b6bcc709a537a97e7bac900f3806c079b42a0a5e1c20828247e8db0c9`.
- Fixed runner SHA-256: `520537a5e924ccc1227efc112aba11bcf41f4356551deec6a7c4c5884418e870`.

The live city was `/private/tmp/graph-demo.XUuMnB/city`, with its own GC_HOME.
Preserved reports retain their original paths and wording. They are agent
reports, not an assertion that every opinion or ad hoc test claim is correct.
The first source snapshot, final source, machine-generated fixed-test reports
and work-state snapshot provide independently inspectable evidence.

## Outcome

The workflow closed with `gc.outcome = "pass"` at `2026-09-16T01:01:57Z`.
The graph verifier confirmed ordering, overlapping review/testing, preserved
first-version provenance and identical final hashes in the controller and
verifier test records. All twelve fixed tests passed on the initial and final
implementations. Only one revision attempt was used.

| Work                      | Started (UTC) | Closed (UTC) |
| ------------------------- | ------------- | ------------ |
| Implementation            | 00:16:55      | 00:22:04     |
| Review                    | 00:24:37      | 00:34:12     |
| First tests               | 00:24:37      | 00:25:15     |
| Revision attempt 1        | 00:36:05      | 00:52:30     |
| Revision executable check | —             | 00:52:37     |
| Final verification        | 00:53:33      | 01:01:52     |

The run took about 52 minutes from the workflow's recorded start, including
setup interruptions and supervised approval waits. This is not a speed claim.
The host independently replayed the critic's oversized-CSV-field finding:
the original raised `_csv.Error`, while the final raised `ValueError` with an
explanatory message. See `review-replay.json` and `verification.json`.

Final source SHA-256:
`1d32b350eb9ca9e9c54e0530ccb413d6aefed3c56ef1f8490d64fe23306cc78d`.
The revision also restricted the accepted number grammar and magnitude range.
Those are policy choices beyond the brief, not proven requirements; the reports
document them and the remaining dependency on the caller's decimal context.

## Supervision and limits

This was not a clean unattended run. The record includes these interventions:

1. Gas City 1.4.1's Claude launch used an obsolete permission-mode spelling.
   The supplied city configuration explicitly maps its `auto-edit` option to
   Claude's `acceptEdits`, and permits listed task/test commands. Permission
   bypass was not enabled. Other commands required individual inspection and
   approval, including read-only Python probes and artifact comparisons.
2. Claude's fresh-folder trust dialog defaulted to No. The folder was explicitly
   trusted through an interactive launch before continuing.
3. The demo's tmux server disappeared during worker turnover more than once.
   Work and reports remained in the Beads store and filesystem. Workers were
   recreated, and supervision included recreating the demo-only terminal server
   with a temporary neutral keeper session. The root cause was not established;
   this is not evidence of unattended or general crash recovery.
4. The critic proposed very large exponent probes. Those were declined; it was
   instructed to use bounded inputs and report the resource concern from code
   inspection. The reviser was likewise kept to bounded checks. A proposed shell
   heredoc was redirected to inline probes or file-editing tools.
5. An early observer used the wrong success label, `success` rather than the
   runtime's `pass`. The observer was corrected. Observation deadlines do not
   cancel the workflow; observation continued across that deadline.

The prepared reproduction uses a path-derived city name to avoid sharing a
tmux socket with another city named `city`. This isolation improvement was
init/compiler-verified in a second directory, without launching another set of
agents. The observed workflow used the original city name.

The test suite is deliberately small. Passing it does not prove a secure,
production-ready CSV parser. No defect was planted, no benchmark comparison was
performed, and the bounded retry failure path was configured but not forced.
Agent permissions and ordinary work-item closure remain trust boundaries: a
dependency graph alone cannot stop a malicious worker from misreporting work.

## Inspect or recheck the evidence

From the repository root:

```sh
python3 scripts/verify_evidence.py observed-run observed-run/beads.json
python3 scripts/verify_review.py observed-run
```

The verifier checks recorded task ordering, code hashes, controller/final test
results and unchanged fixed tests/runner. It does not rerun the agents. The
separate review replay checks the oversized-field behavior against both source
versions; it was also checked against an unchanged baseline to verify that it
fails when the error-handling change is absent. This additional probe was added
after review and does not replace or enlarge the fixed acceptance suite. The
original polling timeline remains in the authoring workspace; the compact final
work-state snapshot here excludes unrelated sessions and provider state.
