# Limitations

This file records the earlier design-time limitations. The completed finite
study and its remaining claim limits are in
`docs/research-completion-2026-09-22/RESULTS.md`. Response-only and
interface-only statements below refer to the historical evaluator and legacy
repair function, respectively. The prospective runner added a full declared
state oracle and a separate sandboxed C repair worker. The 2026-09-23
ordinary comparator study is separately indexed in `docs/EVIDENCE-INDEX.md`;
its first attempt stopped at setup, and the amended attempt does not establish
a case-discovery advantage. The historical open-risk statements below are not
claims that the 2026-09-22 full-state study remained unrun.

## Known at design time

1. **One reference application.** Gitea at a pinned version. "The reference" means *this build of Gitea*, not "correct issue-tracker behaviour."
2. **Six operations.** Coverage outside them is `unsupported`, which is reported, not hidden.
3. **Same-author evaluator.** Independent read-back from the API contract reduces, but does not remove, correlated normalization/evaluator error. External adversarial review remains necessary.
4. **Fidelity ≠ safety.** If Gitea has a bug and the simulator reproduces it, fidelity is achieved and nothing has been validated. These are separate axes and must be reported separately.
5. **Finite passing suite ≠ equivalence.** The supported statement is agreement over a stated tested scope and observation projection.
6. **Authored pilot.** The earlier 30-family comparison and later prospective
   30-case study do not estimate population frequencies. No power analysis or
   population claim is supported.
7. **No improved-agent-training claim in v1.** Current evidence concerns simulator fidelity. Downstream agent improvement requires evidence this project does not yet have.
8. **Scripted policies first.** Any agent-based result carries model variability that the simulator comparison must not absorb.

## Structural risks

- **Normalization erases signal.** Primary technical risk. Mitigated by mandatory mutation tests.
- **Repair overfits.** The repair API omits holdout inputs and verification
  requires nonempty regressions that agree before and after a candidate repair.
  This is interface discipline, not OS/process isolation from held-out files.
- **Response projection is not full post-state observation.** The harness
  compares API responses and one bounded read-back path. It can miss a silent
  extra backend mutation that leaves the returned response unchanged.
- **Targeted probing may add nothing.** This is the central algorithmic
  hypothesis. The historical arms were not matched on measured HTTP cost, so
  the null or benefit remains untested under the corrected harness.
- **Container/reset cost dominates.** Bounded sequence grammar required; resets must be cheap or the pilot is infeasible.

## What a reviewer should attack

- The strongest overlooked predecessor (candidates: RESTler-adjacent work, stateful conformance testing literature).
- The simplest baseline that defeats the design (ordinary contract testing at comparable effort).
- One fatal experimental flaw.
- The smallest additional contribution they would consider useful.

## Falsifiers we commit to reporting

The project **fails as a new contribution** if: ordinary contract testing catches everything at comparable effort; targeted probing adds nothing over random; repair overfits; or the output is merely another authored toy environment. Those outcomes may still yield useful regression tests — they do not justify a platform claim.
