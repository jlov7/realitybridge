# RealityBridge next-increment results

This local, AI-assisted increment challenges the six-operation Gitea observation contract and runs three bounded follow-up studies. The protocol was frozen before the new reference outcomes (SHA-256 `df343372c01d632ddff14e58b6bfc237fc2e74779562d96132f1c5823b758a05`). Each executable study has a pre-outcome JSON inventory, source hashes, a committed runtime ancestor, and a raw receipt in `artifacts/next-increment-2026-09-23/`. `experiments/replay_next_increment.py` verifies those hashes and recomputes saved-data summaries from a history-free source export. It does not rerun Docker, the macOS worker sandbox, or an outside review. The 2026-09-22 measured candidate and 2026-09-23 ordinary study remain separate and unchanged.

## A. Duplicate label rows

The original oracle treated two same-name/same-color registry rows as interchangeable. A planted raw pair showed that an issue attached to the first row and an issue attached to the second row had the same old projection. The live pinned Gitea 1.24.7 probe showed why row identity can matter: `add_label(name)` attached both identical rows, and the adapter's `remove_label(name)` removed the first row, leaving the second attached. This is a six-operation, name-resolving adapter observation. It is not a newly measured defect in the repaired simulator.

The current simulator now stores row memberships, adds every matching row, and removes the first matching row. Current paired traces map unique seed rows by `(name, color)` and later rows by corresponding `create_label` responses. Generated IDs are never compared directly. If a duplicate membership lacks pairing evidence, the state comparator returns `undetermined`. Tests challenge swapped membership, generated-ID drift, registry order, ID reuse, and a membership ID that points at a different registry row. The historical measured simulator and oracle source were not changed. The first live attempt ended at setup with zero requests; its receipt is retained. The amended attempt completed A01 and A02 and stopped during A03 at the frozen 80-request cap. A03 is censored. Both completed traces and the partial third trace are retained; no completion is inferred for A03.

## B. Outside oracle review packet

The reviewer capsule contains 28 randomized, opaque case files with raw reference and simulator responses/errors and separately observed post-action state. It also contains the **historical** observation contract, a captured six-operation schema excerpt from the pinned 1.24.7 `/swagger.v1.json`, a classification form, and a reviewer protocol. The comparator verdicts and source-case mapping sit in a separate private answer key outside the capsule. The generator and packet receipts record hashes; the replay checks that case JSON has no verdict fields. The initial packet and first amendment remain retained outside this source export. The final capsule is the A2 packet.

The historical contract and the later stricter paired-row contract must be adjudicated separately. A disagreement caused solely by applying the later rule is not a mistake in a historical verdict. **No outside human classification, discrepancy adjudication, or independent replication has occurred.** The discrepancy log is blank and ready for an authorized reviewer.

## C. Equal-request discovery feasibility

Two AI-authored, predeclared case procedures each challenged three planted defect families. The ordinary arm systematically covered normal issue/label actions, duplicate rows, and repeated actions; the RealityBridge arm prioritized boundary sequences. Both methods received full raw response and state traces within an arm. All 12 trials per arm completed. Both comparators found all three planted families in each arm. The ordinary arm used 240 metered reference requests and 2.794 seconds measured machine time; the RealityBridge arm used 264 requests and 3.324 seconds. Shared setup used seven requests. There was no unique RealityBridge discovery. These are planted-fault detections with known provenance, not independent adjudication of unknown defects. Author and oracle-building time was not reliably measured, both procedures were written by AI in the same project, and no matched-human-effort or superiority claim follows. The historical 12-case ordinary comparison and its 229 requests are not added to this prospective count.

The [complete C trial table](../../artifacts/next-increment-2026-09-23/C-ALL-TRIALS.csv) lists all 24 family/case attempts, including agreements.

## D. Decision consequences

Five new synthetic task instances of the existing fixed policy templates were frozen before reference outcomes: two selection tasks and three evaluation tasks, each run with all three policies. P23 is an exposed missing-label/task-shift control on repaired source, not a positive simulator-error detector or a novel discovery. These tasks are AI-authored assumptions about possible use, not observed user demand. All 15 cells completed in 277 metered requests. Simulator and reference selected `minimal`; there was no ranking disagreement or simulator false task pass. Total reference regret was 99 utility points, all task shift on P23; the simulator-induced component was zero. The existing planted-false-pass metric test separately proves the summary code can report a rank reversal and simulator-induced regret when one is present.

The [complete D task/policy table](../../artifacts/next-increment-2026-09-23/D-ALL-CELLS.csv) retains every cell; the raw receipt retains each action and post-state.

## E. Repair rule applicability

Three separately authored defect families had frozen training, nonempty known-regression, and unseen sequences. The existing macOS sandboxed C worker received a training counterexample only and was probed against the tracked unseen-case file; all three runs allowed its staged execution and denied that read. It selects among prewritten color transforms. It does not synthesize a new code patch.

| Family | Training before | Known regression before | Unseen before | Worker result | After |
| --- | --- | --- | --- | --- | --- |
| Color hash leak | diverge | agree | diverge | `strip_leading_hash` | train agree; regression agree; unseen agree |
| Duplicate row overwrite | diverge | agree | diverge | no supported rule | no after-run repair claim |
| Unknown-label add error | diverge | agree | diverge | no supported rule | no after-run repair claim |

The study used 205 metered requests and 11.673 seconds measured machine time. Its one positive result is applicability of an authored color rule to another frozen color case. The two unsupported families are expected limits of that worker, not evidence about a general autonomous repair system. No worker was expanded after seeing these outcomes.

## F. Second pinned Gitea version

The second reference was the official `gitea/gitea:1.24.6-rootless` Linux ARM64 image pinned at `sha256:fe643e27326a7fae86dedb544d9392ba662adc3083763a21bd7acc35796449fd`. Its image metadata and live `/api/v1/version` identified 1.24.6. All six scoped path/method entries were present in the live Swagger before the case run and again after reset; the child runner also checked that reset kept the second pinned container image. The twelve previously exposed N cases all agreed against the current simulator in 233 metered requests. A reference-only comparison with the retained 1.24.7 N traces found no difference in normalized action responses or declared state on these twelve cases. Exact timestamps, generated IDs, and unrelated API fields were outside that comparison. This is bounded transfer evidence on an exposed set, not a new held-out result or general version compatibility guarantee.

The [case-by-case compatibility table](../../artifacts/next-increment-2026-09-23/F-COMPATIBILITY.csv) attributes all twelve cells. There was no observed version delta or current simulator divergence to attribute in this set.

OpenCode and Codex assisted design, implementation, tests, and this account. The cases, mutation families, reviewer packet, and interpretation have not had independent human validation. Local source checks and saved-data replay establish that the reported computations match the retained receipts; they do not establish that the observation contract captures every relevant behavior, that a new user would benefit, or that publication is approved.
