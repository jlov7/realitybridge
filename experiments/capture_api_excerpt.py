"""Capture only six API operation schemas from the owned pinned reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from reality_bridge import reference as ref

IMAGE = "gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9"
METHODS = {
    "/repos/{owner}/{repo}/issues": ["post"],
    "/repos/{owner}/{repo}/issues/{index}": ["get", "patch"],
    "/repos/{owner}/{repo}/issues/{index}/labels": ["post"],
    "/repos/{owner}/{repo}/issues/{index}/labels/{id}": ["delete"],
    "/repos/{owner}/{repo}/labels": ["post"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("owned lifecycle required")
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["source_sha256"].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError(f"source mismatch: {name}")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    if commit != manifest["runtime_commit"]:
        raise RuntimeError("commit mismatch")
    container = ref._compose("ps", "-q", "gitea").strip()
    image = subprocess.run(
        ["docker", "inspect", "-f", "{{.Config.Image}}|{{.Image}}", container],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if image.split("|")[0] != IMAGE:
        raise RuntimeError("pinned image mismatch")
    with ref.count_reference_calls(limit=2) as meter:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{ref.REFERENCE_PORT}",
            timeout=15,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            version = (
                ref.reference_request(client, "GET", "/api/v1/version").raise_for_status().json()
            )
            swagger = (
                ref.reference_request(client, "GET", "/swagger.v1.json").raise_for_status().json()
            )
        selected = {
            path: {method: swagger["paths"][path][method] for method in methods}
            for path, methods in METHODS.items()
        }
        result = {
            "status": "complete",
            "manifest_sha256": sha(manifest_path),
            "runtime_commit": commit,
            "image": image,
            "version": version,
            "swagger": selected,
            "requests": meter.requests,
        }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                "status": result["status"],
                "requests": result["requests"],
                "version": result["version"],
            }
        )
    )
