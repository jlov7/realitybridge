# Experimental protocol — observation projection and comparison

**Status:** historical v1 design seed, frozen at Milestone C. The prospective
2026-09-22 research-completion study is separately frozen in
`docs/research-completion-2026-09-22/PROTOCOL.md`; its result must not be read
back into this historical design. Changes require a `STATUS.md` entry with
reason.

## 1. Observation projection

A projection maps a raw API exchange to the fields that count as "what happened." It must be **declared**, and its exclusions must be documented.

```python
step(action) -> Observation
reset(seed) -> InitialStateRef
compare(reference_observation, simulator_observation, projection) -> Difference
shrink(sequence, reproduces_difference) -> MinimalCounterexample
```

`Difference` has four outcomes, and the third is not optional:

- `agree`
- `diverge(reason, evidence)`
- **`undetermined(reason)`** — comparison could not decide
- `unsupported(operation)` — simulator explicitly does not implement it

`undetermined` must never collapse into `agree`. Over-normalisation is the primary way this project could erase the very differences it exists to find.

## 2. Normalization rules (normative for this project)

| Dimension | Rule | Failure mode if done naively |
|---|---|---|
| **Identifiers** | Map objects by logical identity established during paired creation | Stripping all IDs makes a wrong-object response undetectable |
| **Time** | Control the clock, or compare justified relations/ranges | Stripping a timestamp that governs expiry or ordering |
| **Unordered collections** | Normalize only where the contract permits arbitrary order | Hides pagination boundaries and duplicate membership |
| **Errors** | Keep permission-denial / not-found / validation-conflict / transport-uncertainty distinct | A uniform error category conceals precisely the mismatches under study |
| **Concurrency** | Exclude from the first deterministic claim unless explicitly scheduled | Instant-equality grading or poll-until-success both fabricate agreement |

## 3. Experimental arms

1. Documentation-only generated emulator.
2. Hand-coded / documentation-based emulator (strong baseline).
3. Generated emulator + **random** reference probing + bounded repair.
4. Generated emulator + **targeted** probing + bounded repair.
5. Real reference application (for downstream policy evaluation only).

Budgets held identical across arms 3 and 4, **or** both fixed-budget and
best-achievable tracks reported. The reference-query count includes every HTTP
request made by setup, failed calls, read-backs, resets, and shrink probes. The
harness meters actual requests. Equal seeds, sequence counts, or maximum lengths
do not establish an equal query budget; an arms comparison is matched only when
the retained measured counts are equal.

## 4. Measures

**Primary:** held-out consequential transition disagreement; false task-pass frequency; reference-call + repair cost.

**Secondary:** policy-ranking stability (with ties and uncertainty); selected-policy regret on the real reference; simulator runtime speed; unsupported-operation coverage.

**Publish coverage and agreement jointly.** A simulator that safely reports `unsupported` is not equivalent.

## 5. Pilot sizing

Six operations, **30 authored semantic test families**, sequences up to six steps. Development and test families fixed and disjoint.

These counts **size a pilot**. They do not establish statistical power or population representativeness. Repeated sequences on one family are repetitions, not new cases. Preserve denominators.

## 6. Policy-selection design

Scripted policies first — this cheaply separates simulator error from model variability. Then a small frozen set of agent configurations on reference and simulator.

**Use discovery tasks to choose a policy. Use held-out tasks to estimate how that choice performs.** Reusing selection data for the regret estimate overstates the contribution.
