# Prospective bounded research-completion protocol

- **Frozen before implementation results:** 2026-09-22
- **Pre-execution correction:** policy execution independence and task-instance
  wording corrected after adversarial design review; no live outcome had been
  observed. The original freeze remains in Git history.
- **Reference:** pinned Gitea 1.24.7 rootless ARM64 image already declared in
  `reference/compose.yaml`
- **Scope:** the six operations in `contracts/operations.yaml`, one synthetic
  repository, scripted policies, local execution only

This protocol closes three previously open endpoints: complete declared-domain
post-state comparison, cost-controlled random versus targeted discovery, and a
bounded policy-selection consequence test. A null or adverse result completes
an endpoint when the run is valid. The protocol does not require a positive
effect.

The historical 30 families have already been executed and inspected. They are
a requalification set, not prospective holdout evidence. This study freezes a
new authored set of 30 cases before observing its reference outcomes: 14
development cases and 16 evaluation-only cases. The set is an authored pilot,
not a population sample or independent human benchmark.

## Completion criteria

The local research result is complete when all of the following are retained
against exact source and protocol hashes:

1. The oracle detects planted silent extra mutations and, on every valid live
   trial, compares equal initial states before comparing actions.
2. Three random development orders and one fixed targeted order run under the
   same 180-request hard cap, with every reference HTTP request metered and no
   filler requests.
3. A repair worker executes behind an OS-enforced read boundary, a deliberate
   forbidden read is denied, ordinary staged input succeeds, and promotion
   remains fail-closed.
4. Scripted policy selection and reference evaluation retain every policy's
   simulator and reference utility, deterministic rankings, false-pass status,
   selected-policy utility, best-reference utility, and regret.
5. Setup failures, budget censoring, unsupported operations, undetermined
   comparisons, and negative results remain in the denominators and receipts.

An initial-state mismatch is a setup failure. It is never counted as an action
failure. The affected run must stop, the cause must be corrected, and the
protocol must be refrozen before a replacement run is interpreted.

## Endpoint 1: complete declared-domain post-state oracle

After reset and after every action, the evaluator obtains raw state separately
from each system and canonicalizes it without importing simulator transition
logic. The reference is read through paginated API list endpoints. The
simulator exports raw state only.

The canonical state contains:

- issue cardinality and every issue's number, title, body, state, closed
  presence, timestamp relation, and assignee set;
- label-registry cardinality and every label's name and color;
- every issue-to-label membership with label name and color;
- duplicate rows, if returned, because canonicalization sorts tuples without
  converting them to sets.

Pagination continues until the returned page is shorter than the fixed page
size. Cardinality is compared separately from row content. Exact database IDs,
URLs, and exact timestamp values remain outside the declared contract.

Each action has two comparisons: its response projection and its full post-state
projection. Family outcome is `agree` only when every action has determinate,
supported response and state agreement. A response can agree while the state
diverges. Tests plant an extra issue mutation, an unrelated label mutation, and
a duplicate state row while preserving the expected action response; all must
diverge.

The known leading-hash color rule is requalified before the study and applied
to the candidate used by the prospective run. Initial-state oracle equality is
then required. This prevents a known seed normalization difference from being
misattributed to every later action.

## Endpoint 2: reference-cost-controlled discovery

### Frozen cases

Development cases are visible to discovery and repair:

| ID | Actions |
|---|---|
| D01 | create issue `p2-dev-create`; get issue 3 |
| D02 | close issue 2; get issue 2 |
| D03 | add `ui` to issue 2; get issue 2 |
| D04 | remove `bug` from issue 1; get issue 1 |
| D05 | create label `p2-dev-bare` with color `112233` |
| D06 | create duplicate seeded label `bug` with color `445566` |
| D07 | create issue with an empty title |
| D08 | create a label with an empty name and color `123456` |
| D09 | get absent issue 801 |
| D10 | close absent issue 802 |
| D11 | add absent label `p2-dev-missing` to issue 1 |
| D12 | remove unattached label `api` from issue 2 |
| D13 | add duplicate label `bug` to issue 1; get issue 1 |
| D14 | create `p2-dev-attach` with color `#778899`; add it to issue 2; get issue 2 |

Evaluation cases are unavailable to the repair worker and are not executed
until discovery and repair outputs are frozen:

| ID | Actions |
|---|---|
| E01 | create issues `p2-eval-a` and `p2-eval-b`; get issue 4 |
| E02 | close issue 2; reopen issue 2; get issue 2 |
| E03 | add `bug` then `api` to issue 2; get issue 2 |
| E04 | remove `bug` twice from issue 1; get issue 1 |
| E05 | create label `p2-eval-hash` with color `#abcdef` |
| E06 | create label `p2-eval-dupe` with `111111`; create it again with `222222` |
| E07 | create an issue with an empty title; get issue 2 |
| E08 | close issue 1; reopen absent issue 901; get issue 1 |
| E09 | close issue 1; add absent label `p2-eval-missing` to it; get issue 1 |
| E10 | remove `bug` from absent issue 902 |
| E11 | create `p2-eval-twice`; add it twice to issue 2; get issue 2 |
| E12 | close issue 1; remove `bug`; reopen issue 1; get issue 1 |
| E13 | create issue `p2-eval-created`; add `ui` to issue 3; get issue 3 |
| E14 | create `p2-eval-l1` and `p2-eval-l2`; add the latter to issue 2; get issue 2 |
| E15 | get absent issue 903; get issue 1 |
| E16 | create an empty-name label; create `p2-eval-after-invalid` with color `334455` |

The concrete case module must hash to the value retained with the result. A
case cannot be changed after a reference outcome is observed without a protocol
amendment and a new study label.

### Arms and order

