"""Private bundled service for native Windows acceptance testing.

No migrations, bootstrap users, secret regeneration or database copies occur here.
The configured existing isolated V2 data must already be initialized.
"""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--port', type=int, default=8765, choices=[8765])
    args = parser.parse_args()
    data = Path(args.data_dir).resolve(strict=True)
    if not (data/'register.sqlite3').is_file() or not (data/'service-secret.txt').is_file():
        raise RuntimeError('Select initialized V2 data; the pilot database is never used.')
    os.environ['ERP_DESKTOP_DATA_DIR'] = str(data)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
    # Isolate this service from unrelated shell database configuration.
    os.environ.pop('POSTGRES_HOST', None)
    os.environ.pop('ERP_DEBUG', None)
    from django.core.wsgi import get_wsgi_application
    from waitress import create_server
    app = get_wsgi_application()
    # Preflight reads only: report pending migrations instead of changing accounts.
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise RuntimeError('The V2 database requires a backed-up upgrade before launch.')
    server = create_server(app, host='127.0.0.1', port=args.port)
    print('V2 desktop service ready on loopback.', flush=True)
    server.run()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Desktop startup failed: {error}', file=sys.stderr, flush=True)
        raise SystemExit(1)
