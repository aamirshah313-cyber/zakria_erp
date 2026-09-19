"""Private bundled service for the native Windows application.

The launcher passes the shared data folder. A missing folder is initialized as a
new, empty installation (private secret, database schema); the first
administrator is then created through the application's one-time setup screen.
An existing database with pending schema changes is backed up and integrity
checked before it is upgraded. One automatic backup is kept per day (newest
seven). No users, passwords or business records are created, copied or changed
here.
"""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import sys
import threading

log = logging.getLogger('zakaria.desktop')


def prepare_data(data):
    """Create a new installation's folders and secret; refuse partial data."""
    database, secret = data / 'register.sqlite3', data / 'service-secret.txt'
    if database.exists() and not secret.is_file():
        raise RuntimeError(f'{data} has a database but no service secret. Restore the complete data folder from backup.')
    for folder in (data, data / 'evidence', data / 'backups', data / 'logs'):
        folder.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(secrets.token_urlsafe(64))
        log.info('Created a new service secret for this installation.')
    return database


def automatic_backups():
    """Daily copy at startup, rechecked hourly while the application stays open."""
    from django.db import connection
    from core.backups import automatic_backup_if_due
    while True:
        try:
            created = automatic_backup_if_due()
            if created:
                log.info('Automatic backup saved: %s', created)
        except Exception:
            log.exception('Automatic backup failed')
        finally:
            connection.close()
        threading.Event().wait(3600)


def configure_logging(data):
    handler = RotatingFileHandler(data / 'logs' / 'service.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    root = logging.getLogger()
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler(sys.stdout))
    root.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--port', type=int, default=8765, choices=[8765])
    args = parser.parse_args()
    data = Path(args.data_dir)
    if not data.is_absolute():
        raise RuntimeError('The data folder must be an absolute path.')
    data = data.resolve()
    database = prepare_data(data)
    configure_logging(data)
    existing = database.is_file() and database.stat().st_size > 0
    os.environ['ERP_DESKTOP_DATA_DIR'] = str(data)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
    # Isolate this service from unrelated shell database configuration.
    os.environ.pop('POSTGRES_HOST', None)
    os.environ.pop('ERP_DEBUG', None)
    from django.core.wsgi import get_wsgi_application
    from waitress import create_server
    app = get_wsgi_application()
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        if existing:
            from core.backups import save_local_backup
            backup, _ = save_local_backup('before-upgrade')
            log.info('Backed up %s before applying %d schema change(s): %s', database.name, len(plan), backup)
        else:
            log.info('Initializing a new database with %d schema change(s).', len(plan))
        call_command('migrate', interactive=False, verbosity=0)
        connection.close()
        log.info('Database schema is current.')
    threading.Thread(target=automatic_backups, name='automatic-backups', daemon=True).start()
    # Backup restores stream large files; waitress would otherwise cap requests at 1 GB.
    server = create_server(app, host='127.0.0.1', port=args.port, max_request_body_size=64 * 1024 ** 3)
    log.info('V2 desktop service ready on loopback using %s', data)
    server.run()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        log.exception('Desktop startup failed')
        print(f'Desktop startup failed: {error}', file=sys.stderr, flush=True)
        raise SystemExit(1)
