"""Reviewed, create-only master imports. Never overwrites an existing master."""
from pathlib import Path
import hashlib
import json
from django.http import FileResponse
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .auth import require, audit
from .models import Company, RegisterCategory, RegisterSource, Project, Party
from .registers import CategorySerializer, SourceSerializer
from .accounting_setup import ProjectSerializer
from .serializers import PartySerializer
from .register_imports import read_upload, parsed_date
from .recovery import desktop_only

TYPES = {'categories': (RegisterCategory,CategorySerializer,['code','name','description','parent','active']),
         'sources': (RegisterSource,SourceSerializer,['name','kind','account_title','bank','branch','account_number','iban','active']),
         'projects': (Project,ProjectSerializer,['code','name','reference','client','location','contact_name','email','start_date','end_date','active']),
         'parties': (Party,PartySerializer,['name','kind','entity_type','address','phone','email','ntn','strn','ftn','active'])}


class ImportTemplate(APIView):
    def get(self, request):
        desktop_only()
        require(request.user, 'register.view')
        file = Path(__file__).resolve().parents[1] / 'resources/V2-Testing-and-Import.xlsx'
        if not file.is_file():
            raise ValidationError('The testing workbook is missing from this installation.')
        return FileResponse(file.open('rb'), as_attachment=True, filename=file.name,
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class MasterImport(APIView):
    @transaction.atomic
    def post(self, request):
        desktop_only()
        require(request.user,'register.manage')
        require(request.user,'register.import')
        get_object_or_404(Company.objects.select_for_update(),pk=1)
        kind = request.data.get('kind')
        if kind not in TYPES:
            raise ValidationError('Select categories, sources, projects or parties.')
        model, serializer_type, fields = TYPES[kind]
        filename, digest, sheets, warnings = read_upload(request)
        if request.data.get('action') == 'inspect':
            return Response({'sheets':list(sheets), 'warnings':warnings})
        selected = request.data.get('sheet')
        if selected not in sheets:
            raise ValidationError('Select a worksheet.')
        try:
            header = int(request.data.get('header_row',1))
        except (TypeError,ValueError):
            raise ValidationError('Invalid header row.')
        source = sheets[selected]
        if not 1 <= header <= min(50,len(source)-1):
            raise ValidationError('Select a header row with data below it.')
        headers = [s.strip().lower() for s in source[header-1]]
        if not headers or any(h not in fields for h in headers) or len(headers) != len(set(headers)):
            raise ValidationError({'message':'Use unique template column headings. Unknown columns are not silently ignored.', 'allowed_columns':fields})
        rows, validators, seen, codes = [], [], set(), set()
        for index, values in enumerate(source[header:],header+1):
            if not any(values):
                continue
            payload = {key:values[i] for i,key in enumerate(headers) if i<len(values) and values[i]!=''}
            errors = []
            try:
                if any(v.startswith('=') for v in payload.values()):
                    raise ValidationError('Use literal values, not formulas.')
                if 'active' in payload:
                    if payload['active'].casefold() not in ['true','false','1','0','yes','no']:
                        raise ValidationError('Active must be true or false.')
                    payload['active'] = payload['active'].casefold() in ['true','1','yes']
                for key in ['start_date','end_date']:
                    if key in payload:
                        payload[key] = parsed_date(payload[key],request.data.get('date_format','iso'))
                for key, related in [('parent',RegisterCategory),('client',Party)]:
                    if key in payload:
                        text = payload[key]
                        matches = [r for r in related.objects.filter(active=True) if text.casefold() in [r.name.casefold(),getattr(r,'code','').casefold()]]
                        if len(matches)!=1:
                            raise ValidationError(f'{key}: select one existing active name/code. Import parent/client records first.')
                        payload[key] = matches[0].pk
                name = str(payload.get('name','')).casefold()
                if name in seen or model.objects.filter(name__iexact=payload.get('name','')).exists():
                    raise ValidationError('Name already exists in this file or the application. Existing records are never overwritten.')
                seen.add(name)
                if payload.get('code'):
                    code = payload['code'].casefold()
                    if code in codes or model.objects.filter(code__iexact=payload['code']).exists():
                        raise ValidationError('Code already exists in this file or the application.')
                    codes.add(code)
                validator = serializer_type(data=payload,context={'request':request})
                validator.is_valid(raise_exception=True)
                validators.append(validator)
            except (ValidationError,ValueError) as error:
                errors.append(str(error))
            rows.append({'row':index,'name':payload.get('name',''),'values':{key:values[i] for i,key in enumerate(headers) if i<len(values)},'errors':errors})
        if not 1 <= len(rows) <= 1000:
            raise ValidationError('Import between 1 and 1,000 records.')
        ready = not any(r['errors'] for r in rows)
        proof = {'user':request.user.pk,'kind':kind,'hash':digest,'sheet':selected,'header':header,'date_format':request.data.get('date_format','iso'), 'count':len(rows)}
        proof['values_hash'] = hashlib.sha256(json.dumps([v.initial_data for v in validators],sort_keys=True,default=str).encode()).hexdigest()
        action = request.data.get('action','preview')
        if action == 'preview':
            return Response({'rows':rows,'ready':ready,'count':len(rows),'warnings':warnings,'token':signing.dumps(proof,salt='master-import') if ready else ''})
        if action != 'commit' or request.data.get('acknowledge') != 'true' or not ready:
            raise ValidationError('Review a valid preview and acknowledge the new records before import.')
        try:
            approved = signing.loads(request.data.get('token',''),salt='master-import',max_age=1800)
        except signing.BadSignature:
            raise ValidationError('Preview expired or invalid. Preview this file again.')
        if approved != proof:
            raise ValidationError('The file or selection changed. Preview again.')
        ids = []
        for validator in validators:
            obj = validator.save()
            ids.append(obj.pk)
            audit(request.user,'register.master_imported',f'{kind}:{obj.pk}',file_hash=digest,sheet=selected)
        audit(request.user,'register.master_import_completed',kind,file_hash=digest,filename=filename,count=len(ids))
        return Response({'message':f'{len(ids)} new {kind} imported.', 'ids':ids},status=201)
