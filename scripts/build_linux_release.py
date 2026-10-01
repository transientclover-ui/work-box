#!/usr/bin/env python3
"""Build the user-local Linux release archive."""
from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
import tarfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


def add_bytes(archive: tarfile.TarFile, name: str, data: bytes, mode: int):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    archive.addfile(info, BytesIO(data))


def build_archive(version: str) -> Path:
    DIST.mkdir(exist_ok=True)
    asset = DIST / f'work-box-{version}-linux-x86_64.tar.gz'
    prefix = f'work-box-{version}-linux-x86_64'
    with asset.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                launcher = (
                    '#!/bin/sh\n'
                    'set -eu\n'
                    'root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
                    'export PYTHONPATH="$root/lib/work-box'
                    '${PYTHONPATH:+:$PYTHONPATH}"\n'
                    'exec python3 -m workbox "$@"\n'
                ).encode()
                add_bytes(
                    archive,
                    f'{prefix}/bin/work-box-orders',
                    launcher,
                    0o755,
                )
                for path in sorted((ROOT / 'src' / 'workbox').glob('*.py')):
                    add_bytes(
                        archive,
                        f'{prefix}/lib/work-box/workbox/{path.name}',
                        path.read_bytes(),
                        0o644,
                    )
                for name in ('LICENSE', 'README.md'):
                    add_bytes(
                        archive,
                        f'{prefix}/share/doc/work-box/{name}',
                        (ROOT / name).read_bytes(),
                        0o644,
                    )
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    asset.with_suffix(asset.suffix + '.sha256').write_text(
        f'{digest}  {asset.name}\n',
        encoding='ascii',
    )
    return asset


def main():
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    asset = build_archive(metadata['project']['version'])
    print(asset)


if __name__ == '__main__':
    main()
