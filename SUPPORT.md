# Support and issue scope

Report nonsensitive bugs in the [repository issue tracker](https://github.com/jlov7/realitybridge/issues).
Do not include credentials, exploit details, or client or employer data.
For sensitive findings, follow [Security](SECURITY.md). The 2026-09-24 local
review did not observe a hosted CI result; inspect the current
[Actions page](https://github.com/jlov7/realitybridge/actions) before citing one.

The supported workflow is source archive → locked development install → offline measured replay. The optional live example requires an ARM64 host, cached pinned Gitea image, Docker, a free loopback port, and an owned unique Compose project. The wheel supplies core Python modules; it does not contain the live reference configuration or retained study files.

Python 3.11 and 3.13 are declared CI test targets. Other interpreters accepted by package metadata have no completed evidence in the local review. macOS repair-worker isolation is checked separately on a macOS runner. A workflow file alone does not establish a passing hosted run.

For a reproducible issue, include the exact source commit or archive hash, Python/OS/architecture, command, output status, and a synthetic minimized case. Redact tokens and avoid client or employer data. State whether the problem concerns offline replay, current-emulator regression, live reference, or historical evidence. Scientific claims must identify the measured source and receipt; a green package test is not a new research result.
