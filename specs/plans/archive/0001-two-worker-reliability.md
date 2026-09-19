# Two-worker reliability

Required: two interchangeable coding agents work on different ready beads
concurrently; integration waits for both; fixed tests pass; no runtime rescue
after launch. Preserve the old run, repeat the workflow checks and validate the
complete cleanup path.

Implemented: parse/aggregate/integrate graph, two coding targets, separate module
ownership, bounded test commands, isolated environment and API port, foreground
supervisor ownership, read-only observation and an evidence verifier.

Observed setup failures:

- GC 1.4.2 / bd 1.3.0 fresh initialization repeatedly failed with incomplete
  schema migrations, including dirty-table rejection. Explicit migration of the
  independently verified empty run1 database did not finish workspace identity.
  Do not migrate any existing user database or embed repeated repairs in the demo.
- Isolated GC_HOME alone did not isolate API port 8372. The run1 launchd service
  was removed and its owned Dolt processes stopped. Files were retained.
- Original run's tmux outage is confirmed, but its cause is not established.
  Both GC releases already set exit-empty off; do not attribute a fix to that.

Test the original released pair (GC 1.4.1 / bd 1.2.2) using a command-local PATH;
leave the user's installed defaults unchanged. Pin the resolved tool paths in
the run manifest so workers use the same versions as preparation.

Further observed failures and corrections:

- One shared `coder` pool bound both ready steps to the first claiming session
  (run5). Use distinct coder/coder-b targets, one session each; both are coders.
- run8 demonstrated overlapping claims by different coders, but aggregation
  stopped at an approval prompt for ls/echo/python3 -V. Aborted as failed, without
  approving the prompt. Preauthorize those specific read-only probes and fail
  explicitly when a worker displays an approval prompt.
- Version pins alone did not fix intermittent schema initialization. Fresh
  bd init --force invokes a five-second issue-count store open; the failures
  leave partial migrations. Initialize embedded hq, then copy that CLOSED, newly
  created database from .beads/embeddeddolt/hq to .beads/dolt/hq before GC init.
  Initializing embedded without transferring the database did not fix it.
  This setup succeeded in run11, run12 and run13. It touches no user database.
- gc start/register installs a platform service even with a running foreground
  supervisor. Seed the new private cities.toml registry before foreground start.
  The run5/run8 test launchd services were explicitly uninstalled afterward.
- The bundled Dolt maintenance agent was an unwanted third LLM; suspend bd.dog.
  Its maintenance orders also ran at startup, pushing run11/run12 beyond the
  120-second startup limit before coding. Skip those seven orders for this short
  fresh-database demo; new runs allow 300 seconds to start, then 20 minutes for
  the workflow. Do not extend an active run's deadline.

- run13 exposed slow GC CLI observation and cleanup commands. Observe via the
  read-only local HTTP API; read raw bd timestamps once after completion because
  the API projection omits them. Terminate the owned foreground supervisor
  directly; it shuts down its own city and sessions. run15 verified clean
  shutdown on failure without the former CLI cleanup timeout.
- run14 hit a Python version-probe approval. run15 passed both module suites but
  stopped at Claude's Unicode-whitespace security prompt during a legitimate
  parser probe, despite the Python allowlist. Both runs failed; neither received
  a manual approval. Use Claude's supported auto permission classifier, not
  bypassPermissions or a growing list of exceptions. Account/folder trust is
  completed before launch. Runtime approval prompts still fail the run.
- The evidence exporter refuses failed runs, cleanup errors, and fixed files
  changed after verification. Keep the unsuccessful attempts out of the success
  record rather than relabeling them as supervised passes.
- run16 completed the workflow and independent 24-test check without intervention,
  then failed the evidence verifier: its reserved integration iteration went
  directly from open to closed, with no started_at. Keep that failed run intact.
  Have workers explicitly mark each eligible claimed task in_progress before
  coding, including already-reserved iterations. Do not weaken the temporal check.
- run17 passed workflow, fixed-file, overlap, dependency-order and 24-test checks,
  then exceeded the runner's 45-second shutdown limit. The runner marked it
  failed and stopped the owned supervisor; all three sessions were confirmed
  gone. GC v1.4.1 source has separate 5-second city grace, up-to-30-second worker
  stops, 25-second forced wait and 30-second provider-stop phases. Budget 120
  seconds for the complete shutdown before future runs. Also reject nonzero
  supervisor exit codes and remaining worker sessions; do not relabel run17.
- run19 preparation failed GC's provider probe despite a subsequent direct
  Claude auth status reporting loggedIn=true. v1.4.1's probe allows five seconds.
  Replace that redundant setup probe with an explicit 30-second authentication
  check at both preparation and launch; reject sign-out, invalid output and
  timeouts before creating workers. No authentication or permission bypass.
- Retired leftover database watchdog/server pairs from failed run12 and run16
  using their independently verified PIDs. Files retained; unrelated databases
  and active run18 untouched.

- run18 passed the complete workflow, all strict evidence checks and zero-exit
  worker/supervisor shutdown. A later process check found its Dolt server had
  restarted six seconds after shutdown. Its provisional export is not a final
  success record. Add an explicit, ownership/lock-checked database-stop phase,
  bounded to 120 seconds and requiring 15 seconds with no listener. Regression
  tests reproduce the late restart and reject foreign paths, failed stops and
  a listener that never goes away. Preserve the original run status unchanged.

Completed: run21 passed the unattended workflow and all 24 tests, strict graph
evidence, fixed-file checks, supervisor exit 0, and worker/database shutdown.
The graph had also completed unattended in run18 and run20 before final database
cleanup was added. New cleanup code stopped their reproduced leftover databases
in separate targeted checks; those old records were not relabeled.

A final verification-only fix reads retained dolt-provider-state.json after GC
removes dolt-state.json. It rejects an unknown endpoint instead of vacuously
passing. On completed run21 it verified port 36191 closed for 15 seconds with
zero stop attempts. Export retains the original run status and adds a read-only
endpoint check. Its README explicitly documents this post-run verifier fix.
39 offline regressions pass; the final generated code and evidence are exported
under verified-runs/run-1 for replay. Completed implementation is ready for the
requested commit and push. The private landing-page draft was left unchanged.
