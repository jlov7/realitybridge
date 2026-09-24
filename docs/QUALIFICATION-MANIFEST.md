# Simulator qualification manifest — RealityBridge

**Historical response-only qualification.** This manifest is preserved for
the earlier source and is superseded for current claims by
`docs/research-completion-2026-09-22/RESULTS.md`. Its 4/30 figure does not
describe either the later prospective baseline or the current repaired
simulator.

- Audit date: 2026-09-22
- Audit base: `bec59d73ad52c262cd387f07a31242fa36d36d32`
**Reference:** `gitea/gitea` 1.24.7-rootless, linux/arm64 digest
`sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9`

This is a local qualification statement for a response-projection experiment.
It is not equivalence, bisimulation, a product certificate, a policy-selection
result, a publication receipt, or evidence of independent replication.

## Verified scope of this historical audit

| Surface | Current evidence |
|---|---|
| Four-way evaluator | `tests/test_differential_outcomes.py`; transport uncertainty, missing payloads, and explicit unsupported operations fail closed |
| Projection mutation guards | `tests/test_normalization_mutations.py`, `tests/test_wrong_object_detection.py`, `tests/test_permission_boundary.py` |
| Repair acceptance | `tests/test_repair_holdout_isolation.py`; pre-repair divergence, nonempty regressions agreeing before and after, candidate promotion only after all gates pass |
| Reference network boundary | digest pin, loopback bind, direct HTTP client with proxy environment disabled and redirects off |
| Isolated live lifecycle | configurable Compose project, loopback port, project-scoped token state, and project-scoped volumes |
| Deterministic reset | 3 live tests passed in 36.10 seconds in isolated project `rb-codex-audit-20260922` |
| Corrected frozen comparison | `artifacts/evidence/frozen-comparison-1790096206.json` |
| Corrected repair demo | `artifacts/evidence/repair-demo-1790096208.json` |

The frozen comparison replayed 30 authored families (14 dev, 16 test) against
the emulator and pinned reference. Each family stopped at the first non-agree
outcome. The corrected result was:

```text
dev:  n=14  agree=2  diverge=12  undetermined=0  unsupported=0  HTTP requests=132
test: n=16  agree=2  diverge=14  undetermined=0  unsupported=0  HTTP requests=150
total: 4 agree, 26 diverge, 282 metered reference HTTP requests
```

Agreement means equal projected responses for this pinned build and authored
scope. The runner does not take an independent full backend snapshot after each
mutation. A silent extra mutation that leaves the returned response unchanged
can therefore escape this instrument.

## Repair result and isolation boundary

The corrected live repair demo confirmed a divergence before applying the
candidate rule, verified one previously agreeing regression before repair,
then observed strict agreement on the counterexample and regression after the
candidate. Only then did it promote the rule. Unknown, unsupported, an empty
regression set, or a failed post-repair gate cannot certify or mutate the live
candidate.

The repair function has no holdout parameter and rule derivation uses paired
reference/simulator counterexample values. This is an interface-level control.
The worker runs in the same Python process and checkout; no OS sandbox prevents
arbitrary future code from reading held-out files.

## Historical evidence corrected by this audit

The 2026-09-21 JSON files remain in `artifacts/evidence/`. They are not deleted
or rewritten. Their following interpretations are superseded:

- Equal `transport_uncertain` results could be reported as agreement.
- The repair demo treated every outcome except `diverge` as agreement.
- `all([])` certified an empty regression set.
- The repair rule could be inferred from the reference value without checking
  the paired simulator value.
- Same seed, sequence count, and maximum length were called a matched reference
  budget, although resets, read-backs, variable endpoint cost, and shrink probes
  were not metered.
- Signature inspection was described as proof that repair could not read
  holdouts.
- Response comparison was described as response-plus-resulting-state coverage.

The historical random-versus-targeted result therefore does not establish a
matched-budget negative result. A new arms run with equal retained metered HTTP
request counts is required.

## Reproduction and package boundary

From a source checkout:

```bash
uv sync --extra dev --locked
uv run ruff check .
uv run ruff format --check .
uv run pyright src tests experiments reference
uv run pytest tests/ -q -p no:cacheprovider -k 'not reset_determinism' \
  --cov=src/reality_bridge --cov-report=term-missing

export REALITYBRIDGE_COMPOSE_PROJECT=rb-local-check
export REALITYBRIDGE_PORT=13001
export REALITYBRIDGE_REQUIRE_REFERENCE=1
uv run pytest tests/test_reset_determinism.py -q -p no:cacheprovider
uv run python experiments/frozen_comparison.py
uv run python experiments/repair_demo.py
docker compose -p "$REALITYBRIDGE_COMPOSE_PROJECT" \
  -f reference/compose.yaml down -v
```

The wheel contains the core `reality_bridge` package. The Compose file and seed
module are source-checkout assets, so live lifecycle operations intentionally
fail with a clear source-checkout requirement when those assets are absent.

## Remaining blockers

- No independently implemented evaluator or external replication.
- No full post-state oracle for silent or duplicate backend effects.
- No consequential policy-selection or regret measurement.
- No valid matched-cost random-versus-targeted result under the corrected meter.
- One authored family set and one ARM64 reference build; no power or population
  claim.
- CI is configured but no hosted CI run is claimed.
- The repository has not been published or released by this audit.
