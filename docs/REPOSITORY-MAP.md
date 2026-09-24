# Repository map

Start with the [README](../README.md) for the problem, one scenario, and an offline replay. [Architecture](ARCHITECTURE.md) explains the comparison and tradeoffs. [Contributing](../CONTRIBUTING.md) owns working commands and failure guidance; [status](../STATUS.md) owns the current release and claim state. [Evidence index](EVIDENCE-INDEX.md) identifies which record controls each result. Avoid reading an older proposal or milestone as the current outcome.

| Path | Purpose |
|---|---|
| `src/reality_bridge/` | Current simulator, reference adapter, projection, four-way comparison, full-state oracle, repair and bounded counterexample minimization. The default emulator is repaired after the measured study. |
| `assets/readme/` | Self-contained README mark and desktop/mobile comparison diagrams; the same path is described in Markdown for text-only readers. |
| `contracts/` | Six-operation grammar and declared response/state observation boundary. |
| `reference/` | Digest-pinned, loopback Gitea Compose configuration, synthetic seed, and owned lifecycle wrapper for optional live checks. |
| `experiments/` | Study runners, fixed cases, source materializer, offline replayers, examples, and the **frozen measured emulator/oracle sources** needed to reproduce older receipts. A historical source copy here is intentional, not a second maintained implementation. |
| `tests/` | Unit, boundary, and integration tests for current code; some require macOS isolation or ARM64 Docker. |
| `artifacts/research-completion-2026-09-22/` | Immutable measured attempt, raw arm and policy records, and separately labeled post-study requalifications. |
| `artifacts/ordinary-baseline-2026-09-23/` | Both setup-failure and amended study receipts, offline replay, and later current-source engineering requalification. Keep all records together. |
| `research/ordinary-baseline-2026-09-23/` | Frozen study protocol, amendment, and source manifests, plus byte-verified public derivations of the private source archives for history-free replay. `snapshots/PUBLIC-DERIVATION.json` records original and public archive hashes, every retained member hash, and exclusions. |
| `artifacts/engineering-minimization-2026-09-23/` | Exposed E06 minimization regression receipts. |
| `artifacts/evidence/` and `docs/audit-2026-09-22/` | Older scientific milestone records and raw audit results. Internal publication and audit closeout documents are excluded; the current claim comes from the newer frozen result. |
| `docs/research-completion-2026-09-22/` | Frozen prospective protocol and measured result. |
| `docs/QUALIFICATION-MANIFEST.md`, `research/PROTOCOL.md` | Historical qualification and initial protocol. Useful to understand development, not current result authority. |
| `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` | Declared CI and locked project configuration. A workflow file is not a hosted passing result. |

The [AI-assistance note](AI-ASSISTANCE.md) states how AI was used. `CHANGELOG.md`, `CITATION.cff`, `SUPPORT.md`, and `SECURITY.md` cover version history, citation, support, and reporting scope.
