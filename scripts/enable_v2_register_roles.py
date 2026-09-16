"""Explicit, audited activation of the approved V2 register workflow.

Preview by default. --apply backs up the isolated database before activation.
Never run automatically during application startup or a schema migration.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'storage/v2-desktop'
DATABASE = DATA / 'register.sqlite3'
PILOT = ROOT / 'backend/local.sqlite3'
GRANTS = {
    'Administrator': ['register.view', 'register.manage', 'register.create',
                      'register.import', 'register.export'],
    'Finance Manager': ['register.view', 'register.create', 'register.import',
                        'register.export'],
    'General Manager': ['register.view', 'register.approve', 'register.export'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not DATABASE.is_file() or DATABASE.resolve() == PILOT.resolve():
        raise RuntimeError('An existing isolated V2 database is required.')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
    os.environ['ERP_DESKTOP_DATA_DIR'] = str(DATA)
    sys.path.insert(0, str(ROOT / 'backend'))
    import django
    django.setup()
    from django.conf import settings
    from django.db import transaction
    from core.auth import audit
    from core.models import Company, Role, RegisterRule, User
    from core.serializers import RoleSerializer

    if Path(settings.DATABASES['default']['NAME']).resolve() != DATABASE.resolve():
        raise RuntimeError('Unexpected database target.')
    roles = {name: Role.objects.get(name=name) for name in GRANTS}
    for name, grants in GRANTS.items():
        print(name + ': add ' + ', '.join(sorted(set(grants) - set(roles[name].permissions))))
    rule = RegisterRule.objects.filter(pk=1).first()
    print('Approval rule: ' + ('preserve existing rule' if rule else 'General Manager'))
    reviewers = User.objects.filter(role=roles['General Manager'], status='active', is_active=True).count()
    print('Active General Manager accounts:', reviewers)
    if not args.apply:
        print('Preview only; no records changed.')
        return

    pilot_hash = hashlib.sha256(PILOT.read_bytes()).hexdigest() if PILOT.exists() else None
    backup = ROOT / 'storage/backups' / ('before-v2-role-activation-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
    backup.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True) as source:
        users_before = source.execute('SELECT id, username, password, role_id, status, is_active FROM core_user ORDER BY id').fetchall()
        tables = [row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'core_%'") if row[0] not in {'core_role', 'core_auditevent', 'core_registerrule', 'core_accesssession'}]
        def fingerprints(connection):
            return {table: hashlib.sha256(repr(connection.execute('SELECT * FROM "' + table + '" ORDER BY id').fetchall()).encode()).hexdigest() for table in tables}
        business_before = fingerprints(source)
        with sqlite3.connect(backup) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed.')

    with transaction.atomic():
        Company.objects.select_for_update().get(pk=1)
        for name, grants in GRANTS.items():
            role = Role.objects.select_for_update().get(pk=roles[name].pk)
            before = sorted(role.permissions)
            after = sorted(set(before) | set(grants))
            if before == after:
                continue
            serializer = RoleSerializer(role, data={'permissions': after}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            audit(None, 'role.v2_register_activation', role.pk, role=name,
                  before=before, permissions=after,
                  source='explicit local V2 deployment configuration',
                  reason='Activate approved Finance preparer / General Manager reviewer workflow; preserve audit and bank-identifier access.')
        if not RegisterRule.objects.filter(pk=1).exists():
            rule = RegisterRule.objects.create(pk=1, approver_role=roles['General Manager'])
            audit(None, 'register.approval_rule_activated', rule.pk,
                  approver_role=rule.approver_role_id,
                  source='explicit local V2 deployment configuration')

    with sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True) as source:
        assert source.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert users_before == source.execute('SELECT id, username, password, role_id, status, is_active FROM core_user ORDER BY id').fetchall()
        assert business_before == fingerprints(source), 'Business records changed during activation; investigate concurrent activity.'
    assert pilot_hash == (hashlib.sha256(PILOT.read_bytes()).hexdigest() if PILOT.exists() else None)
    print('PASS: role activation audited; user accounts/passwords, business records and pilot preserved.')
    print('Backup:', backup)


if __name__ == '__main__':
    main()
