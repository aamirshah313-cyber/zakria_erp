"""Create isolated development data; never overwrite the pilot or V2 database."""
import argparse
import os
from pathlib import Path
import secrets
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy-pilot', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target_dir = root / 'storage' / 'v2-desktop'
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / 'evidence').mkdir(exist_ok=True)
    secret_file = target_dir / 'service-secret.txt'
    try:
        fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(secrets.token_urlsafe(64))
    destination = target_dir / 'register.sqlite3'
    if destination.exists():
        print('V2 database already exists; preserved without changes.')
        return
    if args.copy_pilot:
        source = root / 'backend' / 'local.sqlite3'
        if not source.is_file():
            raise SystemExit('Pilot database not found; no empty replacement was created.')
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
            with sqlite3.connect(destination) as clone:
                original.backup(clone)
                # Preserve passwords/roles; require fresh sign-in to this copy.
                if clone.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_accesssession'").fetchone():
                    clone.execute('DELETE FROM core_accesssession')
        print('Created isolated V2 development copy; pilot untouched, copied sessions cleared.')
    else:
        print('Desktop directories prepared. Migrations will initialize an empty V2 database.')


if __name__ == '__main__':
    main()
