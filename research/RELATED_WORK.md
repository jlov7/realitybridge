# Related work

RealityBridge is a bounded simulator-comparison experiment: six issue and label operations against pinned Gitea, with response and state observations, retained counterexamples, and offline replay. Its ordinary-comparator challenge found no additional in-scope discovery advantage. It has not established a new general testing method or superiority over the tools below.

The following primary-source descriptions were checked on 2026-09-24. This is a selected reading list, not a systematic literature review. The differences describe this repository's workload and evidence; they do not assert that the cited projects lack an unexamined capability.

| Work | Relevant scope | Relation to this repository |
| --- | --- | --- |
| [SynAE](https://arxiv.org/abs/2605.22564) | Evaluates the validity, fidelity and diversity of synthetic tool-calling trajectories, including downstream evaluation. | Provides a broader account of evaluation-data quality. RealityBridge observes one executable simulator against one reference application. |
| [Agent-Diff](https://arxiv.org/abs/2602.11224) | Evaluates code-executing agents using enterprise API replicas and state-diff contracts. | State-based evaluation is established prior work. Our question is the simulator's agreement with a pinned reference under a declared observation contract. |
| [When Simulation Lies / RobustBench-TC](https://arxiv.org/abs/2605.11928) | Studies tool-use robustness under perturbations and a domain-randomized reinforcement-learning recipe. | Connects tool failures to agent behavior. The scripted policy exercises here are much narrower and found no simulator-caused ranking error in their authored tasks. |
| [OPINE-World](https://arxiv.org/abs/2607.01531) | Learns programmatic world models through interaction, hypothesis testing and counterexample-guided refinement. | Program synthesis and counterexample-guided repair are prior work. RealityBridge applies a bounded comparison to an existing business API. |
| [LearnLib](https://learnlib.de/) | Supplies automata-learning algorithms, counterexample analysis and conformance-testing infrastructure. | Model learning and conformance testing are established techniques; this repository does not claim to invent them. |
| [RESTler](https://github.com/microsoft/restler-fuzzer) | Performs stateful REST API fuzzing to find security and reliability defects. | A relevant testing tool, but not a directly evaluated baseline in the retained study. The local ordinary comparator must not be described as RESTler. |

## What the evidence supports

The contribution is an inspectable implementation and a small set of reproducible measurements, including negative comparisons. Matching a reference bug establishes agreement with that version under the measured contract; it does not establish correctness or safety. Separate evaluator code does not establish independent human validation. The [evidence index](../docs/EVIDENCE-INDEX.md) identifies which result and receipt support each claim.
