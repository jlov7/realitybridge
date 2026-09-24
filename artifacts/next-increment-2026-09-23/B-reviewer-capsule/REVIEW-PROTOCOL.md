# Blind oracle review

Classify against the enclosed historical 2026-09-22 observation contract. The current source has a later, stricter paired label-row rule. A difference caused only by applying that later rule is a contract change, not a missed verdict under the historical contract. Record it separately.

The case IDs are opaque and randomized. Each case gives raw reference and simulator responses/errors and separately read issue/label state after each action. Classify the initial state and each step using `agree`, `diverge`, `unsupported`, or `undetermined`. Name the exact fields, API contract rule, and any uncertainty. Do not infer agreement from an absent response or an unsuccessful readback. If a raw ID matters, explain the paired identity evidence instead of comparing generated IDs directly.

First submit your classifications without accessing the answer key or comparison code. Then compare against the private key with a separate adjudicator. Record every disagreement, source trace, rationale, resolution and unresolved question. A reviewer who already knows public cases should disclose that exposure. This capsule contains no comparator verdict; packet preparation is not a review.
