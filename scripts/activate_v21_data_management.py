"""Explicit V2 deployment activation after the backed-up migration."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
os.environ['DJANGO_SETTINGS_MODULE']='config.desktop'
os.environ['ERP_DESKTOP_DATA_DIR']=str(root/'storage/v2-desktop')
sys.path.insert(0,str(root/'backend'))
import django
django.setup()
from django.db import transaction
from core.models import Role
from core.auth import audit
with transaction.atomic():
    role=Role.objects.select_for_update().get(name='Administrator')
    before=list(role.permissions)
    if 'register.delete' not in before:
        role.permissions=sorted(set(before)|{'register.delete'})
        role.save(update_fields=['permissions'])
        audit(None,'role.v21_data_management',role.pk,source='Explicit local V2 deployment',reason='User requested deletion provisions; enable recoverable draft removal and master archival for Administrator.',before=before,permissions=role.permissions)
print('Administrator Data management enabled. No other roles, users, passwords or audit permissions changed.')
