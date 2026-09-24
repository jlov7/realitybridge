# RealityBridge finite study result — 2026-09-22

The frozen, local study completed against the pinned ARM64 Gitea image. The
measured candidate was the deliberately imperfect emulator at source commit
`19b2b4776b538ca5bf7326118fe6fcdae7f21cd2`. The study found three
response or state divergences in the 16 new evaluation cases. It did not find
a simulator-caused policy selection error in the six scripted evaluation task
instances. The later engineering fixes are separate from this measurement.

The controlling evidence is the unmodified JSON under
`artifacts/research-completion-2026-09-22/attempt-20260922T182622Z-59359/`.
Its `receipt.json` SHA-256 is
`f96145b240dc2d6b759ce8b0a590843c6b39d51685188735558036a9ea0e3216`.
The protocol SHA-256 is
`60e5f90b4f588b304ab25453d2b96d690a8222d97183d9fb8d3d5a61b5e91e8c`;
the concrete 30-case inventory hash is
`3d286c5707f1f560fbf06d6e2c4666742c1b62102ff5af1629162d2b5650fe60`.
The container was checked as
`gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9`
on `linux/arm64`, in only the `rb-research-20260922` Compose project, bound to
loopback port `13002`. Every harness HTTP request, including setup, errors,
read-backs and paginated state observations, was metered. Docker healthchecks
and Compose status probes are explicitly outside that count.

## Full-state and repair checks

The initial reference and candidate states agreed after the previously known
leading-hash color repair. The independent oracle compared all declared issue
and label rows, cardinalities, issue-label memberships, duplicates, closed
presence, and timestamp ordering after every action. Planted extra issue,
label, membership and duplicate-row effects were detected in unit tests.
Malformed declared response fields were classified `undetermined`, not as
agreement. The repair worker's ordinary staged read succeeded; its attempted
read of `experiments/prospective_cases.py` was denied by macOS `sandbox-exec`.
The receipt retains worker, compiler, binary and profile hashes and the
repository-relative denied path. This is an OS read-boundary proof for that
worker invocation, not a general security certification.

## Cost-controlled discovery

Each arm had a hard cap of 180 actual reference HTTP requests and admitted a
whole case only when its declared maximum fit. The fixed targeted order ran
once. Three random orders used seeds `20260922`, `20260923`, and `20260924`.
At each shared cutoff, only cases completed at or before the cost cutoff enter
the comparison.

| Random seed | Shared cutoff | Random completed / 14 | Targeted completed / 14 | Random divergent families | Targeted divergent families |
|---|---:|---:|---:|---:|---:|
| 20260922 | 160 | 11 | 10 | 1 | 3 |
| 20260923 | 162 | 10 | 11 | 2 | 3 |
| 20260924 | 162 | 10 | 11 | 2 | 3 |

The targeted arm first found a difference at request 13; random orders first
found one at requests 160, 28 and 42. Targeted found three distinct divergent
case instances within each shared cutoff. These fixed authored orders and three
seeds do not estimate a population-level advantage or establish that targeted
probing is generally more efficient. Arm totals were 162 targeted and
160/176/178 random requests; all arms stopped before admitting a case that
could exceed the 180-request cap. Full per-action outcomes, censoring and the
fixed defect-signature taxonomy are in the arm JSON files.

## New evaluation cases

All 16 new cases completed; 13 agreed and three diverged. There were no
`undetermined` or `unsupported` evaluation outcomes.

| Case | Observed difference |
|---|---|
| E04 | A second removal of the same registered label was a successful no-op in Gitea; the candidate returned 404. |
| E06 | Gitea retained two distinct registry rows with the same label name and preserved the original issue membership; the candidate overwrote the name-keyed row. The action responses agreed, but full state differed. |
| E09 | Adding a label name absent from the registry returned the unchanged membership in Gitea; the candidate returned 404. |

These are genuine simulator fidelity defects for the tested build. They were
retained as measured baseline findings and fixed only after this study.

## Scripted policy consequence

All three policies ran independently on each backend for four selection and
six separately parameterized evaluation task instances. Every backend used
its own responses and predeclared stop rule. The simulator and reference both
ranked `minimal`, `ensure_prerequisite`, then `inspect_first` on selection
tasks. There were zero simulator false task passes across the 30 policy/task
pairs. The selected policy's per-task reference regret totaled 99 utility
points, all on P05, where the selected policy tried to add a new label before
creating it. The reference-selected policy was also `minimal`; the signed
simulation-induced decomposition component was 0, and the task-instance shift
component was 99. This decomposition is arithmetic, not a universally
nonnegative causal effect. The result does not support a claim that this
simulator misled policy selection in the measured task set.

## Post-study engineering state

The current default `Emulator` includes the verified color normalization and
the three narrow label-behavior fixes. The exact pre-fix emulator source is
retained byte-for-byte at
`experiments/research_baseline_emulator_19b2b47.py` (SHA-256
`61b81d7b4f5c97a1116855fbb93c422d772d9342c5503c1f84b7bd659f3c02ac`).
`experiments/materialize_research_baseline.py` creates a fresh local checkout
using that source; from it, the original receipt was reproduced without access
to the private Git commit. A separate exposed-case requalification at current
commit `3e1870a8aec8` found 30/30 case agreements and 3/3 matching final
policy states for P05, using 554 metered reference requests. Its unique
receipt is
`artifacts/research-completion-2026-09-22/post-study-requalification-20260922T183442Z-62290.json`.
Earlier six-case post-fix attempts are also retained; none is prospective
holdout evidence.

For the exact measured result, run
`experiments/reproduce_research_completion.py` against the attempt directory
from a source tree created by `experiments/materialize_research_baseline.py`.
The reproducer recomputes case outcomes, cost cutoffs, policy rankings and
regret from the raw JSON, and checks the frozen protocol, case and source
hashes. The current default simulator can be checked using
`experiments/post_study_requalification.py` against the isolated reference.

## Claim limit

This is one synthetic, authored pilot against one pinned reference build and
six operations. Case instances share structural patterns. Reference and
evaluator code were AI-authored and have not had independent human review.
The study does not establish general API fidelity, population-level probing
efficiency, cross-version behavior, model-agent impact, normative correctness,
security certification, hosted CI, publication or release readiness.