- Random arm orders are deterministic shuffles of D01-D14 using seeds
  `20260922`, `20260923`, and `20260924`.
- The targeted arm uses this fixed, outcome-independent boundary order:
  `D06,D12,D11,D08,D07,D10,D09,D13,D14,D04,D03,D02,D05,D01`.
- Seed repetitions measure order sensitivity. They are not additional task
  diversity. The targeted order is executed once and paired analytically with
  each random order.
- No arm receives evaluation cases or previous arm outcomes. No shrinking
  occurs inside an arm.

### Request accounting and exhaustion

Each arm has a hard cap of 180 harness-issued reference API requests. The meter
covers failed calls, API reset and seed calls, the initial oracle, action calls,
operation read-backs, and every post-action oracle page. Initialization, repair
verification, prospective evaluation, and policy evaluation are also metered in
separate, non-nested ledger categories so every harness request appears exactly
once and the total experiment cost remains reconstructable. Docker healthchecks,
Compose status checks, and other infrastructure probes are excluded and reported
separately; this is not a claim about total server traffic.

There are no padding or idle requests. A case of `n` actions is admitted only
when at least `10 + 5n` requests remain: eight for soft reset and seed, two for
the initial two-list oracle, and at most three action requests plus two oracle
list requests per action. The runtime checks each component against this bound.
A hard meter refuses a request at the cap. A bound violation censors the arm;
it is not repaired after observing outcomes.

Arms may consume unequal useful totals because a whole next case does not fit.
For each random/targeted pairing, the comparison cutoff is
`min(random_requests_used, targeted_requests_used)`, selected from cost alone.
Only cases completed at or before that shared cutoff contribute to the primary
comparison. Outcomes completed later are retained but excluded. The receipt
reports, per arm and cutoff:

- completed families / 14 and censored families / 14;
- families with any response or state divergence / completed families;
- unique predeclared defect signatures per request;
- actions with response mismatch / compared actions;
- actions with state mismatch / compared actions;
- undetermined and unsupported families and actions;
- call offset of each completed case and first discovery.

No statistical superiority or population effect is inferred from three orders.

## Enforced repair boundary

The repair worker is a separate `sandbox-exec` process. Its profile denies by
default and grants read access only to the worker program, required system
runtime files, and a temporary staged discovery-input directory. It grants
write access only to a temporary output directory and denies network access.
The repository, historical artifacts, and evaluation-case module are not
staged.

Two checks are mandatory before use:

1. allowed execution reads staged input and writes a declarative proposal;
2. a deliberate attempt to read the evaluation-case file is denied.

If `sandbox-exec` is unavailable or either check fails, repair is unavailable;
the controller cannot fall back to an interface-only boundary. The worker can
emit only the bounded rule schema already supported by the project. The
controller applies a proposal to a copy, verifies the originating development
counterexample, initial-state equality, and nonempty development regressions,
then promotes it. Evaluation results never gate or revise a proposal.

## Endpoint 3: scripted policy consequence

No LLM or agent configuration is used. Three fixed policy templates are
compared:

- `minimal`: shortest direct plan for the goal;
- `inspect_first`: a target issue read followed by the direct plan;
- `ensure_prerequisite`: establish the relevant lifecycle or label
  precondition, then perform the direct plan.

Four development task instances select one policy using mean simulator utility.
Six separately parameterized evaluation task instances estimate consequence on
the reference. They are disjoint instances, not claims of distinct semantic
task families.

Selection goals:

1. issue 2 is closed;
2. issue 2 has label `ui`;
3. label `p2-policy-dev` exists with color `556677`;
4. issue 1 lacks label `bug`.

Evaluation goals:

1. issue 1 is closed;
2. issue 2 has label `api`;
3. label `p2-policy-eval` exists with color `8899aa`;
4. issue 2 lacks label `bug`;
5. issue 1 has new label `p2-policy-attach`;
6. issue 1 is open after a close/reopen lifecycle.

Each policy-task pair starts from equal reset state, but then executes
independently on each backend using only that backend's responses and the
predeclared stop rules. A backend stops its own plan on its own response error,
unsupported result, or undetermined result. A cross-backend response or state
divergence is recorded diagnostically after execution and never steers either
backend's plan. Transport failure or request-cap exhaustion can censor the
affected trial. Goal success is decided only from that backend's final full
state. Utility is `100` for goal success, `0` otherwise, minus the number of
attempted actions. Policy ranking uses descending mean utility, then ascending
total attempted actions, then lexicographic policy name. The tie-break is fixed
here.

The receipt retains every policy's simulator and reference utility on every
selection and evaluation task. It reports:

- simulator-selected and counterfactual reference-selected policy;
- selection-rank disagreement;
- simulator false task-pass count;
- reference evaluation utility of the simulator-selected policy;
- best reference policy evaluation utility;
- total regret and per-task regret;
- simulation-induced regret separately from regret across the separately
  parameterized task instances.

A planted simulator defect must change a policy ranking and produce positive
regret in a unit test. The live result may show no ranking change or no regret;
that is a completed negative endpoint.

The policy phase has a hard ceiling of 750 reference HTTP requests. Every reset,
initial oracle, action, read-back, and post-action oracle is included. Exceeding
the ceiling censors the phase.

## Evidence and claim ceiling

The final result receipt includes exact Git commit, dirty-tree state, protocol
hash, case hash, image digest, architecture, commands, request ledger, every
family and action outcome, repair-boundary checks, policy matrices, elapsed
time, and failure/censoring status. Raw synthetic API responses may be retained;
tokens are never retained.

This study can support conclusions only for the authored cases, declared
projection, pinned ARM64 image, and scripted policies. It cannot establish
population frequencies, cross-version or cross-architecture fidelity,
independent evaluator validity, safety, publication readiness, or performance
of model-based agents.
