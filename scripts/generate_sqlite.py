#!/usr/bin/env python3
"""Generate a sqlite3 DB from current migrations and fixtures.

This script forces Django to use the repo `db.sqlite3` for the run
by setting `USE_REPO_SQLITE=1` before importing Django settings.
It then runs `migrate` and `loaddata` (if fixture exists) to produce
`db.sqlite3` in the repository root.
"""
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

# Tell settings to prefer the repo sqlite for this execution
os.environ['USE_REPO_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asset_manager.settings')

try:
    import django
    from django.core.management import call_command
except Exception as exc:
    print('Unable to import Django. Ensure your virtualenv is active.', file=sys.stderr)
    raise

django.setup()

print('Running migrations on sqlite...')
call_command('migrate', '--noinput')

fixture = ROOT / 'gestao' / 'fixtures' / 'devdata.json'
if fixture.exists():
    print(f'Loading fixture {fixture} into sqlite DB...')
    call_command('loaddata', str(fixture))
else:
    print('No devdata.json fixture found; skipping loaddata')

dbfile = ROOT / 'db.sqlite3'
if dbfile.exists():
    print(f'Created sqlite DB at {dbfile}')
else:
    print('Failed to create sqlite DB', file=sys.stderr)
    sys.exit(1)
