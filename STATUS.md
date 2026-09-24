# STATUS

**State, 2026-09-24 local review:** research software preview. The results
below were produced and retained locally. No hosted CI result or independent
replication was observed in that review. Check [Actions](https://github.com/jlov7/realitybridge/actions)
and [Releases](https://github.com/jlov7/realitybridge/releases) for subsequent
hosted runs and published assets; neither changes the scientific claim limit.
The 2026-09-24 comparator correction reports `undetermined` when either
response is transport-uncertain, including one-sided loss. Two older tests
were corrected to construct the observation categories they intended to
check. On macOS at `b3798b8e92c892ae9a67acc2080ae323657d5a8e`, 136
portable tests passed on each of Python 3.11 and 3.13. On local Linux ARM
at `e684df27c56a7e3bda91b04d9e678be6f278629d`, the same 136 tests
passed on both versions. The unchanged runtime also passed the macOS repair
isolation test and three pinned Gitea reference tests during review. These
are local engineering checks. The correction does not alter the frozen study
results or establish a hosted CI result.
The 2026-09-22 finite study is complete and immutable. The current emulator has
later repairs. A new AI-authored ordinary comparator study has a retained
setup-failure attempt and a separately amended completed attempt; its raw
trace disagreements received AI cross-review, with no independent human validation.
This local research record is not evidence of hosted CI or external replication.

| Current statement | Authority and limit |
|---|---|
| Measured baseline: 13 agreements, 3 divergences among 16 evaluation cases; 1,518 total study HTTP requests | [2026-09-22 result](docs/research-completion-2026-09-22/RESULTS.md) and frozen attempt receipt. Exact measured source `19b2b4776b538ca5bf7326118fe6fcdae7f21cd2`. Authored six-operation cases on one pinned Gitea build. |
| Scripted policy: no rank disagreement and zero simulator-induced regret; task shift contributed 99 regret | Same frozen result and policy raw JSON. No model-agent or general policy-benefit claim. |
| Current repaired emulator: 30 exposed cases and three P05 final states agreed in a separate 554-request run | [Post-study requalification](artifacts/research-completion-2026-09-22/post-study-requalification-20260922T183442Z-62290.json). Engineering regression evidence, not new prospective validation. |
| Ordinary comparator challenge: amended attempt completed 12 new case instances, 32 actions, 229/320 requests; both methods marked N06 and N09 divergent; ordinary marked N02 and N05 undetermined while instrument agreed | [Protocol](research/ordinary-baseline-2026-09-23/PROTOCOL.md), [setup amendment](research/ordinary-baseline-2026-09-23/AMENDMENT-1.md), and both retained receipts under `artifacts/ordinary-baseline-2026-09-23/`. First attempt stopped at N01 setup after 17 requests. AI cross-review found no additional in-scope discoveries over the ordinary comparator. Its two unknowns came from a stricter parseability check on `closed_at='now'`, exposing a current-emulator engineering defect and weaker prior oracle validation. No superiority or false-positive rate is established. |
| Current post-fix engineering requalification: both comparators agreed on all 12 now-exposed ordinary-baseline cases, 229 metered requests | `artifacts/ordinary-baseline-2026-09-23/engineering-requalification/current-df40d4f.json`, source `df40d4fa37f3c0a7c1baff770db11e9dd204dc64`, pinned ARM64 Gitea. This validates the timestamp repair on the exposed workload; it does not change the frozen A1 outcome or create new holdouts. |
| Full-state E06 minimization: target state defect retained after metered final recheck, 81 total requests | `artifacts/engineering-minimization-2026-09-23/e06-evidence-bound.json` (final evidence-bound selector, 81 requests) and earlier `e06-state.json`. Exposed engineering cases only. |
| Release automation | Portable Linux ARM, macOS repair isolation, and ARM64 reference jobs are defined in `.github/workflows/ci.yml`. They were unobserved at the 2026-09-24 local review; inspect current [Actions](https://github.com/jlov7/realitybridge/actions) results before citing them. |

The current evidence map is [docs/EVIDENCE-INDEX.md](docs/EVIDENCE-INDEX.md).
The [next-increment result](research/next-increment-2026-09-23/RESULTS.md)
records a paired-row oracle challenge, an outside-review packet awaiting a
human reviewer, three bounded synthetic follow-up studies, and an exposed-case
transfer to pinned Gitea 1.24.6. The ordinary discovery arm detected the same
three planted faults with fewer reference requests than the RealityBridge arm;
the new decision study again found zero simulator-induced regret. These are
local AI-authored results, not independent validation or release approval.
The normal `src/reality_bridge/emulator.py` is repaired; the exact measured
pre-fix source is `experiments/research_baseline_emulator_19b2b47.py`.
A fresh source archive can replay the original study without Docker through
`experiments/public_workflow.py replay`; `experiments/replay_ordinary_baseline.py`
checks both public derivations of the frozen source snapshots and recomputes the A1 comparator
outcomes from raw rows without Git history.

## Historical milestone tracker (superseded by the current study above)

## Milestone tracker

| ID | Milestone | Exit criterion | State |
|----|-----------|----------------|-------|
| A | Reference bring-up | Pinned Gitea runs locally, resets repeatably, six supported operations verified against real OpenAPI, no network side effects, reset cost measured. | **COMPLETE for config/direct-client boundary**; network-layer egress denial is not claimed |
| B | Projection + planted-defect detection | Projection detects planted wrong-object, permission, state-update and duplicate-effect defects. Generator cannot filter inconvenient invalid sequences post-hoc. Normalization mutations caught by test. | **COMPLETE for response-level method tests**; silent backend effects remain outside the oracle |
| C | First real divergence | One documentation-only simulator produced; one real minimized divergence found. **No-divergence retained as a legitimate result.** | **COMPLETE** |
| D | Repair + query selection | Bounded repair loop; random and targeted probing arms at matched reference-call budget. Test proves repairs cannot read holdouts. | **HISTORICAL PARTIAL** — superseded by the current finite-study status above |
| E | Frozen comparison | Transition comparison frozen and run. Only then a small downstream-agent study. | **HISTORICAL PARTIAL** — 4 agree, 26 diverge in the earlier response-only run; superseded by the current full-state study |
| F | Release | Reproducible cases + simulator qualification manifest. Optional upstream/reviewer contact. **No acceptance assumed.** | **HISTORICAL LOCAL PREPARATION**; check current Releases separately. |

The detailed narrative below preserves the 2026-09-21 historical record. Its
old claim limits and incomplete milestones are not the current study result.
The 2026-09-22 `RESULTS.md` and immutable JSON receipts control current claims;
historical JSON remains unchanged.

## Milestone A evidence

**Reference identification.** `gitea/gitea` **rootless** variant, pinned by **digest**, not tag:

```
arm64/linux  sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9   (1.24.7-rootless)
```

The non-rootless variant was tried first and rejected with retained evidence: the s6 supervisor inside it cannot run as a non-root user (`.s6-svscan/lock: Permission denied`, exit 111), and Gitea's own CLI refuses to run as root ("Gitea is not supposed to be run as root"), which would have made admin/token setup impossible in automated execution.

**Six operations verified against the pinned build's real OpenAPI** (`/swagger.v1.json`, served by the running instance, swagger version 1.24.7, 285 paths). Selected for the issue/label lifecycle:

| Operation | Path |
|---|---|
| Create an issue | `POST /repos/{owner}/{repo}/issues` |
| Get an issue | `GET /repos/{owner}/{repo}/issues/{index}` |
| Edit an issue | `PATCH /repos/{owner}/{repo}/issues/{index}` |
| Add a label to an issue | `POST /repos/{owner}/{repo}/issues/{index}/labels` |
| Remove a label from an issue | `DELETE /repos/{owner}/{repo}/issues/{index}/labels/{id}` |
| Create a label | `POST /repos/{owner}/{repo}/labels` |

Notably, `POST /repos/{owner}` does **not** exist in this build — repo creation is `POST /user/repos`. The OpenAPI was consulted, which is the point.

**Reset determinism (integration test, real container).** `tests/test_reset_determinism.py` — 3 passed in 34.55s:
- Snapshot detects a mutation (the instrument is not blind).
- Reset+seed after a mutation returns to observably identical state (2 issues, exactly the authored seed).
- Reset stays inside the trial budget.

**Reset cost (G3), measured with a real reset:** down 1.31s / healthy 6.93s / admin 0.23s / seed 0.12s → **total 8.58s per reset**. Worst-case pilot (30 families × sequences ≤ 6 with a fresh state pair per step → ~180 resets) ≈ 26 minutes of reset overhead in the whole pilot. **Reset cost is not the bottleneck; the sequence grammar does not need shrinking for this reason.** This resolves the build-plan G3 risk.

## Milestone B evidence

**29/29 instrument tests pass, ruff clean.** Three test files + the sequence-integrity file:

- `contracts/operations.yaml` — bounded action grammar, six operations (verified against the pinned build's OpenAPI; methods are lowercase in the swagger, request bodies inline-`additionalProperties` — recorded, not assumed).
- `contracts/observation.yaml` — the projection contract: identifier mapping (logical identity, not literal id), label-set ordering normalization, timestamp *relations* not exact values, documented exclusions, and the four-way error taxonomy (permission_denied / not_found / validation_conflict / transport_uncertain).
- `src/reality_bridge/projection.py` — raw→observation mapping with explicit exclusion discipline.
- `src/reality_bridge/differential.py` — `compare() → Difference{agree, diverge, undetermined, unsupported}`; `undetermined` is first-class and never collapses into `agree`.
- `tests/test_wrong_object_detection.py` (5) — wrong-object caught via *semantic* fields, never the literal id; label-set membership loss caught despite order normalization.
- `tests/test_permission_boundary.py` (8) — all error-category pairings diverge; category matching agrees; an error never merges with success.
- `tests/test_normalization_mutations.py` (7) — the REQUIRED guard. The safe projection detects known divergences (title, state, wrong-object, body); a maintainer who over-normalizes makes these tests fail — caught by test, not inspection. Exclusions are documented (asserted against the contract file).
- `tests/test_sequences_integrity.py` (6) — the generator is a pure function of `(seed, max_len, count)`: no outcome channel exists, so post-hoc filtering is impossible *by API shape*, and determinism across a simulated outcome observation is asserted.
- `experiments/incumbent_probe.py` (+ retained JSON) — the G1 falsifier probe: **does ordinary plain-equality contract testing already catch everything cheaply?**

## G1 incumbent probe — what it proved

The project's central falsifier (from brief §10): *ordinary contract testing catches everything at comparable effort.* Ran 7 hand-built divergent/equal cases through both the incumbent (naive raw-field equality) and the instrument:

| Case | Incumbent (plain equality) | Instrument (projection) |
|---|---|---|
| C1 wrong-object (title) | diverge | diverge |
| C2 literal-id drift (semantically identical) | **diverge (FALSE alarm)** | agree |
| C3 state transition | diverge | diverge |
| C4 label-set order (equal members) | **diverge (FALSE alarm)** | agree |
| C5 duplicate effect | agree (blind — needs read-back) | agree (needs read-back oracle) |
| C6 permission vs not-found | diverge only if status not coarsened | diverge (taxonomy enforced) |
| C7 identical | agree | agree |

**Historical interpretation corrected:** raw field equality false-alarmed on literal-id drift and label order in these seven authored examples, and a response-only check could not see duplicate effects. This establishes the weakness of that deliberately naive comparator, not that competent ordinary stateful contract testing is inferior at comparable effort. The later shared-trace study above is a separate, narrower challenge.

## Milestone C evidence — first real divergence (live reference)

**The simulator diverges from the real application, and the divergence is now a finding, not an assertion.**

`experiments/differential_run.py` (live, container-backed) ran generated sequences through both the documentation-faithful emulator and the real Gitea, comparing after every step. Retained: `artifacts/evidence/differential-*.json`.

```
5 sequences run · 4 diverged · 1 no-divergence (legitimate result) · 0.7s
seq#0 diverged at step 0: create_label → ref=('label-2','0e8a16') sim=('label-2','#0e8a16')
seq#1 diverged at step 0: create_label → same root cause
seq#2 diverged at step 0: edit_issue  → labels ref=bug('d73a4a') sim=bug('#d73a4a')
seq#3 diverged at step 0: edit_issue  → same root cause
seq#4: NO DIVERGENCE (retained as a legitimate negative)
```

**Root cause (one defect, four divergences):** Gitea **normalizes label colors by stripping the leading `#`** (`d73a4a`, not `#d73a4a`), while the documentation-faithful emulator stored them verbatim. Exactly the "faithful to docs, wrong against reality" gap RealityBridge exists to find. Every divergence minimized to a 1-step prefix.

**Two engineering learnings, retained in history:**
1. **API-level soft reset required for the differential loop.** The first run reset the container (`down -v`) per sequence AND per shrink probe and wedged Docker into a non-responsive state. `soft_reset()` (delete repo + re-seed via API, deterministic, ~1s, zero Docker churn) succeeded — a full 5-sequence session now runs in 0.7s.
2. **Gitea returns `assignees: null`, not `[]`.** The projection now tolerates both shapes.

## Historical Milestone D evidence — repair + claimed holdout isolation

**Bounded repair loop, verified end to end against the real container.**

`experiments/repair_demo.py` takes the differential's minimized counterexample, derives the minimal rule from the *reference observation* (not the emulator internals), applies it through the emulator's public `normalize_color` seam, and re-verifies. Retained: `artifacts/evidence/repair-demo-*.json`.

```
divergence at step 0: create_label
  evidence: ref=('label-2','0e8a16') sim=('label-2','#0e8a16')
  minimal prefix: [create_label(label-2, #0e8a16)]

BEFORE repair: counterexample agrees? False
rules derived: ['strip_leading_hash']
counterexample now agrees: True
regressions still agree:   True
REPAIR VERIFIED
```

**Superseded interpretation:** the old tests demonstrated interface shape and
deterministic rule derivation. They did not prove OS/process isolation from
held-out files, and an empty regression list could vacuously pass.
- The `repair()` signature is `(emu, counterexample, regression_sequences, agrees)` — there is **no channel** through which a held-out family could be passed (asserted by signature inspection).
- The derived rule is a pure function of the counterexample's reference observation: two emulator worlds differing only in unrelated state derive the **same** rule.
- An empty regression list still derives the same rule — regression feedback is never required to derive, only to gate acceptance after.
- A counterexample with no un-hashed colour derives **no** rule (the worker cannot mine rules from anywhere else).
- The seam normalizes at **emission** only; storage stays verbatim (`emu.labels["random"].color == "#abcdef"`), so unrelated labels are untouched.

## Historical Milestone D query-selection arms (budget not established)

The retained arms used the same seed, count, maximum length, and sequence cap.
Those controls did not equalize reference HTTP requests because early exits,
resets, variable-cost operations, and shrink probes differed. The artifacts are
retained, but no matched-budget efficacy conclusion is supported.

```
ARM random:   sequences run: 5   divergences: 4   elapsed 0.8s
  create_label (color-hash), remove_label, get_issue ×2 (color-hash)
ARM targeted: sequences run: 5   divergences: 3   elapsed 0.9s
  add_label ×2, edit_issue (color-hash)
```

The descriptive counts were random 4 and targeted 3 divergences. They are not
an efficacy comparison until both arms are rerun at equal measured HTTP cost.

Two harness bugs surfaced by running the arms (both real, both fixed, retained in git history):
1. `_project()` crashed on list-typed responses (Gitea returns a **label array** for `add_label`/`remove_label`) — fixed by dispatching on response shape, not on op name alone.
2. `reference.step_reference` used `resp.is_json` (the `requests` API) — a latent `httpx` bug that only fired under error paths; fixed to a `try/except ValueError` decode.
3. The `Action`-vs-dict boundary in `reproduces()` (a `TypeError: 'Action' object is not subscriptable`) — fixed by normalizing to `.as_dict()` at the call site.

The repair mechanism is verified under the corrected gate. Query-selection
efficacy and enforced holdout isolation remain unproven.

## Milestone D unexpected-but-retained: Docker wedge

The differential run wedged Docker Desktop when the loop used the full container teardown per probe. Recovery: graceful quit, hard-stop backend, relaunch. **Not a Gitea issue — a harness design issue, fixed with soft reset.** Recorded in `src/reality_bridge/reference.py` because a future maintainer must not reintroduce per-probe container cycles.

## Milestone E evidence — frozen response-projection comparison

`experiments/families.py` contains 30 authored families (14 dev, 16 test).
The corrected runner compares projected responses after each step and stops at
the first non-agree outcome. It does not independently snapshot complete backend
state. Current evidence: `artifacts/evidence/frozen-comparison-1790096206.json`.

```
families run: 30 (dev 14, test 16)   elapsed 5.0s
DEV : coverage 14/14  agreement 2  disagreement 12  undetermined 0  unsupported 0  HTTP requests 132
TEST: coverage 16/16  agreement 2  disagreement 14  undetermined 0  unsupported 0  HTTP requests 150
```

The documentation-based emulator disagreed with the pinned reference response
projection on 26 of 30 authored families. All 30 produced determinate supported
comparisons. This does not establish full transition fidelity, population
frequency, or downstream policy effect.

**Honest caveats, stated not buried:** agreement here means *equal projection under the shared normalisation contract vs this pinned 1.24.7 rootless build* — it is not a claim that the reference is correct, and not a claim that unsupported cases agree. A precise per-family false-task-pass rate requires the reference's own pass/fail semantics per family, which remains a follow-up metrology step and is not claimed in this run.

## Commands run (Milestone A)

```bash
docker compose -f reference/compose.yaml up -d           # bring up
docker compose -f reference/compose.yaml down -v         # reset (wipes named volumes)
docker exec realitybridge-gitea gitea admin user create ...  # superseded: use compose exec -T gitea
curl http://127.0.0.1:13000/swagger.v1.json              # real OpenAPI for op selection
uv run pytest tests/test_reset_determinism.py            # 3 passed in 34.55s
uv run python -c "from reality_bridge.reference import reset; print(reset(with_seed=True))"
```

Python env: `uv venv --python 3.12`, `uv pip install -e '.[dev]'` → httpx 0.28.1, pytest 9.1.1.

## Bugs found and fixed (each retained in git history)

1. **Wrong image variant.** Non-rootless image cannot run as uid 1000 (s6 lock). Fixed by switching to `-rootless` digest. This is a reproducibility finding, not cosmetic — a fresh checkout using the non-rootless pin fails at container start.
2. **`compose exec` target.** Compose exec addresses the *service* name, not the container name. The first draft passed `realitybridge-gitea` (container); the service is `gitea`. Fixed; verified by `compose exec -T gitea ...`.
3. **API prefix.** `BASE_URL` was the web root; all Gitea API calls need `/api/v1`. Reproduced a 405 (`/user/repos` is a GET-only web route) before fixing.
4. **Repo root resolution.** `Path(__file__).resolve().parents[1]` from `src/reality_bridge/reference.py` resolves to `src/`, not the repo root. Fixed to `parents[2]`.
5. **Deprecated config.** `GITEA__repository__DISABLE_MIRRORS` is deprecated since v1.19.0 and its fallback is gone in 1.24. Replaced with `GITEA__mirror__ENABLED=false`.

## Untested empirical claims

- That a documentation-only simulator will diverge from Gitea in a *consequential* (policy-affecting) way. **Partially established.** A real divergence exists and is repaired (label-colour normalization), but it is a representation-level gap. Whether the simulator diverges on a *consequential* case — one that changes which agent policy wins — remains untested. Explicitly out of v1 scope.
- That targeted probing beats random probing at equal reference-call budget.
  **UNTESTED under corrected metering.** The historical 3-vs-4 counts did not
  retain equal measured HTTP-request costs.
- Whether the six operations behave identically across OS/architectures of the same image. **Not tested. Pinned to arm64/linux digest only.**
- Whether reset determinism holds under load beyond the integration test. **Partially tested; the arms and frozen comparison accumulated more trials without failure.**
- **No network side effects.** **RESOLVED:** `tests/test_reference_isolation.py` asserts at the config surface that outbound integration channels are disabled and binds are loopback-only (6 assertions). Network-level egress impossibility is environment-dependent and NOT claimed.

## Open research questions

The next scientific checks, if pursued, are:
1. Add an independent post-state oracle if transition or duplicate-effect
   coverage is to be claimed.
2. Rerun random and targeted arms with equal retained metered HTTP cost.
3. Define and execute a consequential policy-selection study, if pursued.
4. Obtain independent evaluator review or replication before an externally
   validated contribution claim.

## Known open risks

1. **Network-layer egress isolation unproven.** Application channels are
   disabled, the host bind is loopback-only, and the adapter ignores proxy
   environment variables and redirects. Docker-level egress denial is not shown.
2. **Normalization can erase the signal.** Guarded by `tests/test_normalization_mutations.py` — but the guard only protects the *current* projection; new fields added later must extend it.
3. **Same-author evaluator.** Independent read-back from the API contract reduces, but does not remove, correlated normalization/evaluator error.
4. **The found divergence is representation-level, not yet consequential.** The repair proof is real, but a policy-selection story needs a divergence that changes which agent behaviour wins. If none exists for this reference, that is itself a finding about the reference and scope.
5. **Query-selection result absent.** The prior arms run was not matched on
   measured HTTP requests.
6. **Response-only blind spot.** Silent extra backend mutations can escape the
   current per-step projection.
