# Contributing

Evidence-first experimental repository. Start with the [architecture](docs/ARCHITECTURE.md),
[current status](STATUS.md), and [evidence precedence](docs/EVIDENCE-INDEX.md).
The [2026-09-22 protocol and result](docs/research-completion-2026-09-22/RESULTS.md)
control the measured finite-study claim; the later ordinary comparator has a
separate [protocol](research/ordinary-baseline-2026-09-23/PROTOCOL.md) and
[amendment](research/ordinary-baseline-2026-09-23/AMENDMENT-1.md). Do not
reinterpret a frozen result by changing its cases or estimator after observing outcomes.

## Non-negotiable rules

1. **Never claim equivalence.** The manifest is a qualification over a stated
   tested scope — not bisimulation, not a certificate. "The simulator equals
   production" must never appear in any output.
2. **Preserve the four-way taxonomy.** `undetermined` and `unsupported` are
   first-class outcomes. Code that collapses them into `agree` is a regression.
3. **Keep the over-normalisation guard.** `tests/test_normalization_mutations.py`
   exists to catch a maintainer who normalises away the divergences this
   project hunts. If your change touches the projection, those tests must stay
   green — extension beyond the current stated scope must add new cases, not
   weaken existing ones.
4. **Reference stays pinned and isolated.** Changes to `reference/compose.yaml`
   must keep the digest pin, loopback-only binds, and outbound-channel
   disabling. The isolation test asserts all three.
5. **State the exact repair boundary.** The legacy repair function has an
   interface-only boundary. The prospective C worker has a tested macOS
   sandbox boundary for its staged input and one forbidden repository path.
   Neither is a general security certificate.
6. **Failures are retained.** New finite-study evidence goes under
   `artifacts/research-completion-2026-09-22/` with a unique attempt name.
   Historical evidence under `artifacts/evidence/` remains unchanged. Do not
   silently replace or delete a failed attempt.

## Development loop

```bash
uv sync --python 3.13 --extra dev --locked
uv run ruff check .
uv run ruff format --check . \
  --extend-exclude experiments/decision_consequence.py \
  --extend-exclude experiments/prepare_blind_oracle_packet.py \
  --extend-exclude experiments/research_completion.py \
  --extend-exclude experiments/version_transfer.py \
  --extend-exclude reference/owned_second_version.py \
  --extend-exclude src/reality_bridge/state_oracle.py
uv run pyright src tests experiments reference
uv run pytest tests/ -q -p no:cacheprovider -k 'not reset_determinism and not repair_sandbox'
uv run python experiments/public_workflow.py replay
```

The macOS sandbox test is a separate required host-specific check; the ARM64
Docker reference test runs through `reference/owned_lifecycle.py` with an
explicit unique `REALITYBRIDGE_COMPOSE_PROJECT` and free `REALITYBRIDGE_PORT`.
See the live example below. A local unsupported host can omit those checks
while reporting them as unverified; required CI jobs fail if prerequisites are
missing. Never manually sweep a Compose project you did not create.

## Offline replay

From a source checkout or source archive with Python 3.11 or 3.13, Git, and `uv`, run
`uv sync --python 3.13 --extra dev --locked`, then:

```sh
uv run python experiments/public_workflow.py replay --output /tmp/realitybridge-replay.json
uv run python experiments/replay_ordinary_baseline.py --output /tmp/realitybridge-ordinary-replay.json
```

The first command materializes the exact measured pre-fix baseline into a
temporary tree and checks the retained 2026-09-22 receipt without Docker or
private Git history. It should report `13 agree / 3 diverge`, 1,518 recorded
requests, and the scripted policy decomposition shown in the README. Missing
receipt files fail with their path; invoking the raw reproducer against the
repaired default source instead fails with `source manifest mismatch`.

The second command verifies both [public derivations of the frozen ordinary-study
source archives](research/ordinary-baseline-2026-09-23/PUBLIC-SNAPSHOT-DERIVATION.md),
their unchanged source manifests, and the raw receipts; it then rematerializes
the measured emulator and recomputes each
method from retained raw rows. Its expected amended totals are instrument
`10 agree / 2 diverge`, ordinary `8 agree / 2 diverge / 2 undetermined`,
32 actions, and 229 requests. The separate first-attempt setup failure used
17 requests before any N01 action. Output files must not already exist; choose
new paths for another run. Neither replay makes a new reference observation.
The source archive must include tracked evidence and source snapshots; the
installed wheel alone contains the core modules.

## Optional live current-emulator example

This needs an ARM64 host, Docker, the cached pinned Gitea image from
`reference/compose.yaml`, a free loopback port, and a unique Compose project.
Fetch the image deliberately if it is absent:

```sh
docker pull --platform linux/arm64 gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9
```

Then run from the source checkout with a new output path:

```sh
export REALITYBRIDGE_COMPOSE_PROJECT=rb-example-unique-20260923
export REALITYBRIDGE_PORT=13021
uv run python reference/owned_lifecycle.py -- \
  uv run python experiments/public_workflow.py live \
  --output /tmp/realitybridge-live-example.json
```

The wrapper preflights Docker, ARM64 image architecture, the project name,
existing resources, and the port. It removes only the project it accepted and
started, including on command failure. The example uses exposed development
case D14. Expect `status: complete`, one agreeing case, and a nonzero metered
request count. This checks the current implementation, not a new holdout. Do
not use an old `docker compose down -v` command against a project you did not
create.

## What a PR must contain

- The change and the retained evidence that motivates it.
- A `STATUS.md` entry if a milestone claim or the untested-claims section
  changes.
- Updated manifest rows if simulator behaviour changed.
- AI-assistance disclosure if any part was AI-written, consistent with the
  [existing disclosure](docs/AI-ASSISTANCE.md).

Protocol and reference-pin changes require a documented review before new
measurements. Do not reinterpret the frozen 2026-09-22 result by changing its
cases or estimator after observing outcomes.
