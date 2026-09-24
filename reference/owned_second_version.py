"""Owned lifecycle for the one pinned 1.24.6 rootless transfer reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from reality_bridge import reference as ref
from reference import owned_lifecycle

IMAGE = 'gitea/gitea@sha256:fe643e27326a7fae86dedb544d9392ba662adc3083763a21bd7acc35796449fd'
ref.COMPOSE_FILE = ROOT / 'reference/compose-1.24.6.yaml'
owned_lifecycle.IMAGE = IMAGE

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('provide a command after --')
    raise SystemExit(owned_lifecycle.run_owned(command))
