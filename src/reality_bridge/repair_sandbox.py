"""OS-enforced input boundary for the bounded repair proposal worker."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RepairSandboxError(RuntimeError):
    """The enforced worker boundary was unavailable or failed closed."""


@dataclass(frozen=True, slots=True)
class SandboxRepairReceipt:
    rules: tuple[dict[str, str], ...]
    allowed_execution: bool
    forbidden_read_denied: bool
    worker_source_sha256: str
    worker_binary_sha256: str
    compiler_sha256: str
    profile_sha256: tuple[str, str]
    profile_templates: tuple[str, str]
    forbidden_probe_repo_path: str


def _quoted(path: Path) -> str:
    return str(path).replace('"', '\\"')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile(worker: Path, input_path: Path, output_dir: Path) -> str:
    return f"""
(version 1)
(deny default)
(import "system.sb")
(deny network*)
(allow process-exec (literal "{_quoted(worker)}"))
(allow file-read* file-map-executable
    (literal "{_quoted(worker)}")
    (literal "{_quoted(input_path)}"))
(allow file-write* (subpath "{_quoted(output_dir)}"))
""".strip()


def _extract_colors(counterexample: dict[str, Any]) -> tuple[str, str]:
    ref = counterexample.get("ref") or {}
    sim = counterexample.get("sim") or {}
    if not isinstance(ref, dict) or not isinstance(sim, dict):
        return "", ""
    if isinstance(ref.get("color"), str) and isinstance(sim.get("color"), str):
        return ref["color"], sim["color"]
    if isinstance(ref.get("labels"), list) and isinstance(sim.get("labels"), list):
        sim_by_name = {item.get("name"): item for item in sim["labels"] if isinstance(item, dict)}
        for ref_item in ref["labels"]:
            if not isinstance(ref_item, dict):
                continue
            sim_item = sim_by_name.get(ref_item.get("name"))
            if isinstance(sim_item, dict) and isinstance(ref_item.get("color"), str):
                sim_color = sim_item.get("color")
                if isinstance(sim_color, str):
                    return ref_item["color"], sim_color
    return "", ""


def _compile_worker(source: Path, output: Path) -> None:
    completed = subprocess.run(
        [
            "/usr/bin/clang",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file():
        diagnostic = completed.stderr.strip().splitlines()[-1:] or ["no diagnostic"]
        raise RepairSandboxError(
            f"repair worker compilation failed with exit {completed.returncode}: "
            f"{diagnostic[0][:160]}"
        )


def _run_once(
    worker: Path,
    colors: tuple[str, str],
    root: Path,
    name: str,
    probe_path: Path | None = None,
) -> tuple[dict[str, Any], str, str]:
    output_dir = root / f"{name}-output"
    output_dir.mkdir()
    input_path = root / f"{name}-input.txt"
    output_path = output_dir / "proposal.json"
    profile_path = root / f"{name}.sb"
    lines = [*colors]
    if probe_path is not None:
        lines.append(str(probe_path))
    input_path.write_text("\n".join(lines) + "\n")
    profile_path.write_text(_profile(worker, input_path, output_dir) + "\n")
    profile_hash = _sha256(profile_path)
    completed = subprocess.run(
        [
            "/usr/bin/sandbox-exec",
            "-f",
            str(profile_path),
            str(worker),
            str(input_path),
            str(output_path),
        ],
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", "TMPDIR": str(root)},
        check=False,
    )
    if completed.returncode != 0 or not output_path.is_file():
        diagnostic = completed.stderr.strip().splitlines()[-1:] or ["no diagnostic"]
        raise RepairSandboxError(
            f"sandboxed worker failed with exit {completed.returncode}: {diagnostic[0][:160]}"
        )
    parsed = json.loads(output_path.read_text())
    if not isinstance(parsed, dict):
        raise RepairSandboxError("sandboxed worker output was not a mapping")
    profile_template = _profile(Path("$WORKER"), Path("$INPUT"), Path("$OUTPUT"))
    return parsed, profile_hash, profile_template


def run_sandboxed_repair(
    counterexample: dict[str, Any], worker_source: Path, forbidden_probe: Path
) -> SandboxRepairReceipt:
    """Derive a proposal and prove a named repository path is unreadable."""
    if os.uname().sysname != "Darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise RepairSandboxError("macOS sandbox-exec is required; no fallback is permitted")
    if not forbidden_probe.is_file() or not os.access(forbidden_probe, os.R_OK):
        raise RepairSandboxError("forbidden probe must exist and be parent-readable")
    colors = _extract_colors(counterexample)
    worker_source = worker_source.resolve()
    source_hash = _sha256(worker_source)
    compiler_hash = _sha256(Path("/usr/bin/clang"))
    with tempfile.TemporaryDirectory(prefix="realitybridge-repair-", dir="/private/tmp") as tmp:
        root = Path(tmp)
        worker = root / "repair-worker"
        _compile_worker(worker_source, worker)
        binary_hash = _sha256(worker)
        ordinary, ordinary_profile_hash, ordinary_template = _run_once(
            worker, colors, root, "ordinary"
        )
        probe, probe_profile_hash, probe_template = _run_once(
            worker, colors, root, "probe", forbidden_probe.resolve()
        )
    raw_rules = ordinary.get("rules")
    if not isinstance(raw_rules, list) or any(not isinstance(rule, dict) for rule in raw_rules):
        raise RepairSandboxError("worker rules did not satisfy the declarative schema")
    rules: list[dict[str, str]] = []
    for rule in raw_rules:
        if set(rule) != {"field", "transform", "evidence"} or any(
            not isinstance(value, str) for value in rule.values()
        ):
            raise RepairSandboxError("worker emitted an unsupported rule shape")
        rules.append(rule)
    denied = probe.get("probe_read") == "denied"
    if not denied:
        raise RepairSandboxError("repair worker could read the forbidden evaluation path")
    return SandboxRepairReceipt(
        rules=tuple(rules),
        allowed_execution=True,
        forbidden_read_denied=True,
        worker_source_sha256=source_hash,
        worker_binary_sha256=binary_hash,
        compiler_sha256=compiler_hash,
        profile_sha256=(ordinary_profile_hash, probe_profile_hash),
        profile_templates=(ordinary_template, probe_template),
        forbidden_probe_repo_path=str(
            forbidden_probe.resolve().relative_to(worker_source.parents[1])
        ),
    )
