# Public source snapshots for the ordinary comparison

The two source snapshots in `snapshots/` are deterministic **public derivations**
of the original private Git archives, not byte-identical copies of those
archives. The originals remain in the private research record. Their SHA-256
hashes, the public archive hashes, every retained file's SHA-256 hash, and the
exact excluded paths and reasons are in
[`snapshots/PUBLIC-DERIVATION.json`](snapshots/PUBLIC-DERIVATION.json).

The derivation copied each retained regular file byte for byte. It excluded
historical private agent instructions and process/status trackers, an internal
build plan, a stale publication checklist, a private audit closeout, an
operational cleanup receipt, and a redundant directory marker. It sorted retained
paths and wrote GNU tar files with normalized owner, group, mode, and time,
then gzip with no filename and zero timestamp. Directory entries were omitted.
No frozen scientific source manifest, protocol, raw observation, or receipt was
changed.

`experiments/replay_ordinary_baseline.py` checks the public archive and
derivation-manifest hashes, the complete retained-member inventory and hashes,
the original archive identities recorded in the derivation, every source hash
in the unchanged frozen manifests, and the retained raw receipt hashes. The
frozen materializer expects `AGENTS.md` as an input copy. Because the historical
agent instructions are not shipped, replay writes a fixed inert `AGENTS.md`
in its temporary extraction **after** verifying the frozen source. That file is
not in either public archive; its hash is reported in replay output. The
materialized source is then verified and required to have a clean local Git
tree. This compatibility file does not change the scientific source or the
recomputed observations.

The offline replay reproduces comparisons from captured rows only. It makes
no new Gitea calls and is not independent replication of the study.
